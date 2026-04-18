---
name: instaloader-mcp Komodo registration status
description: git-mcp-instaloader-nebula IS registered in Komodo DB and runs on nebula-1; stack dir at /etc/komodo/stacks/git-mcp-instaloader-nebula/
type: reference
---

`git-mcp-instaloader-nebula` stack:
- Stack dir: `/etc/komodo/stacks/git-mcp-instaloader-nebula/` on nebula-1 (100.89.96.56)
- Container name: `mcp-instaloader`
- IS registered in Komodo DB — visible as `git-mcp-instaloader-nebula` in `km list`
- Image: `git-mcp-instaloader-nebula-mcp-instaloader` (locally built by Komodo)

To redeploy via Komodo: `echo "" | km execute deploy-stack git-mcp-instaloader-nebula`
If container is not recreated (old uptime), force-recreate via:
`ssh caseyromkes@100.89.96.56 "sudo bash -c 'cd /etc/komodo/stacks/git-mcp-instaloader-nebula && docker compose up -d --force-recreate'"`

Note: The .env file in the stack dir requires sudo to read — always use `sudo bash -c` for docker compose operations on nebula-1 stack dirs.

Previous note (stale): This was previously recorded as running on ubuntu-smurf-mirror and not in Komodo DB — that was incorrect or outdated.
