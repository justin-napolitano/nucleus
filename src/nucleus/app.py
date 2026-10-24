"""Loopback Nucleus catalog API and read-only MCP endpoint."""

from __future__ import annotations

import argparse
import json
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

from nucleus.mcp import handle_message
from nucleus.registry import KINDS, Catalog, RegistryError
from nucleus.skills import load_lock

MAX_REQUEST = 1_000_000
TOOLS = [
    {
        "name": "nucleus_list_objects",
        "description": "List published registry metadata; registration does not grant execution.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "kind": {"type": "string", "enum": list(KINDS)},
                "query": {"type": "string", "maxLength": 200},
                "offset": {"type": "integer", "minimum": 0},
                "limit": {"type": "integer", "minimum": 1, "maximum": 100},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "nucleus_get_object",
        "description": "Read one exact published registry object by its returned ID.",
        "inputSchema": {
            "type": "object",
            "properties": {"object_id": {"type": "string", "maxLength": 250}},
            "required": ["object_id"],
            "additionalProperties": False,
        },
    },
]


def invoke(catalog: Catalog, name: str, arguments: Any) -> dict[str, Any]:
    """Map only approved read tools to bounded catalog operations."""
    if not isinstance(arguments, dict):
        raise ValueError("invalid-arguments")
    if name == "nucleus_list_objects" and set(arguments) <= {"kind", "query", "offset", "limit"}:
        kind, query = arguments.get("kind", ""), arguments.get("query", "")
        offset, limit = arguments.get("offset", 0), arguments.get("limit", 25)
        if (
            not isinstance(kind, str)
            or not isinstance(query, str)
            or type(offset) is not int
            or type(limit) is not int
        ):
            raise ValueError("invalid-arguments")
        return catalog.list(kind=kind, query=query, offset=offset, limit=limit, published_only=True)
    if (
        name == "nucleus_get_object"
        and set(arguments) == {"object_id"}
        and isinstance(arguments["object_id"], str)
    ):
        return catalog.get(arguments["object_id"], published_only=True)
    raise ValueError("unknown-or-invalid-tool")


def make_server(catalog: Catalog, static: Path, port: int) -> ThreadingHTTPServer:
    """Compose a loopback-only request host; no external source adapter is mounted."""
    assets = {
        "/": ("index.html", "text/html; charset=utf-8"),
        "/app.js": ("app.js", "text/javascript; charset=utf-8"),
        "/style.css": ("style.css", "text/css; charset=utf-8"),
    }

    class Handler(BaseHTTPRequestHandler):
        """Serve fixed routes with strict host and body bounds."""

        def _allowed(self) -> bool:
            """Reject cross-site requests and non-loopback Host authorities."""
            return (
                self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}"
                and self.headers.get("Origin")
                in (None, f"http://127.0.0.1:{self.server.server_port}")
                and self.headers.get("Sec-Fetch-Site") != "cross-site"
            )

        def _send(self, status: int, body: bytes, content_type: str = "application/json") -> None:
            """Send bounded, uncached responses without reflecting request content."""
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, status: int, value: dict[str, Any]) -> None:
            """Encode API metadata without writing it to logs."""
            self._send(status, json.dumps(value).encode("utf-8"))

        def do_GET(self) -> None:
            """Serve health, catalog metadata, and the static Library shell."""
            if not self._allowed():
                self._json(403, {"error": "forbidden"})
                return
            route = urlsplit(self.path)
            if route.path in assets and not route.query:
                filename, content_type = assets[route.path]
                self._send(200, (static / filename).read_bytes(), content_type)
                return
            try:
                if route.path == "/health" and not route.query:
                    payload = {"status": "ok", "service": "nucleus", "mode": "local-read-only"}
                elif route.path == "/v1/capabilities" and not route.query:
                    payload = {
                        "kinds": list(KINDS),
                        "catalogWrite": False,
                        "sourceExecution": False,
                        "mcpTools": [tool["name"] for tool in TOOLS],
                    }
                elif route.path in {"/v1/catalog", "/v1/catalog/object", "/v1/review/skill"}:
                    params = parse_qs(route.query, strict_parsing=True)
                    if any(len(values) != 1 for values in params.values()):
                        raise ValueError("invalid-query")
                    args = {key: values[0] for key, values in params.items()}
                    if route.path == "/v1/review/skill":
                        if set(args) != {"object_id"}:
                            raise ValueError("invalid-query")
                        payload = catalog.review_skill(args["object_id"])
                    elif route.path.endswith("/object"):
                        if set(args) != {"object_id"}:
                            raise ValueError("invalid-query")
                        payload = catalog.get(args["object_id"])
                    else:
                        if set(args) - {"kind", "query", "offset", "limit"}:
                            raise ValueError("invalid-query")
                        payload = catalog.list(
                            kind=args.get("kind", ""),
                            query=args.get("query", ""),
                            offset=int(args.get("offset", "0")),
                            limit=int(args.get("limit", "25")),
                        )
                else:
                    self._json(404, {"error": "not-found"})
                    return
                self._json(200, payload)
            except (ValueError, RegistryError):
                self._json(400, {"error": "invalid-request-or-registry"})
            except KeyError:
                self._json(404, {"error": "not-found"})

        def do_POST(self) -> None:
            """Handle a single read-only MCP message on the fixed endpoint."""
            if not self._allowed():
                self._json(403, {"error": "forbidden"})
                return
            if self.path != "/mcp":
                self._json(404, {"error": "not-found"})
                return
            try:
                length = int(self.headers.get("Content-Length", ""))
                if not 0 < length <= MAX_REQUEST:
                    raise ValueError("invalid-length")
                body = self.rfile.read(length)
                status, result = handle_message(
                    body, TOOLS, lambda name, args: invoke(catalog, name, args)
                )
                if result is None:
                    self._send(status, b"")
                else:
                    self._json(status, result)
            except (ValueError, RegistryError):
                self._json(400, {"error": "invalid-request-or-registry"})

        def log_message(self, format: str, *args: object) -> None:
            """Keep request paths and package metadata out of process logs."""

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def main() -> None:
    """Run the local API or stdio MCP against an explicit empty-or-populated registry."""
    if sys.argv[1:2] == ["skills"]:
        from nucleus.skills import main as skills_main

        skills_main(sys.argv[2:])
        return
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("api", "mcp"))
    parser.add_argument("--registry", type=Path, default=Path("registry"))
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    package = Path(__file__).resolve().parent
    resources = package / "resources"
    catalog = Catalog(
        args.registry,
        resources / "schemas",
        resources / "registry",
        load_lock(),
    )
    if args.mode == "mcp":
        for line in sys.stdin.buffer:
            if len(line) > MAX_REQUEST:
                continue
            status, result = handle_message(
                line, TOOLS, lambda name, values: invoke(catalog, name, values)
            )
            if status != HTTPStatus.ACCEPTED and result is not None:
                print(json.dumps(result), flush=True)
        return
    if not 1 <= args.port <= 65535:
        parser.error("invalid-port")
    server = make_server(catalog, package / "resources" / "web", args.port)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
