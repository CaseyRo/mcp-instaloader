"""Tests for the rate limiting middleware."""

import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_instaloader.rate_limiter import RateLimitMiddleware


class TestRateLimitMiddleware:
    """Tests for RateLimitMiddleware."""

    def test_init_defaults(self):
        """Test default initialization values."""
        limiter = RateLimitMiddleware()
        assert limiter.requests_per_window == 10
        assert limiter.window_seconds == 60

    def test_init_custom_values(self):
        """Test custom initialization values."""
        limiter = RateLimitMiddleware(requests_per_window=5, window_seconds=30)
        assert limiter.requests_per_window == 5
        assert limiter.window_seconds == 30

    def test_is_rate_limited_within_limit(self):
        """Test that requests within limit are not blocked."""
        limiter = RateLimitMiddleware(requests_per_window=3, window_seconds=60)
        session_id = "test-session"

        # Record 2 requests (under limit of 3)
        limiter._record_request(session_id)
        limiter._record_request(session_id)

        assert not limiter._is_rate_limited(session_id)

    def test_is_rate_limited_at_limit(self):
        """Test that requests at limit are blocked."""
        limiter = RateLimitMiddleware(requests_per_window=3, window_seconds=60)
        session_id = "test-session"

        # Record 3 requests (at limit)
        limiter._record_request(session_id)
        limiter._record_request(session_id)
        limiter._record_request(session_id)

        assert limiter._is_rate_limited(session_id)

    def test_old_requests_cleaned(self):
        """Test that old requests are cleaned from the window."""
        limiter = RateLimitMiddleware(requests_per_window=2, window_seconds=1)
        session_id = "test-session"

        # Record requests
        limiter._record_request(session_id)
        limiter._record_request(session_id)

        # At limit now
        assert limiter._is_rate_limited(session_id)

        # Wait for window to expire
        time.sleep(1.1)

        # Should no longer be rate limited
        assert not limiter._is_rate_limited(session_id)

    def test_multiple_sessions_isolated(self):
        """Test that rate limiting is per-session."""
        limiter = RateLimitMiddleware(requests_per_window=2, window_seconds=60)

        # Fill up session1
        limiter._record_request("session1")
        limiter._record_request("session1")
        assert limiter._is_rate_limited("session1")

        # session2 should still be allowed
        assert not limiter._is_rate_limited("session2")

    def test_get_session_id_default(self):
        """Test session ID extraction with no session."""
        limiter = RateLimitMiddleware()
        context = MagicMock()
        context.session = None

        assert limiter._get_session_id(context) == "default"

    def test_get_session_id_from_context(self):
        """Test session ID extraction from context."""
        limiter = RateLimitMiddleware()
        context = MagicMock()
        context.session.id = "my-session-id"

        assert limiter._get_session_id(context) == "my-session-id"

    @pytest.mark.asyncio
    async def test_call_tool_allowed(self):
        """Test that tool calls within limit are allowed."""
        limiter = RateLimitMiddleware(requests_per_window=5, window_seconds=60)

        context = MagicMock()
        context.method = "tools/call"
        context.session.id = "test-session"

        call_next = AsyncMock(return_value="tool_result")

        result = await limiter(context, call_next)

        assert result == "tool_result"
        call_next.assert_called_once_with(context)

    @pytest.mark.asyncio
    async def test_call_tool_rate_limited(self):
        """Test that tool calls over limit return error."""
        limiter = RateLimitMiddleware(requests_per_window=1, window_seconds=60)

        context = MagicMock()
        context.method = "tools/call"
        context.session.id = "test-session"

        call_next = AsyncMock(return_value="tool_result")

        # First call should succeed
        result1 = await limiter(context, call_next)
        assert result1 == "tool_result"

        # Second call should be rate limited
        result2 = await limiter(context, call_next)
        assert result2.isError is True
        assert "Rate limit exceeded" in result2.content[0].text

    @pytest.mark.asyncio
    async def test_non_tool_calls_pass_through(self):
        """Test that non-tool-call methods are not rate limited."""
        limiter = RateLimitMiddleware(requests_per_window=1, window_seconds=60)

        context = MagicMock()
        context.method = "resources/read"
        context.session.id = "test-session"

        call_next = AsyncMock(return_value="resource_result")

        # Should always pass through regardless of rate limit
        result1 = await limiter(context, call_next)
        result2 = await limiter(context, call_next)
        assert result1 == "resource_result"
        assert result2 == "resource_result"
