# Changelog
All notable changes to this project will be documented in this file.

## [0.1.0] - 2026-01-01
### Added
- Initial release: FastMCP server wrapping instaloader
- `fetch_instagram_post` tool: fetch Instagram post by URL or shortcode
- `fetch_instagram_reel` tool: fetch Instagram reel by URL or shortcode
- Optional session cookie support for private content
- Rate limiting middleware (configurable via environment variables)
- Automatic instaloader version checking (cached daily)
- Health check endpoint
