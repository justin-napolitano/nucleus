"""Compile portable, content-addressed schema and lineage evidence without a database."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from nucleus.registry import MAX_OBJECT_BYTES, Catalog, RegistryError

PROJECT_KINDS = {"Source", "SchemaContract", "Mapping", "Run", "Artifact", "Lineage", "Decision"}
POINTERS = {
    "Decision": {"subjectRef": None, "supersedesRef": "Decision"},
    "SchemaContract": {"sourceRef": "Source"},
    "Mapping": {"contractRef": "SchemaContract"},
    "Artifact": {"sourceRef": "Source", "contractRef": "SchemaContract", "runRef": "Run"},
    "Lineage": {"sourceRef": None, "targetRef": None, "runRef": "Run"},
}


def digest(value: Any) -> str:
    """Hash deterministic Python JSON; this is not RFC 8785 canonicalization."""
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(encoded.encode()).hexdigest()


def snapshot(catalog: Catalog, repository: str, revision: str) -> dict[str, Any]:
    """Validate exact references and package contents from one local index generation.

    Revision is a caller-supplied provenance claim, not proof of a clean checkout.
    Publish through a pinned-checkout adapter before treating it as verified Git evidence.
    """
    if not repository or not re.fullmatch(r"[a-f0-9]{40}", revision):
        raise RegistryError("immutable-source-required")
    packages = catalog._packages()
    rows = []
    for _identity, (row, directory) in packages.items():
        components = {}
        for name in row["files"]:
            path = directory / name
            if path.stat().st_size > MAX_OBJECT_BYTES:
                raise RegistryError("component-too-large")
            content = path.read_bytes()
            components[name] = {
                "checksum": "sha256:" + hashlib.sha256(content).hexdigest(),
                "bytes": len(content),
            }
        for reference in row["references"]:
            if reference not in packages:
                raise RegistryError("unresolved-reference")
        if row["kind"] in PROJECT_KINDS:
            if not row["id"].startswith(row["project"] + "--"):
                raise RegistryError("project-qualified-id-required")
            for field, target_kind in POINTERS.get(row["kind"], {}).items():
                target = row.get(field)
                if target is None:
                    continue
                if target not in row["references"] or target not in packages:
                    raise RegistryError("unresolved-evidence-pointer")
                if target_kind and packages[target][0]["kind"] != target_kind:
                    raise RegistryError("wrong-evidence-kind")
            file_field = {"SchemaContract": "contractFile", "Mapping": "mappingFile"}.get(
                row["kind"]
            )
            if file_field:
                name = row[file_field]
                if name not in components or not name.endswith(".json"):
                    raise RegistryError("declared-json-component-required")
                document = json.loads((directory / name).read_text())
                if row["kind"] == "SchemaContract":
                    if not isinstance(document, dict):
                        raise RegistryError("contract-object-required")
                    Draft202012Validator.check_schema(document)
        package = {"object": row, "components": components}
        rows.append({**package, "packageHash": digest(package)})
    body = {
        "schemaVersion": "evidence.nucleus/v0.1",
        "repository": repository,
        "revision": revision,
        "revisionVerified": False,
        "objects": rows,
    }
    return {**body, "snapshotHash": digest(body)}


def check_immutable(previous: dict[str, Any], current: dict[str, Any]) -> None:
    """Reject replacement or deletion of previously published object versions."""
    indexed = {item["object"]["objectId"]: item for item in current["objects"]}
    for item in previous["objects"]:
        if item["object"]["state"] == "published":
            new = indexed.get(item["object"]["objectId"])
            if new is None or new["packageHash"] != item["packageHash"]:
                raise RegistryError("published-version-changed-or-deleted")


def main(arguments: list[str] | None = None) -> None:
    """Emit a snapshot for caller-owned persistence; never fetch or execute sources."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--previous", type=Path)
    args = parser.parse_args(arguments)
    schemas = Path(__file__).resolve().parent / "resources" / "schemas"
    try:
        value = snapshot(Catalog(args.registry, schemas), args.repository, args.revision)
        if args.previous:
            check_immutable(json.loads(args.previous.read_text()), value)
    except (ValueError, KeyError, OSError, SchemaError) as exc:
        parser.exit(1, f"Snapshot rejected ({type(exc).__name__}).\n")
    print(json.dumps(value, indent=2, sort_keys=True))
