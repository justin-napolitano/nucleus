"""Fictional multi-project evidence tests; no provider payloads or credentials."""

import json
from pathlib import Path

import pytest

from nucleus.evidence import check_immutable, snapshot
from nucleus.registry import Catalog, RegistryError

SCHEMAS = Path(__file__).resolve().parents[1] / "src/nucleus/resources/schemas"


def package(root, kind, collection, name, **fields):
    """Build an independent project-scoped package for each test."""
    directory = root / collection / name / "1.0.0"
    directory.mkdir(parents=True)
    value = {
        "schemaVersion": "registry.nucleus/v0.1",
        "kind": kind,
        "id": name,
        "version": "1.0.0",
        "state": "published",
        "project": "demo",
        "displayName": name,
        "description": "Fictional metadata",
        "owners": [{"type": "user", "id": "example-owner"}],
        "files": [],
        "references": [],
        **fields,
    }
    (directory / "object.json").write_text(json.dumps(value))
    return f"registry://{kind}/{name}@1.0.0", directory


def fixture(root):
    """Create source, physical contract, and a declared lineage edge."""
    source, _ = package(
        root,
        "Source",
        "sources",
        "demo--source",
        sourceKey="fictional:source",
        metadataFingerprint="sha256:" + "a" * 64,
        citation="https://example.invalid/catalog",
    )
    contract, path = package(
        root,
        "SchemaContract",
        "schema-contracts",
        "demo--contract",
        sourceRef=source,
        origin="inferred",
        semanticStatus="unknown",
        contractFile="record.json",
        files=["record.json"],
        references=[source],
    )
    (path / "record.json").write_text(
        json.dumps(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
                "properties": {"identifier": {"type": "string"}},
            }
        )
    )
    _, edge = package(
        root,
        "Lineage",
        "lineage",
        "demo--lineage",
        sourceRef=source,
        targetRef=contract,
        evidence="source-declared",
        references=[source, contract],
    )
    return Catalog(root, SCHEMAS), path, edge


def compile_fixture(catalog):
    """Use an explicitly unverified commit claim in offline snapshots."""
    return snapshot(catalog, "https://example.invalid/repo", "a" * 40)


def test_contract_content_hash_and_immutable_history(tmp_path):
    """Changing bytes under a published identity is detected against a prior receipt."""
    catalog, path, _ = fixture(tmp_path)
    original = compile_fixture(catalog)
    assert original == compile_fixture(catalog)
    assert original["revisionVerified"] is False
    (path / "record.json").write_text('{"type":"object"}')
    changed = compile_fixture(catalog)
    assert changed["snapshotHash"] != original["snapshotHash"]
    with pytest.raises(RegistryError, match="published-version-changed"):
        check_immutable(original, changed)


def test_unresolved_and_wrong_kind_pointers_rejected(tmp_path):
    """A valid-looking reference must resolve to the required exact object kind."""
    catalog, path, _ = fixture(tmp_path)
    manifest = path / "object.json"
    value = json.loads(manifest.read_text())
    value["sourceRef"] = "registry://Source/demo--missing@1.0.0"
    manifest.write_text(json.dumps(value))
    with pytest.raises(RegistryError, match="unresolved-evidence-pointer"):
        compile_fixture(catalog)
    value["sourceRef"] = "registry://SchemaContract/demo--contract@1.0.0"
    value["references"].append(value["sourceRef"])
    manifest.write_text(json.dumps(value))
    with pytest.raises(RegistryError, match="wrong-evidence-kind"):
        compile_fixture(catalog)


def test_runtime_lineage_requires_run(tmp_path):
    """A declaration cannot silently claim observed execution without a run reference."""
    catalog, _, edge = fixture(tmp_path)
    manifest = edge / "object.json"
    value = json.loads(manifest.read_text())
    value["evidence"] = "runtime-observed"
    manifest.write_text(json.dumps(value))
    with pytest.raises(RegistryError, match="invalid-object"):
        compile_fixture(catalog)
    run, _ = package(
        tmp_path,
        "Run",
        "runs",
        "demo--run",
        runId="fictional-1",
        workerRevision="b" * 40,
        outcome="succeeded",
    )
    value["runRef"] = run
    value["references"].append(run)
    manifest.write_text(json.dumps(value))
    assert len(compile_fixture(catalog)["objects"]) == 4


def test_project_prefix_and_deleted_published_versions(tmp_path):
    """Project-qualified IDs avoid collisions; published history cannot disappear."""
    catalog, path, edge = fixture(tmp_path)
    original = compile_fixture(catalog)
    manifest = path / "object.json"
    value = json.loads(manifest.read_text())
    value["project"] = "other"
    manifest.write_text(json.dumps(value))
    with pytest.raises(RegistryError, match="project-qualified-id-required"):
        compile_fixture(catalog)
    value["project"] = "demo"
    manifest.write_text(json.dumps(value))
    (edge / "object.json").unlink()
    with pytest.raises(RegistryError, match="published-version-changed-or-deleted"):
        check_immutable(original, compile_fixture(catalog))


def test_decisions_pin_subject_and_preserve_prior_choice(tmp_path):
    """Successive choices can coexist; supersession references an exact prior decision."""
    catalog, _, _ = fixture(tmp_path)
    subject = "registry://SchemaContract/demo--contract@1.0.0"
    first, _ = package(
        tmp_path,
        "Decision",
        "decisions",
        "demo--decision-one",
        subjectRef=subject,
        choice="yes",
        actor="fictional-reviewer",
        recordedAt="2026-10-28T00:00:00Z",
        reason="Fictional review",
        references=[subject],
    )
    old = compile_fixture(catalog)
    package(
        tmp_path,
        "Decision",
        "decisions",
        "demo--decision-two",
        subjectRef=subject,
        choice="no",
        actor="fictional-reviewer",
        recordedAt="2026-10-28T01:00:00Z",
        reason="Fictional correction",
        supersedesRef=first,
        references=[subject, first],
    )
    new = compile_fixture(catalog)
    check_immutable(old, new)
    choices = [
        item["object"]["choice"] for item in new["objects"] if item["object"]["kind"] == "Decision"
    ]
    assert sorted(choices) == ["no", "yes"]
