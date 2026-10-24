# Registry

This repository intentionally ships with no domain, metric, data product, skill,
workflow, tool, MCP server, or agent registrations. The Library starts empty.

Add reviewed packages under `<kind-directory>/<id>/<version>/object.json`.
The eight supported kind directories are listed in `schemas/` and in the API
capabilities response. Referenced package files must stay within that version
directory. A registration is discoverable metadata; it cannot grant access or
activate source execution.
