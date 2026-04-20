"""Settings behaviour — defaults, validation, and fail-fast for HTTP mode."""

from __future__ import annotations

import pytest


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    """Strip known settings env vars so tests see a predictable baseline."""
    for var in (
        "RATE_LIMIT_REQUESTS",
        "RATE_LIMIT_WINDOW",
        "COOKIE_FILE",
        "TRANSPORT",
        "HOST",
        "MCP_PORT",
        "MCP_API_KEY",
    ):
        monkeypatch.delenv(var, raising=False)
    return monkeypatch


def test_defaults_with_api_key(clean_env):
    clean_env.setenv("MCP_API_KEY", "test-key")

    from mcp_instaloader.config import Settings

    s = Settings()
    assert s.rate_limit_requests == 10
    assert s.rate_limit_window == 60
    assert s.transport == "http"
    assert s.host == "127.0.0.1"
    assert s.mcp_port == 3336
    assert s.cookie_file is None
    assert s.mcp_api_key.get_secret_value() == "test-key"


def test_http_mode_requires_api_key(clean_env):
    clean_env.setenv("TRANSPORT", "http")

    from mcp_instaloader.config import Settings

    with pytest.raises(ValueError, match="MCP_API_KEY is required"):
        Settings()


def test_stdio_mode_allows_empty_api_key(clean_env):
    clean_env.setenv("TRANSPORT", "stdio")

    from mcp_instaloader.config import Settings

    s = Settings()
    assert s.mcp_api_key.get_secret_value() == ""


def test_rate_limit_must_be_positive(clean_env):
    clean_env.setenv("MCP_API_KEY", "test-key")
    clean_env.setenv("RATE_LIMIT_REQUESTS", "0")

    from mcp_instaloader.config import Settings

    with pytest.raises(ValueError, match=">= 1"):
        Settings()


def test_secret_not_in_repr(clean_env):
    clean_env.setenv("MCP_API_KEY", "super-secret")

    from mcp_instaloader.config import Settings

    s = Settings()
    assert "super-secret" not in repr(s)
    assert "super-secret" not in str(s)
