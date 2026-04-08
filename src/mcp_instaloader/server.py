"""FastMCP server for Instagram content fetching."""

import os

from dotenv import load_dotenv
from fastmcp import FastMCP
from instaloader.exceptions import (
    ConnectionException,
    InstaloaderException,
    LoginRequiredException,
)
from pydantic import Field
from starlette.responses import JSONResponse

from .auth import BearerTokenVerifier
from .instaloader_client import InstaloaderClient
from .rate_limiter import RateLimitMiddleware
from .url_parser import is_valid_instagram_url

# Load environment variables
load_dotenv()

# Get rate limit configuration from environment
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "10"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))

# Initialize rate limiting middleware
rate_limiter = RateLimitMiddleware(
    requests_per_window=RATE_LIMIT_REQUESTS,
    window_seconds=RATE_LIMIT_WINDOW,
)

# Build authentication (bearer token via MCP_API_KEY)
_api_key = os.getenv("MCP_API_KEY", "")
_auth = BearerTokenVerifier(api_key=_api_key) if _api_key else None

# Initialize FastMCP server with middleware and optional auth
mcp = FastMCP("mcp-instaloader", middleware=[rate_limiter], auth=_auth)

# Get configuration from environment
MCP_PORT = int(os.getenv("MCP_PORT", "3336"))
COOKIE_FILE = os.getenv("COOKIE_FILE")

# Initialize instaloader client
instaloader_client = InstaloaderClient(cookie_file=COOKIE_FILE)


@mcp.tool()
async def fetch_instagram_content(
    url: str = Field(
        ...,
        description=(
            "Instagram post or reel URL (e.g., https://www.instagram.com/p/DRr-n4XER3x/ "
            "or https://www.instagram.com/reel/ABC123/) or shortcode (e.g., DRr-n4XER3x)."
        ),
    ),
) -> dict:
    """
    Fetch an Instagram post or reel by URL or shortcode and return its text content.

    Automatically handles both posts (/p/) and reels (/reel/) — they use the same
    underlying Instagram API. You can pass any Instagram content URL or just a shortcode.

    Returns:
        Dictionary containing:
        - text: Caption/text content
        - shortcode: Content shortcode
        - author: Author username
        - timestamp: Post timestamp (ISO format)
        - likes: Number of likes
        - comments: Number of comments
        - is_video: Whether content is a video
        - typename: Instagram content type (GraphImage, GraphVideo, GraphSidecar)
    """
    try:
        # Validate URL format
        if not is_valid_instagram_url(url):
            return {
                "error": "Invalid Instagram URL format",
                "error_code": "INVALID_URL_FORMAT",
                "message": f"The provided URL '{url}' is not a valid Instagram URL format. Expected: https://www.instagram.com/p/SHORTCODE/ or https://www.instagram.com/reel/SHORTCODE/ or just the shortcode.",
                "url": url,
            }

        # Fetch content data (posts and reels use the same API)
        content_data = await instaloader_client.fetch_post(url)

        return content_data
    except LoginRequiredException as e:
        return {
            "error": "Authentication required",
            "error_code": "AUTHENTICATION_REQUIRED",
            "message": f"{str(e)} Please provide a valid session cookie file via COOKIE_FILE environment variable. You can create one by running 'instaloader --login your_username'.",
            "url": url,
        }
    except ConnectionException as e:
        return {
            "error": "Network error",
            "error_code": "NETWORK_ERROR",
            "message": f"Failed to connect to Instagram: {str(e)}. Please check your internet connection and try again.",
            "url": url,
            "retry_hint": "This may be a temporary network issue. Please retry after a few moments.",
        }
    except ValueError as e:
        return {
            "error": "Content not found",
            "error_code": "CONTENT_NOT_FOUND",
            "message": f"{str(e)} The post/reel may have been deleted, made private, or the URL/shortcode is incorrect.",
            "url": url,
        }
    except InstaloaderException as e:
        return {
            "error": "Error fetching content",
            "error_code": "INSTALOADER_ERROR",
            "message": f"An error occurred while fetching the content: {str(e)}",
            "url": url,
        }
    except Exception as e:
        return {
            "error": "Unexpected error",
            "error_code": "UNEXPECTED_ERROR",
            "message": f"An unexpected error occurred: {str(e)}",
            "url": url,
        }


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    """Health check endpoint for Docker/load balancer probes."""
    return JSONResponse({"status": "healthy", "service": "mcp-instaloader"})


# ASGI app for production deployment with uvicorn
# stateless_http=True: each JSON-RPC POST is self-contained (no session negotiation).
# Required for simple HTTP callers (Sammler mcpCall pattern) that do not implement
# the full MCP SSE session handshake. Same pattern as mcp-ytdlp.
app = mcp.http_app(stateless_http=True)


def main():
    # Run the server with HTTP transport
    mcp.run(transport="streamable-http", host="0.0.0.0", port=MCP_PORT)


if __name__ == "__main__":
    main()
