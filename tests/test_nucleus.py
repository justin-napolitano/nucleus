"""Synthetic tests for the empty user registry and bundled review candidates."""

from __future__ import annotations

import json
import shutil
import threading
from http.client import HTTPConnection
from pathlib import Path

import pytest

from nucleus.app import TOOLS, invoke, make_server
from nucleus.mcp import handle_message
from nucleus.registry import Catalog, RegistryError
from nucleus.skills import SkillSourceError, load_lock

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "src" / "nucleus" / "resources" / "schemas"
WEB = ROOT / "src" / "nucleus" / "resources" / "web"
BUILTIN = ROOT / "src" / "nucleus" / "resources" / "registry"


def test_external_registry_starts_empty() -> None:
    """No organizational package ships in the user-controlled registry."""
    catalog = Catalog(ROOT / "registry", SCHEMAS)
    assert catalog.list() == {"items": [], "total": 0, "offset": 0, "limit": 25, "nextOffset": None}
    assert not list((ROOT / "registry").glob("*/*/*/object.json"))


def test_bundled_skills_are_review_only() -> None:
    """All pinned skill candidates appear with source evidence and no authority."""
    catalog = Catalog(ROOT / "registry", SCHEMAS, BUILTIN, load_lock())
    rows = catalog.list(kind="Skill")
    assert rows["total"] == 13
    assert all(
        row["state"] == "review" and row["executionEligible"] is False for row in rows["items"]
    )
    identity = "registry://Skill/anthropic-frontend-design@0.0.0-dbd4588f"
    item = catalog.get(identity)
    assert "instructionsText" not in item
    review = catalog.review_skill(identity)
    assert "frontend-design" in review["instructionsText"]
    assert item["source"]["commit"] == load_lock()["commit"]


def test_bundled_skill_change_fails_closed(tmp_path: Path) -> None:
    """A missing or changed bundled candidate cannot silently enter review."""
    copied = tmp_path / "bundled"
    shutil.copytree(BUILTIN, copied)
    catalog = Catalog(tmp_path / "not-created", SCHEMAS, copied, load_lock())
    assert catalog.list(kind="Skill")["total"] == 13
    package = copied / "skills" / "anthropic-frontend-design" / "0.0.0-dbd4588f"
    (package / "SKILL.md").write_text("Changed instructions.\n")
    with pytest.raises(SkillSourceError):
        catalog.list(kind="Skill")
    (package / "SKILL.md").unlink()
    with pytest.raises(RegistryError):
        catalog.list(kind="Skill")


def test_synthetic_domain_is_discoverable_then_removed(tmp_path: Path) -> None:
    """A fictional package is validated and deletion takes effect on the next read."""
    package = tmp_path / "data-domains" / "demo-domain" / "0.1.0"
    package.mkdir(parents=True)
    object_file = package / "object.json"
    object_file.write_text(
        json.dumps(
            {
                "schemaVersion": "registry.nucleus/v0.1",
                "kind": "DataDomain",
                "id": "demo-domain",
                "version": "0.1.0",
                "state": "draft",
                "displayName": "Demo domain",
                "description": "Fictional fixture",
                "owners": [{"type": "team", "id": "demo-team"}],
                "files": [],
                "references": [],
                "classification": "public",
                "stewardship": {"accountableTeam": "demo-team", "reviewCadence": "annual"},
            }
        )
    )
    catalog = Catalog(tmp_path, SCHEMAS)
    rows = catalog.list(kind="DataDomain")
    assert rows["total"] == 1
    assert rows["items"][0]["executionEligible"] is False
    assert invoke(catalog, "nucleus_list_objects", {"kind": "DataDomain"})["total"] == 0
    identity = rows["items"][0]["objectId"]
    assert catalog.get(identity)["displayName"] == "Demo domain"
    object_file.unlink()
    assert catalog.list()["total"] == 0
    with pytest.raises(KeyError):
        catalog.get(identity)


def test_invalid_package_fails_closed(tmp_path: Path) -> None:
    """A malformed registered package cannot be silently skipped."""
    package = tmp_path / "skills" / "demo-skill" / "0.1.0"
    package.mkdir(parents=True)
    (package / "object.json").write_text('{"kind":"Skill"}')
    with pytest.raises(RegistryError):
        Catalog(tmp_path, SCHEMAS).list()


def test_mcp_has_only_read_tools_and_rejects_unknown_calls() -> None:
    """MCP advertises two read operations and no execution or write capability."""
    catalog = Catalog(ROOT / "registry", SCHEMAS, BUILTIN, load_lock())
    assert [item["name"] for item in TOOLS] == ["nucleus_list_objects", "nucleus_get_object"]
    status, response = handle_message(
        json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}).encode(),
        TOOLS,
        lambda name, args: invoke(catalog, name, args),
    )
    assert status == 200 and response["result"]["tools"] == TOOLS
    with pytest.raises(ValueError):
        invoke(catalog, "nucleus_execute_tool", {})
    with pytest.raises(ValueError):
        invoke(catalog, "nucleus_list_objects", {"limit": 10000})
    assert invoke(catalog, "nucleus_list_objects", {"kind": "Skill"})["total"] == 0
    with pytest.raises(KeyError):
        invoke(
            catalog,
            "nucleus_get_object",
            {"object_id": "registry://Skill/anthropic-frontend-design@0.0.0-dbd4588f"},
        )


def test_loopback_http_api_denies_wrong_host() -> None:
    """The local API shows review candidates and rejects a forged Host."""
    catalog = Catalog(ROOT / "registry", SCHEMAS, BUILTIN, load_lock())
    server = make_server(catalog, WEB, 0)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    connection = HTTPConnection("127.0.0.1", server.server_port, timeout=3)
    try:
        connection.request("GET", "/health")
        response = connection.getresponse()
        assert response.status == 200
        assert json.loads(response.read())["mode"] == "local-read-only"
        connection.request("GET", "/v1/catalog")
        response = connection.getresponse()
        assert json.loads(response.read())["total"] == 13
        connection.request(
            "GET",
            "/v1/review/skill?object_id=registry%3A%2F%2FSkill%2Fanthropic-frontend-design%400.0.0-dbd4588f",
        )
        response = connection.getresponse()
        assert response.status == 200
        assert "frontend-design" in json.loads(response.read())["instructionsText"]
        connection.request("GET", "/v1/capabilities", headers={"Host": "remote.example"})
        response = connection.getresponse()
        assert response.status == 403
        response.read()
    finally:
        connection.close()
        server.shutdown()
        server.server_close()
        worker.join(timeout=3)
