# Federated Anthropic skills

## Decision

Nucleus keeps a file-digest lock for 13 Apache-2.0 packages from
[`anthropics/skills`](https://github.com/anthropics/skills) at commit
`dbd4588f9e1033efb41dad4bef2f7947c8993d44`. It fetches the pinned public
source when a user explicitly installs skills. The skills remain upstream
owned; Nucleus does not vendor or execute their contents.

Anthropic describes `docx`, `pdf`, `pptx`, and `xlsx` as source-available under
separate terms. They are not in the lock or installer.

## Use on each machine

From a clone of this repository, install the Python package and choose a set:

```bash
python -m venv .venv
.venv/bin/pip install -e .
.venv/bin/nucleus skills list
.venv/bin/nucleus skills install frontend-design webapp-testing
.venv/bin/nucleus skills install --all --dest /path/to/other/skills
```

The default destination is `~/.codex/skills`. The command refuses an existing
skill directory. Each installed folder includes its upstream `LICENSE.txt`
and a `.nucleus-source.json` receipt naming the repo, commit, and path. Reopen
Codex after installation. To change a skill, review and update the source lock
in a new commit; the installer never silently follows the upstream branch.

## Boundary

Installation copies verified files only. It does not run package scripts,
declare host compatibility, publish a skill in the Nucleus catalog, or grant
execution authority. Generic source-repo skill discovery and the skills wiki
are tracked in [issue #15](https://github.com/justin-napolitano/nucleus/issues/15).
