<!-- stage-runbook: true -->
# Bundled skill review candidates

## Status and boundary

The application now packages 13 pinned Anthropic skills as inert `review`
objects. A fresh installed wheel shows their metadata and instructions on
loopback UI/API; MCP excludes unapproved entries. No accept/reject workflow,
hosted multi-user identity, or execution authority is claimed.

## Stage ledger

| Stage | Result | Next action |
| --- | --- | --- |
| Source snapshot | PASS: 13 upstream packages copied byte for byte; 160 files match the pinned lock | Audit staged tree |
| Catalog | PASS: 13 review objects with exact source, license, and disabled execution | Validate installed wheel |
| Review UI/API | PASS: loopback API returns 13 review entries and instructions; browser automation through Edge returned 403 under cross-site policy | Use direct local browser for visual review |
| Validation | PASS: 11 tests, Ruff, 0.3.0 wheel, foundation and security PR checks | Merge PR |

## Current evidence

- `verify_bundled_candidate` across all 13 copied packages: PASS, exact file inventories and digests.
- `.venv/bin/pytest -q tests --tb=short`: PASS, 11 tests including review-only, source tamper, and MCP exclusion.
- `.venv/bin/ruff check .` and `.venv/bin/ruff format --check src/nucleus/*.py tests`: PASS. Bundled upstream code is excluded from formatting and linting.
- `UV_CACHE_DIR=/private/tmp/nucleus-uv-cache uv build`: PASS, 0.3.0 wheel. Wheel inspection found 13 `object.json`, 13 `SKILL.md`, and 13 `LICENSE.txt` files.
- Installed-wheel import from outside the checkout with a missing user registry: PASS, 13 `review` entries and readable instructions.
- Direct loopback `GET /v1/catalog?kind=Skill`: PASS, 200 with 13 disabled review candidates.
- Browser extension navigation: PARTIAL, returned 403 because the local server rejected its cross-site request. No visual claim.
- `git diff --cached --check`: PASS with vendored upstream files excluded from whitespace normalization through `.gitattributes`; their locked bytes remain unchanged.
- `gh pr checks 17 --repo justin-napolitano/nucleus`: PASS, foundation and GitGuardian checks.

## Remaining work

Merge the reviewed PR and record the merged result. Formal approve/reject controls and hosted identity
remain in issues #4, #8, and #10.

## PR handoff

Review upstream licensing and pinned digests, package inclusion, empty user
registry, review-state semantics, MCP exclusion, and the loopback-only
instructions route. The full upstream scripts are bundled as inert review
resources; Nucleus never imports or runs them.
