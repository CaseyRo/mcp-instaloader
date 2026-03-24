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

from .instaloader_client import InstaloaderClient
from .rate_limiter import RateLimitMiddleware
from .update_checker import check_for_updates
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

# Initialize FastMCP server with middleware
mcp = FastMCP("mcp-instaloader", middleware=[rate_limiter])

# Get configuration from environment
MCP_PORT = int(os.getenv("MCP_PORT", "3336"))
COOKIE_FILE = os.getenv("COOKIE_FILE")

# Initialize instaloader client
instaloader_client = InstaloaderClient(cookie_file=COOKIE_FILE)


@mcp.tool()
async def fetch_instagram_post(
    url: str = Field(
        ...,
        description=(
            "Instagram post URL (e.g., https://www.instagram.com/p/DRr-n4XER3x/) "
            "or shortcode (e.g., DRr-n4XER3x)."
        ),
    ),
) -> dict:
    """
    Fetch an Instagram post by URL or shortcode and return its text content as JSON.

    Args:
        url: Instagram post URL (e.g., "https://www.instagram.com/p/DRr-n4XER3x/")
             or shortcode (e.g., "DRr-n4XER3x")

    Returns:
        Dictionary containing:
        - text: Post caption/text content
        - shortcode: Post shortcode
        - author: Author username
        - timestamp: Post timestamp (ISO format)
        - likes: Number of likes
        - comments: Number of comments
        - is_video: Whether post is a video
        - update_info: Instaloader version update information
    """
    try:
        # Validate URL format
        if not is_valid_instagram_url(url):
            return {
                "error": "Invalid Instagram URL format",
                "error_code": "INVALID_URL_FORMAT",
                "message": f"The provided URL '{url}' is not a valid Instagram URL format. Expected format: https://www.instagram.com/p/{'{shortcode}'}/ or shortcode only.",
                "url": url,
            }

        # Fetch post data
        post_data = await instaloader_client.fetch_post(url)

        # Get update information
        update_info = await check_for_updates()

        # Combine post data with update info
        return {
            **post_data,
            "update_info": update_info,
        }
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
            "error": "Post not found",
            "error_code": "POST_NOT_FOUND",
            "message": f"{str(e)} The post may have been deleted, made private, or the URL/shortcode is incorrect.",
            "url": url,
        }
    except InstaloaderException as e:
        return {
            "error": "Error fetching post",
            "error_code": "INSTALOADER_ERROR",
            "message": f"An error occurred while fetching the post: {str(e)}",
            "url": url,
        }
    except Exception as e:
        return {
            "error": "Unexpected error",
            "error_code": "UNEXPECTED_ERROR",
            "message": f"An unexpected error occurred: {str(e)}",
            "url": url,
        }


@mcp.tool()
async def fetch_instagram_reel(
    url: str = Field(
        ...,
        description=(
            "Instagram reel URL (e.g., https://www.instagram.com/reel/ABC123/) "
            "or shortcode (e.g., ABC123)."
        ),
    ),
) -> dict:
    """
    Fetch an Instagram reel by URL or shortcode and return its text content as JSON.

    Args:
        url: Instagram reel URL (e.g., "https://www.instagram.com/reel/ABC123/")
             or shortcode (e.g., "ABC123")

    Returns:
        Dictionary containing:
        - text: Reel caption/text content
        - shortcode: Reel shortcode
        - author: Author username
        - timestamp: Reel timestamp (ISO format)
        - likes: Number of likes
        - comments: Number of comments
        - is_video: Always True for reels
        - update_info: Instaloader version update information
    """
    try:
        # Validate URL format
        if not is_valid_instagram_url(url):
            return {
                "error": "Invalid Instagram URL format",
                "error_code": "INVALID_URL_FORMAT",
                "message": f"The provided URL '{url}' is not a valid Instagram URL format. Expected format: https://www.instagram.com/reel/{'{shortcode}'}/ or shortcode only.",
                "url": url,
            }

        # Fetch reel data (reels are posts with video content)
        reel_data = await instaloader_client.fetch_reel(url)

        # Get update information
        update_info = await check_for_updates()

        # Combine reel data with update info
        return {
            **reel_data,
            "update_info": update_info,
        }
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
            "error": "Reel not found",
            "error_code": "REEL_NOT_FOUND",
            "message": f"{str(e)} The reel may have been deleted, made private, or the URL/shortcode is incorrect.",
            "url": url,
        }
    except InstaloaderException as e:
        return {
            "error": "Error fetching reel",
            "error_code": "INSTALOADER_ERROR",
            "message": f"An error occurred while fetching the reel: {str(e)}",
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
app = mcp.http_app()


if __name__ == "__main__":
    # Run the server with HTTP transport
    mcp.run(transport="http", host="0.0.0.0", port=MCP_PORT)
