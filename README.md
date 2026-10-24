# Nucleus

Nucleus is an open source foundation for discovering governed data products and
agent capabilities. This repository starts with an **empty registry**. It
contains no organizational data domains, metrics, products, skill selections,
credentials, or source bindings.

## What works now

- A local Library UI and read-only catalog API.
- Versioned JSON Schema contracts for domains, products, metrics, skills,
  workflows, tools, MCP servers, and agents.
- A read-only MCP endpoint with `nucleus_list_objects` and
  `nucleus_get_object` tools.
- Immediate correction and deletion readback from local registry packages.
- Fail-closed package validation and a fixed loopback host. Capability
  declarations never activate execution.

This is the public foundation. Enterprise identity, authoring and approval,
hosted execution, and parity with the private Nucleus application remain
planned work. Do not expose the local server beyond your machine.

## Run locally

Python 3.11 or newer is required.

```bash
python -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/nucleus api --registry registry --port 8765
```

Open <http://127.0.0.1:8765/>. The Library should report zero items. The API
health endpoint is `/health`; `/v1/capabilities` lists the supported kinds and
tools. `POST /mcp` accepts bounded JSON-RPC MCP requests. A local stdio mode is
also available with `.venv/bin/nucleus mcp --registry registry`.

## Define a package

Choose a kind schema in [`schemas/`](src/nucleus/resources/schemas/) and put its `object.json` under
the corresponding directory in `registry/`. Package files named in `files`
must be present under the same version directory. An object becomes visible in
the Library but remains `executionEligible: false`. The repository contains no
sample domain package; tests create fictional packages in temporary directories.

## Development

```bash
.venv/bin/pip install -e '.[dev]'
.venv/bin/pytest -q
.venv/bin/ruff check .
```

The [API and MCP contract](docs/api-mcp.md) and [parity roadmap](docs/roadmap.md)
describe the current boundary. Contributions should preserve the empty default
registry and the separation between registration, authorization, and execution.

Licensed under [Apache-2.0](LICENSE).
