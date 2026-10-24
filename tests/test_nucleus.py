"""Synthetic tests for the empty public default and bounded read routes."""

from __future__ import annotations

import json
import threading
from http.client import HTTPConnection
from pathlib import Path

import pytest

from nucleus.app import TOOLS, invoke, make_server
from nucleus.mcp import handle_message
from nucleus.registry import Catalog, RegistryError

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "src" / "nucleus" / "resources" / "schemas"
WEB = ROOT / "src" / "nucleus" / "resources" / "web"


def test_public_registry_starts_empty() -> None:
    """No organizational package may ship in the default registry."""
    catalog = Catalog(ROOT / "registry", SCHEMAS)
    assert catalog.list() == {"items": [], "total": 0, "offset": 0, "limit": 25, "nextOffset": None}
    assert not list((ROOT / "registry").glob("*/*/*/object.json"))


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
    catalog = Catalog(ROOT / "registry", SCHEMAS)
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


def test_loopback_http_api_denies_wrong_host() -> None:
    """The local API reports an empty catalog and rejects a forged Host."""
    catalog = Catalog(ROOT / "registry", SCHEMAS)
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
        assert json.loads(response.read())["total"] == 0
        connection.request("GET", "/v1/capabilities", headers={"Host": "remote.example"})
        response = connection.getresponse()
        assert response.status == 403
        response.read()
    finally:
        connection.close()
        server.shutdown()
        server.server_close()
        worker.join(timeout=3)
