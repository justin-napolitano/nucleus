# Parity roadmap

## Current foundation

The public repo has the catalog model, empty Library, read-only API/MCP, and
generic domain, product, metric, skill, workflow, tool, MCP-server and agent
contracts. It has a fresh history and no organizational packages.

## Next delivery units

1. Move the private Nucleus identity and authorization model behind portable
   adapters, with synthetic local proof and no organization-specific defaults.
2. Add governed authoring proposals, owner review, immutable release receipts,
   and Git-backed domain/skill/workflow registration.
3. Port the full frontend and parity tests after removing organizational
   content, private hostnames, and deployment-specific routes.
4. Add optional hosted MCP/API deployment only after identity, revocation,
   durability and source-execution gates pass.

External skill packages are not bundled. A future optional plugin can use
upstream packages only after its own license, owner selection, and host review.
