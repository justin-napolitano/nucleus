<!-- stage-runbook: true -->
# Federated Anthropic skills review

## Status and boundary

The public branch adds an optional pinned-source installer for 13 reviewed
Apache-2.0 Anthropic skills. It does not bundle skill bodies, register them in
the runtime catalog, or run scripts. The four separately licensed document
skills remain excluded. The broader repo sync and wikis are open issues.

## Stage ledger

| Stage | Result | Next action |
| --- | --- | --- |
| Source and license | PASS: pinned public commit checked out; 13 inventories and license digests matched | Retain exact pin in review |
| Installer | PASS: all 13 installed to a disposable root and this machine's Codex skills root with receipts | Verify after merge |
| Synthetic checks | PASS: 9 tests, Ruff, and 0.2.0 wheel build | Run public CI |
| Federation plan | PASS: issues #1–#15 now distinguish repo sync, extraction, typed adapters, wikis, and source-repo review | Merge plan with installer |

## Current evidence

- `git -C /private/tmp/nucleus-anthropic-upstream checkout --detach dbd4588f9e1033efb41dad4bef2f7947c8993d44`: PASS.
- `verify_package` across the 13 locked names: PASS, 160 source files matched.
- `.venv/bin/pytest -q tests/test_skills.py --tb=short`: PASS, 4 tests.
- `.venv/bin/pytest -q tests --tb=short`: PASS, 9 tests.
- `.venv/bin/ruff check .`: PASS.
- `.venv/bin/nucleus skills install --all --dest /private/tmp/nucleus-anthropic-proof`: PASS, 13 installed with explicit source receipts.
- `.venv/bin/nucleus skills install --all --dest ~/.codex/skills`: PASS, 13 installed on this machine using the equivalent absolute destination; installed hashes rechecked against the lock.
- `UV_CACHE_DIR=/private/tmp/nucleus-uv-cache uv build`: PASS, 0.2.0 source archive and wheel.
- Installed the 0.2.0 wheel in a disposable environment and ran `nucleus skills list` from outside the checkout: PASS, all 13 names returned offline.

## Remaining work

Inspect the exact public diff, review/merge the PR, and verify CI. Generic
skills-wiki sync remains tracked in issue #15. Other machines run the documented
install command locally.

## PR handoff

Review lock provenance, license exclusions, no-code-execution install path,
destination overwrite/rollback behavior, docs, and synthetic tests. Public
default registry remains empty.
