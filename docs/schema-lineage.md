# Shared schema and lineage catalog

Nucleus is reusable across projects. Project repositories own their definitions;
Nucleus indexes exact versions. `us-business-catalog` is the first intended
producer, not the owner of the platform. No organizational datasets, bindings,
or configuration are included in this addition.

## Implemented foundation

The local catalog recognizes seven additional inert package kinds:

| Kind | Records |
| --- | --- |
| Source | Stable source key, metadata fingerprint, source citation |
| SchemaContract | Published or inferred physical JSON Schema; semantic status |
| Mapping | Versioned mapping document referencing its physical contract |
| Run | Worker revision, run identity, outcome |
| Artifact | Object URI, content checksum, exact source/contract/run references |
| Lineage | Exact source and target versions; declared or observed evidence |
| Decision | Yes, no, or needs-review; subject version, actor, time, reason |

Each new kind requires `project`. IDs begin with `<project>--` to avoid collisions
between producers. References use `registry://Kind/id@version`. Runtime-observed
lineage requires an exact Run reference; that is a claim requiring producer
verification, not proof that an execution occurred. Inferred schemas do not
establish business meaning or completeness. A decision targets one exact version;
it does not approve later versions or grant execution authority.

The catalog API lists these packages. The offline snapshot command additionally
validates reference closure, typed evidence pointers, project-qualified IDs,
declared contract/mapping files, and JSON Schema structure. It hashes raw component
bytes, object packages, and the whole snapshot. It never fetches JSON Schema URLs
or executes package content. Contract contents remain in the source package;
snapshot receipts contain their checksums, not row data.

```bash
nucleus snapshot --registry /path/to/project/registry \
  --repository https://github.com/owner/project \
  --revision FULL_40_CHARACTER_COMMIT > snapshot.json
# On subsequent exports, add: --previous /trusted/path/previous-snapshot.json
```

The previous receipt is a trusted input. With it, changed or deleted published
identities are rejected; corrections require a new version. This check is not
yet wired into publishing or CI. The revision is caller-supplied and is explicitly
marked `revisionVerified: false`; the future sync adapter must verify clean,
pinned checkout bytes. Cross-project references require the referenced packages
in the same snapshot. Default user registry remains empty.

## Planned GitHub-driven delivery

GitHub is the initial metadata source of truth. No dedicated database or GCS
metadata store is required. The public Nucleus code repository remains separate
from project catalogs; private metadata stays in private repositories.

| GitHub location | Authority |
| --- | --- |
| Producer registry packages | Source definitions, schemas, mappings, declared lineage |
| Issues | Work queue and review state |
| Append-only structured issue comments | Run, decision, and observed-lineage receipts |
| Git commits and receipt comment IDs | Version citations and reproducible catalog inputs |

A static review site calls an authenticated API. That API reads pinned repository
files and structured issue receipts, validates them, and serves an ephemeral or
cached index. Cache loss is recoverable by reparsing GitHub. Source metadata has
explicit project, category, owner, citation, fingerprint, access/auth requirements,
and freshness; schema versions and diffs link back to exact source revisions.
No secrets or downloaded business rows belong in catalog receipts.

Yes / no / needs-review decisions append a receipt with actor, time, reason,
subject version, idempotency key, and superseded decision receipt. Actor identity
comes from verified authentication, never a client-supplied actor field. The API
compares the reviewed source version and current decision before acceptance;
concurrent conflicting decisions require reconciliation rather than silent
last-writer-wins. Receipts and schema files need a publication adapter before
these guarantees are enforced. GitHub issue comments are editable/deletable, so
checksums, linked receipt history, and reconciliation detect gaps or changes;
they do not make GitHub a tamper-proof audit ledger.

A GitHub App with narrowly scoped installation access handles repository reads,
receipt comments, and schema PRs. Tokens stay server-side. Source repository
permissions govern visibility; a project label is not an authorization boundary.
The API needs project authorization before reading or caching metadata. An
approved version never implicitly approves later versions or starts execution.

Verified webhooks can invalidate the cache; periodic polling reconciles missed
notifications, edits, and deletions. Pagination, rate-limit backoff, conditional
requests, and bounded reads keep the projection practical. Parse provider-specific
manifest/receipt formats through adapters rather than trusting issue prose.
Pub/Sub may later notify workers after GitHub persistence, with retry and
reconciliation. GCS may later store bulk raw ingestion files, referenced by URI
and checksum; it is not needed for the catalog metadata path.

## Next delivery

1. Parse pinned producer packages and GitHub receipt comments into one validated
   catalog projection, preserving every upstream identity and revision.
2. Add authenticated GitHub decision writes and conflict-safe receipt history.
3. Extend the static Library with source details, lineage traversal, schema
   version comparisons, mapping status, and change timelines.
4. Connect `us-business-catalog` as the first producer, then other projects.

The GitHub reader/writer adapters, authenticated write API, full catalog UI,
schema diffing, and producer integration remain unimplemented. The existing
server remains loopback-only and read-only. A database can later provide a
rebuildable search/graph index without changing GitHub's metadata authority.
