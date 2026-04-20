# Changelog

## [0.2.5] - 2026-04-20

- chore(pkg): add __main__.py and py.typed per MCP Server Standards


## [0.2.4] - 2026-04-20

- chore(pkg): add __main__.py and py.typed per MCP Server Standards


## [0.2.3] - 2026-04-18

- feat(reliability): fail-fast auth + stateless_http on mcp.run + FastMCP 3.2.4


## [0.2.2] - 2026-04-09

- fix: lowercase Docker image tags in release CI


## [0.2.0] - 2026-04-09

### Changed
- Bumped FastMCP dependency to >=3.2.2
- Added disambiguation note to fetch_instagram_content docstring

### Added
- Automated version bump and release CI via GitHub Actions

## [0.1.0] - 2026-01-01
### Added
- Initial release: FastMCP server wrapping instaloader
- `fetch_instagram_post` tool: fetch Instagram post by URL or shortcode
- `fetch_instagram_reel` tool: fetch Instagram reel by URL or shortcode
- Optional session cookie support for private content
- Rate limiting middleware (configurable via environment variables)
- Automatic instaloader version checking (cached daily)
- Health check endpoint
