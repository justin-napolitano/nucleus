"""Read versioned registry packages without activating their declared capabilities."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

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

    def __init__(self, root: Path, schemas: Path) -> None:
        """Bind the registry and schema roots; reads revalidate on every call."""
        self.root = root.resolve(strict=True)
        self.schemas = schemas.resolve(strict=True)
        if not self.root.is_dir() or not self.schemas.is_dir():
            raise RegistryError("registry-or-schema-unavailable")
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

    def _packages(self) -> list[dict[str, Any]]:
        """Rebuild the index so removed or corrected packages take effect immediately."""
        found: dict[str, dict[str, Any]] = {}
        for kind, directory in KINDS.items():
            base = self.root / directory
            if not base.exists():
                continue
            if base.is_symlink() or not base.is_dir():
                raise RegistryError("unsafe-registry-directory")
            for path in sorted(base.glob("*/*/object.json")):
                if path.is_symlink() or any(
                    part.is_symlink() for part in path.parents if part != self.root
                ):
                    raise RegistryError("symlink-package")
                if (
                    not path.resolve().is_relative_to(self.root)
                    or path.stat().st_size > MAX_OBJECT_BYTES
                ):
                    raise RegistryError("unsafe-package")
                value = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(value, dict):
                    raise RegistryError("invalid-object")
                errors = list(
                    Draft202012Validator(
                        self._schema_by_kind[kind], registry=self._resolver
                    ).iter_errors(value)
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
                found[object_id] = {**value, "objectId": object_id, "executionEligible": False}
        return [found[key] for key in sorted(found)]

    def list(
        self, *, kind: str = "", query: str = "", offset: int = 0, limit: int = 25
    ) -> dict[str, Any]:
        """Return a bounded page of metadata; declared tools never become callable."""
        if kind and kind not in KINDS or len(query) > 200 or offset < 0 or not 1 <= limit <= 100:
            raise RegistryError("invalid-filter")
        needle = query.casefold()
        rows = [
            row
            for row in self._packages()
            if (not kind or row["kind"] == kind)
            and (not needle or needle in (row["displayName"] + " " + row["description"]).casefold())
        ]
        return {
            "items": rows[offset : offset + limit],
            "total": len(rows),
            "offset": offset,
            "limit": limit,
            "nextOffset": offset + limit if offset + limit < len(rows) else None,
        }

    def get(self, object_id: str) -> dict[str, Any]:
        """Resolve only an exact indexed identity, never a caller-supplied path."""
        return (
            next((row for row in self._packages() if row["objectId"] == object_id), None)
            or _missing()
        )


def _missing() -> dict[str, Any]:
    """Raise the same not-found result for all unknown identities."""
    raise KeyError("object-not-found")
