# Agent Memory — komodo-infra

- [Komodo stack environment literal-newline quirk](feedback_komodo_env_newlines.md) — km update stack stores \n literally; Komodo periphery converts to real newlines only on actual container recreation
- [MCP server fleet auth migration](project_mcp_auth_oidcproxy.md) — OIDCProxy migration completed 2026-04-05; CLIENT_ID/SECRET replace AUDIENCE/API_KEY across all MCP stacks
- [instaloader-mcp not in Komodo DB](reference_instaloader_komodo_status.md) — Container runs via Komodo stack dir but stack is not registered in Komodo DB; deploy manually via SSH
