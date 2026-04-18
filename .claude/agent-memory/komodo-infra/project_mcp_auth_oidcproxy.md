---
name: MCP server OIDCProxy auth migration
description: Migration of all MCP servers from API key / KEYCLOAK_AUDIENCE auth to OIDCProxy (KEYCLOAK_CLIENT_ID + KEYCLOAK_CLIENT_SECRET), completed 2026-04-05
type: project
---

All MCP servers migrated to OIDCProxy auth on 2026-04-05. The new pattern uses `KEYCLOAK_CLIENT_ID` and `KEYCLOAK_CLIENT_SECRET` instead of `MCP_API_KEY`/`MCP_HTTP_AUTH_TOKEN`/`KEYCLOAK_AUDIENCE`.

**KEYCLOAK_ISSUER** for all servers: `https://auth.cdit-works.de/realms/cdit-mcp`

Affected Komodo stacks (all updated):
- `git-mcp-siyuan` (ubuntu-smurf-mirror) — CLIENT_ID=mcp-siyuan
- `git-mcp-klartext` (ubuntu-smurf-mirror) — CLIENT_ID=mcp-klartext
- `git-mcp-writings` (ubuntu-smurf-mirror) — CLIENT_ID=mcp-writings (uses ghcr.io image)
- `git-mcp-zernio` (ubuntu-smurf-mirror) — CLIENT_ID=mcp-zernio
- `git-mcp-lexoffice` (werkstatt-1) — CLIENT_ID=mcp-lexoffice (compose file: docker-compose.yml)
- `ytdlp-mcp` (ubuntu-smurf-mirror) — CLIENT_ID=mcp-ytdlp (port 8718, not 8000)
- `instaloader-mcp` (ubuntu-smurf-mirror) — CLIENT_ID=mcp-instaloader (NOT in Komodo DB)

**mcp-things**: Runs locally on macOS, already updated separately.
**mcp-outbank**: No stack exists anywhere — not yet deployed.

**Why:** Auth simplification to OIDCProxy pattern pushed to all repos simultaneously.

**How to apply:** If adding a new MCP server, use CLIENT_ID/CLIENT_SECRET pattern. The old AUDIENCE/API_KEY vars are no longer needed in compose environment blocks.
