# API and MCP v0.1

## Local routes

| Route | Meaning |
| --- | --- |
| `GET /` | Library UI |
| `GET /health` | Local server status |
| `GET /v1/capabilities` | Supported registry kinds and read tools |
| `GET /v1/catalog` | Bounded metadata page; `kind`, `query`, `offset`, `limit` filters |
| `GET /v1/catalog/object?object_id=...` | Exact returned object identity |
| `POST /mcp` | MCP JSON-RPC endpoint |

The MCP server supports `initialize`, `ping`, `tools/list`, and `tools/call`.
`nucleus_list_objects` accepts optional `kind`, `query`, `offset`, and `limit`.
`nucleus_get_object` requires an `object_id` returned by the catalog. Both are
read-only. All responses mark registered objects as ineligible for execution.

The server binds to `127.0.0.1`. It rejects other Host authorities and
cross-site browser requests. It has no login system, write API, provider
connection, hosted execution route, or enterprise deployment profile.
