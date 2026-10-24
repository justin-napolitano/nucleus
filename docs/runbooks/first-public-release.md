<!-- stage-runbook: true -->
# First public release

## Status and boundary

Published Apache-2.0 standalone Nucleus foundation. The default
registry is empty. It serves a local catalog UI/API and read-only MCP tools.
It has no enterprise sign-in, hosted execution, source adapters, approval flow,
or parity claim with the private application.

## Stage ledger

| Stage | Evidence and result | Next action |
| --- | --- | --- |
| Selection | PASS: exact staged tree contains only generic contracts, local runtime, UI, docs, and synthetic tests; organizational registries excluded | Maintain boundary in future PRs |
| Package | PASS: wheel contains schemas, UI assets, and Apache license | Keep packaging verified in CI |
| Behavior | PASS: five synthetic tests and installed-wheel MCP smoke test | Extend with future features |
| Publication | PASS: GitHub reports PUBLIC and Apache-2.0; first Verify workflow passed | Begin parity work in separate PRs |

## Current evidence

- `.venv/bin/pytest -q tests --tb=short`: PASS, 5 tests.
- `.venv/bin/ruff check .`: PASS.
- `.venv/bin/ruff format --check src tests`: PASS.
- `UV_CACHE_DIR=/private/tmp/nucleus-uv-cache uv build`: PASS, source archive and wheel.
- Installed the wheel in an isolated temporary environment, then invoked
  `nucleus mcp --registry registry` with a synthetic `nucleus_list_objects`
  request: PASS, empty catalog returned.
- Scanned source, docs, registry, and manifests for organizational names,
  private hosts, and source bindings: PASS, no such content found.
- `git diff --cached --check`: PASS. `git grep --cached` for organizational
  names, account identifiers, source bindings, and credential markers found
  only the intentional `*.secret*` ignore rule.
- `gh repo view justin-napolitano/nucleus --json name,visibility,url,licenseInfo,defaultBranchRef`:
  PASS, public `main`, GitHub recognized Apache-2.0.
- `gh run watch 40060526616 --repo justin-napolitano/nucleus --exit-status`:
  PASS, first foundation workflow.

## Remaining work

Identity, authoring, hosted execution, and private application parity are
separate delivery units in the roadmap.

## PR handoff

The initial release has fresh standalone history and no private-repo ancestry.
Future PRs should review each parity unit against the roadmap. Organizational
registry instances and third-party skill packages stay excluded.
