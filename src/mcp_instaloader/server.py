"""FastMCP server for Instagram content fetching."""

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
from .config import settings
from .instaloader_client import InstaloaderClient
from .rate_limiter import RateLimitMiddleware
from .url_parser import is_valid_instagram_url

# load_dotenv runs after Settings() has read env; kept for dev-mode .env support
# in case settings picks up late-loaded values on module reimport.
load_dotenv()

rate_limiter = RateLimitMiddleware(
    requests_per_window=settings.rate_limit_requests,
    window_seconds=settings.rate_limit_window,
)

_api_key = settings.mcp_api_key.get_secret_value()
_auth = BearerTokenVerifier(api_key=_api_key) if _api_key else None

mcp = FastMCP("mcp-instaloader", middleware=[rate_limiter], auth=_auth)

instaloader_client = InstaloaderClient(cookie_file=settings.cookie_file)


@mcp.tool()
async def fetch_instagram_content(
    url: str = Field(
        ...,
        description=(
            "Instagram post or reel URL (e.g., https://www.instagram.com/p/DRr-n4XER3x/ "
            "or https://www.instagram.com/reel/ABC123/), a shortcode (e.g., DRr-n4XER3x), "
            "or a numeric media_id (e.g., 17966020298908086 — the shape IG/Zernio "
            "webhook attachments carry)."
        ),
    ),
) -> dict:
    """[media] Fetch an Instagram post or reel and return caption + media URLs.

    Disambiguation: This tool fetches text/caption content plus the creator-curated
    cover image (display_url) and, for videos, the mp4 URL. For cross-platform post
    metadata, use zernio's research_download_post.

    Automatically handles both posts (/p/) and reels (/reel/) — they use the same
    underlying Instagram API. Accepts full URLs, bare shortcodes, or numeric media_ids.

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
        - display_url: Creator-curated cover image URL (for reels: the chosen
          poster frame, not a freeze frame). Always present for public posts.
        - video_url: mp4 URL for GraphVideo/reels; null otherwise.
    """
    try:
        # Validate URL / shortcode / media_id format
        if not is_valid_instagram_url(url):
            return {
                "error": "Invalid Instagram URL format",
                "error_code": "INVALID_URL_FORMAT",
                "message": (
                    f"The provided URL '{url}' is not a valid Instagram URL, "
                    "shortcode, or numeric media_id."
                ),
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
    if settings.transport == "stdio":
        mcp.run(transport="stdio")
        return
    # stateless_http=True matches the http_app() construction above —
    # no orphaned SSE sessions.
    mcp.run(
        transport="streamable-http",
        host=settings.host,
        port=settings.mcp_port,
        stateless_http=True,
    )


if __name__ == "__main__":
    main()
