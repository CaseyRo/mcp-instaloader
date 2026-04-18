---
name: Komodo stack environment newline handling
description: km update stack stores \n as literal characters; only converted to real newlines by Komodo periphery when it writes .env during an actual container recreation (not a no-op deploy)
type: feedback
---

`km update stack <name> "environment=KEY1=val1\nKEY2=val2"` stores the `\n` as literal backslash-n in Komodo's DB. The Komodo periphery agent converts them to real newlines when it writes the `.env` file to disk — but only during a deploy that actually recreates the container (e.g., image changed, first deploy, or `--force-recreate`).

If the deploy is a no-op (container already up, image unchanged), the `.env` may not be rewritten, leaving the literal `\n` on disk. In that case:
1. Manually write the `.env` with real newlines using `printf` on the server
2. Force-recreate the container via `docker compose up -d --force-recreate`

**Why:** Discovered during the OIDCProxy auth migration on 2026-04-05 when 4 of 6 stacks had garbled env vars because their containers weren't recreated.

**How to apply:** After `km update stack` changes the environment, always trigger a real deploy that recreates the container. If unsure, check the `.env` on disk with `xxd` — look for `0a` (real newline) vs `\n` literal.
