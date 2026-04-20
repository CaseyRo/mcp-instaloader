"""Pytest configuration and fixtures.

Sets MCP_TRANSPORT=stdio before server import so the fail-fast in
src/mcp_instaloader/server.py does not trigger SystemExit during
test collection (it refuses to run in HTTP mode without MCP_API_KEY).
"""

from __future__ import annotations

import os

os.environ.setdefault("MCP_TRANSPORT", "stdio")
os.environ.setdefault("MCP_API_KEY", "test-key-not-real")
