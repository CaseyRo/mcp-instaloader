"""Rate limiting middleware for FastMCP."""

import time
from collections import defaultdict

from fastmcp.server.middleware import Middleware, MiddlewareContext
from mcp import types as mt


class RateLimitMiddleware(Middleware):
    """
    Simple in-memory rate limiting middleware.

    Limits the number of tool calls per session within a sliding time window.
    """

    def __init__(
        self,
        requests_per_window: int = 10,
        window_seconds: int = 60,
    ):
        """
        Initialize the rate limiter.

        Args:
            requests_per_window: Maximum number of requests allowed per time window
            window_seconds: Time window size in seconds
        """
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        # Track requests: session_id -> list of timestamps
        self._requests: dict[str, list[float]] = defaultdict(list)

    def _get_session_id(self, context: MiddlewareContext) -> str:
        """Extract session ID from context, falling back to a default."""
        # Try to get session ID from context
        if hasattr(context, "session") and context.session:
            session_id = getattr(context.session, "id", None)
            if session_id:
                return str(session_id)
        return "default"

    def _clean_old_requests(self, session_id: str) -> None:
        """Remove requests outside the current time window."""
        now = time.time()
        cutoff = now - self.window_seconds
        self._requests[session_id] = [
            ts for ts in self._requests[session_id] if ts > cutoff
        ]

    def _is_rate_limited(self, session_id: str) -> bool:
        """Check if the session has exceeded the rate limit."""
        self._clean_old_requests(session_id)
        return len(self._requests[session_id]) >= self.requests_per_window

    def _record_request(self, session_id: str) -> None:
        """Record a new request for the session."""
        self._requests[session_id].append(time.time())

    async def __call__(self, context: MiddlewareContext, call_next):
        """Rate limit tool calls."""
        # Only rate-limit tool calls, pass through everything else
        if context.method != "tools/call":
            return await call_next(context)

        session_id = self._get_session_id(context)

        if self._is_rate_limited(session_id):
            # Return a rate limit error as tool result
            return mt.CallToolResult(
                content=[
                    mt.TextContent(
                        type="text",
                        text=f"Rate limit exceeded. Maximum {self.requests_per_window} "
                        f"requests per {self.window_seconds} seconds allowed.",
                    )
                ],
                isError=True,
            )

        # Record this request and proceed
        self._record_request(session_id)
        return await call_next(context)
