# Nucleus

Nucleus is an open source foundation for discovering governed data products and
agent capabilities. Its user registry starts empty: it contains no
organizational domains, metrics, products, credentials, or source bindings.
The application bundles 13 pinned Apache-2.0 Anthropic skill snapshots as
**review candidates**. They are visible in the Library and remain unapproved
and non-executable in Nucleus.

## What works now

- A local Library UI and read-only catalog API.
- A bundled review queue with the 13 skill instructions, source paths, commit,
  licenses, and file inventories, available from an installed package.
- Versioned JSON Schema contracts for domains, products, metrics, skills,
  workflows, tools, MCP servers, and agents.
- A read-only MCP endpoint with `nucleus_list_objects` and
  `nucleus_get_object` tools. Review candidates are excluded from those agent
  tools until an approval workflow exists.
- Immediate correction and deletion readback from local registry packages.
- Fail-closed package validation and a fixed loopback host. Capability
  declarations never activate execution.
- Offline discovery and explicit local installation of 13 pinned Anthropic
  skills, with file digest and license verification.

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

Open <http://127.0.0.1:8765/>. The Library should show 13 review candidates. The API
health endpoint is `/health`; `/v1/capabilities` lists the supported kinds and
tools. `POST /mcp` accepts bounded JSON-RPC MCP requests. A local stdio mode is
also available with `.venv/bin/nucleus mcp --registry registry`.

## Define a package

Choose a kind schema in [`schemas/`](src/nucleus/resources/schemas/) and put its `object.json` under
the corresponding directory in `registry/`. Package files named in `files`
must be present under the same version directory. An object becomes visible in
the Library but remains `executionEligible: false`. The external registry
contains no sample domain package; tests create fictional packages in
temporary directories.

## Use Anthropic skills on a machine

Git is required for the pinned public source fetch during machine installation.
The application bundles review snapshots, but does not install or activate
skills in an agent automatically.

```bash
.venv/bin/nucleus skills list
.venv/bin/nucleus skills install frontend-design mcp-builder
# Or install the full reviewed Apache-2.0 set:
.venv/bin/nucleus skills install --all
```

The default destination is `~/.codex/skills`; use `--dest /path/to/skills` for
another local agent or a disposable proof. Existing skill directories are never
overwritten. Start a new Codex session after installing. The four Anthropic
document skills with separate terms are excluded. See the
[federated skills guide](docs/federated-skills.md) for provenance and limits.

## Development

The [shared schema and lineage catalog](docs/schema-lineage.md) adds project-scoped
source, contract, mapping, run, artifact, lineage, and decision package contracts,
plus an offline `nucleus snapshot` verifier. The hosted static review site and
authenticated GitHub decision API described there are planned, not deployed.
GitHub files, issues, and structured receipts are the planned metadata authority;
Nucleus builds a rebuildable read projection without a dedicated database.

```bash
.venv/bin/pip install -e '.[dev]'
.venv/bin/pytest -q
.venv/bin/ruff check .
```

The [API and MCP contract](docs/api-mcp.md) and [parity roadmap](docs/roadmap.md)
describe the current boundary. Contributions should preserve the empty default
registry and the separation between registration, authorization, and execution.

Licensed under [Apache-2.0](LICENSE).
