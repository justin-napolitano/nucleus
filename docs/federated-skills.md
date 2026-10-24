# Federated Anthropic skills

## Decision

Nucleus keeps a file-digest lock for 13 Apache-2.0 packages from
[`anthropics/skills`](https://github.com/anthropics/skills) at commit
`dbd4588f9e1033efb41dad4bef2f7947c8993d44`. It fetches the pinned public
source when a user explicitly installs skills. Nucleus also bundles exact
read-only snapshots of the 13 packages so their instructions, license, and
resource inventory are available for review in a fresh installed application.
The upstream repository remains the source of truth. Nucleus never runs the
bundled scripts.

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

## Review in Nucleus

Run `nucleus api` from a local installation and open the Library. The 13
bundled skills appear in `review` state. Expanding **Review skill definition**
shows the pinned `SKILL.md`, source commit/path, and license. The normal MCP
catalog tools exclude review candidates so an agent cannot load their
instructions before approval. The browser route is loopback-only; hosted
multi-user access and formal accept/reject controls remain planned work.

## Boundary

Installation copies verified files only. It does not run package scripts,
declare host compatibility, approve a candidate, or grant execution authority.
Generic source-repo skill discovery and the skills wiki
are tracked in [issue #15](https://github.com/justin-napolitano/nucleus/issues/15).
