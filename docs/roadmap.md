# Federated Nucleus roadmap

## Decision

Project repositories remain the source of truth. Nucleus pulls metadata at an
exact commit and presents a data wiki and skills wiki with source citations.
Repository files are inert input: catalog sync does not run migrations, dbt,
notebooks, skills, or workflows. A repo claim is not proof of deployed state.

## First usable path

1. [Register and sync repos](https://github.com/justin-napolitano/nucleus/issues/1)
   with a [provenance envelope](https://github.com/justin-napolitano/nucleus/issues/11).
2. Parse [migrations and contracts](https://github.com/justin-napolitano/nucleus/issues/12),
   [dbt dependency graphs](https://github.com/justin-napolitano/nucleus/issues/13),
   and [skills](https://github.com/justin-napolitano/nucleus/issues/15). Add
   [analytics assets](https://github.com/justin-napolitano/nucleus/issues/14)
   after choosing an example format.
3. Show the connected [data and skills wikis](https://github.com/justin-napolitano/nucleus/issues/2)
   in the [Library](https://github.com/justin-napolitano/nucleus/issues/5).
4. Add [identity and authorization](https://github.com/justin-napolitano/nucleus/issues/3),
   [source-cited chat](https://github.com/justin-napolitano/nucleus/issues/9),
   [API/MCP compatibility](https://github.com/justin-napolitano/nucleus/issues/6),
   and [authorized agent routing](https://github.com/justin-napolitano/nucleus/issues/7).

## Second pass

[Review the bundled skill candidates](https://github.com/justin-napolitano/nucleus/issues/18),
[review exact repo snapshots](https://github.com/justin-napolitano/nucleus/issues/4),
and [contribute through source-repo PRs](https://github.com/justin-napolitano/nucleus/issues/10).
Add [hosted operation](https://github.com/justin-napolitano/nucleus/issues/8)
after identity, durability, and revocation gates pass.

The current public code is a local read-only foundation with 13 bundled skill
review candidates and an optional Anthropic skill installer. It does not claim
generic wiki sync, source-repo review decisions, or hosted features above are
implemented.
