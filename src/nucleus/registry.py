"""Read versioned registry packages without activating their declared capabilities."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from nucleus.skills import verify_bundled_candidate

KINDS = {
    "DataDomain": "data-domains",
    "DataProduct": "data-products",
    "Metric": "metrics",
    "Skill": "skills",
    "Workflow": "workflows",
    "Tool": "tools",
    "McpServer": "mcp-servers",
    "Agent": "agents",
}
SCHEMA_FILES = {
    "DataDomain": "data-domain.schema.json",
    "DataProduct": "data-product.schema.json",
    "Metric": "metric.schema.json",
    "Skill": "skill.schema.json",
    "Workflow": "workflow.schema.json",
    "Tool": "tool.schema.json",
    "McpServer": "mcp-server.schema.json",
    "Agent": "agent.schema.json",
}
MAX_OBJECT_BYTES = 1_000_000


class RegistryError(ValueError):
    """A package is malformed, ambiguous, or outside the registry boundary."""


class Catalog:
    """Validate and list local package metadata without granting execution authority."""

    def __init__(
        self,
        root: Path,
        schemas: Path,
        builtin_root: Path | None = None,
        builtin_lock: dict[str, Any] | None = None,
    ) -> None:
        """Bind external and bundled metadata roots; reads revalidate on every call."""
        if root.is_symlink() or (root.exists() and not root.is_dir()):
            raise RegistryError("unsafe-registry-directory")
        self.root = root.resolve()
        self.schemas = schemas.resolve(strict=True)
        self.builtin_root = builtin_root.resolve(strict=True) if builtin_root else None
        self.builtin_lock = builtin_lock
        if not self.schemas.is_dir() or (self.builtin_root and not self.builtin_root.is_dir()):
            raise RegistryError("registry-or-schema-unavailable")
        if (self.builtin_root is None) != (self.builtin_lock is None):
            raise RegistryError("builtin-lock-required")
        resources: list[tuple[str, Resource[Any]]] = []
        self._schema_by_kind: dict[str, dict[str, Any]] = {}
        for path in sorted(self.schemas.glob("*.schema.json")):
            schema = json.loads(path.read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(schema)
            resources.append((schema["$id"], Resource.from_contents(schema)))
            for kind, filename in SCHEMA_FILES.items():
                if path.name == filename:
                    self._schema_by_kind[kind] = schema
        if set(self._schema_by_kind) != set(KINDS):
            raise RegistryError("missing-kind-schema")
        self._resolver = Registry().with_resources(resources)

    def _packages(self) -> dict[str, tuple[dict[str, Any], Path]]:
        """Rebuild the external and pinned indexes without activating skills."""
        found: dict[str, tuple[dict[str, Any], Path]] = {}
        for source_root in (self.builtin_root, self.root):
            if source_root is None:
                continue
            seen_builtin: set[str] = set()
            for kind, directory in KINDS.items():
                base = source_root / directory
                if not base.exists():
                    continue
                if base.is_symlink() or not base.is_dir():
                    raise RegistryError("unsafe-registry-directory")
                for path in sorted(base.glob("*/*/object.json")):
                    self._register_package(path, kind, source_root, found)
                    if source_root == self.builtin_root:
                        seen_builtin.add(path.parent.parent.name.removeprefix("anthropic-"))
            if source_root == self.builtin_root and seen_builtin != set(
                self.builtin_lock["packages"]
            ):
                raise RegistryError("builtin-review-incomplete")
        return dict(sorted(found.items()))

    def _register_package(
        self,
        path: Path,
        kind: str,
        source_root: Path,
        found: dict[str, tuple[dict[str, Any], Path]],
    ) -> None:
        """Validate one package and its bound source before adding it to the index."""
        if path.is_symlink() or any(
            part.is_symlink()
            for part in path.parents
            if part != source_root and part.is_relative_to(source_root)
        ):
            raise RegistryError("symlink-package")
        if not path.resolve().is_relative_to(source_root) or path.stat().st_size > MAX_OBJECT_BYTES:
            raise RegistryError("unsafe-package")
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise RegistryError("invalid-object")
        errors = list(
            Draft202012Validator(self._schema_by_kind[kind], registry=self._resolver).iter_errors(
                value
            )
        )
        if (
            errors
            or value.get("kind") != kind
            or value.get("id") != path.parent.parent.name
            or value.get("version") != path.parent.name
        ):
            raise RegistryError("invalid-object")
        for relative in value["files"]:
            part = Path(relative)
            target = path.parent / part
            if (
                part.is_absolute()
                or ".." in part.parts
                or target.is_symlink()
                or not target.resolve().is_relative_to(path.parent.resolve())
                or not target.is_file()
            ):
                raise RegistryError("invalid-package-file")
        object_id = f"registry://{kind}/{value['id']}@{value['version']}"
        if object_id in found:
            raise RegistryError("duplicate-object")
        if source_root == self.builtin_root:
            if kind != "Skill" or self.builtin_lock is None:
                raise RegistryError("unsupported-builtin-package")
            name = value["id"].removeprefix("anthropic-")
            expected_source = {
                "repository": self.builtin_lock["source"],
                "commit": self.builtin_lock["commit"],
                "path": f"skills/{name}",
            }
            if (
                value["id"] != f"anthropic-{name}"
                or name not in self.builtin_lock["packages"]
                or value["version"] != f"0.0.0-{self.builtin_lock['commit'][:8]}"
                or value.get("source") != expected_source
                or value.get("license") != {"id": "Apache-2.0", "file": "LICENSE.txt"}
                or value.get("state") != "review"
                or value.get("reviewRequired") is not True
                or value.get("instructionsFile") != "SKILL.md"
                or set(value["files"]) != set(self.builtin_lock["packages"][name]["files"])
            ):
                raise RegistryError("builtin-review-mismatch")
            verify_bundled_candidate(path.parent, name, self.builtin_lock)
        found[object_id] = (
            {**value, "objectId": object_id, "executionEligible": False},
            path.parent,
        )

    def list(
        self,
        *,
        kind: str = "",
        query: str = "",
        offset: int = 0,
        limit: int = 25,
        published_only: bool = False,
    ) -> dict[str, Any]:
        """Return bounded metadata, exposing only published entries to agents."""
        if kind and kind not in KINDS or len(query) > 200 or offset < 0 or not 1 <= limit <= 100:
            raise RegistryError("invalid-filter")
        needle = query.casefold()
        rows = [
            row
            for row, _ in self._packages().values()
            if (not kind or row["kind"] == kind)
            and (not published_only or row["state"] == "published")
            and (not needle or needle in (row["displayName"] + " " + row["description"]).casefold())
        ]
        return {
            "items": rows[offset : offset + limit],
            "total": len(rows),
            "offset": offset,
            "limit": limit,
            "nextOffset": offset + limit if offset + limit < len(rows) else None,
        }

    def get(self, object_id: str, *, published_only: bool = False) -> dict[str, Any]:
        """Resolve metadata by indexed identity, filtering agent reads."""
        item = self._packages().get(object_id)
        if item is None or (published_only and item[0]["state"] != "published"):
            return _missing()
        return item[0]

    def review_skill(self, object_id: str) -> dict[str, Any]:
        """Load pinned instructions only for the loopback browser review route."""
        item = self._packages().get(object_id)
        if item is None or item[0]["kind"] != "Skill" or item[0]["state"] != "review":
            return _missing()
        row, directory = item
        relative = row["instructionsFile"]
        if relative not in row["files"]:
            raise RegistryError("invalid-instructions-file")
        instructions = directory / relative
        if instructions.stat().st_size > 262_144:
            raise RegistryError("instructions-too-large")
        return {**row, "instructionsText": instructions.read_text(encoding="utf-8")}


def _missing() -> dict[str, Any]:
    """Raise the same not-found result for all unknown identities."""
    raise KeyError("object-not-found")
