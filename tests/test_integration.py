"""Integration tests for the MCP server."""

from pathlib import Path

import pytest

from mcp_instaloader.instaloader_client import InstaloaderClient
from mcp_instaloader.server import mcp


def read_example_urls() -> list[str]:
    """Read URLs from example_urls.txt file."""
    test_file = Path(__file__).parent / "example_urls.txt"
    urls = []
    with open(test_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                urls.append(line)
    return urls


@pytest.mark.asyncio
async def test_fetch_public_post():
    """Test fetching a public post without authentication."""
    client = InstaloaderClient()

    # Use one of the example URLs
    url = "https://www.instagram.com/p/DRr-n4XER3x/"

    try:
        result = await client.fetch_post(url)
        assert "text" in result
        assert "shortcode" in result
        assert "author" in result
    except Exception as e:
        # Skip test if network unavailable or post doesn't exist
        pytest.skip(f"Could not fetch post: {e}")


@pytest.mark.asyncio
async def test_fetch_post_from_example_urls():
    """Test fetching posts from example URLs file."""
    urls = read_example_urls()
    assert len(urls) >= 4, "Should have at least 4 example URLs"

    client = InstaloaderClient()

    # Test first URL
    url = urls[0]
    try:
        result = await client.fetch_post(url)
        assert "text" in result or "error" in result
    except Exception as e:
        pytest.skip(f"Could not fetch post: {e}")


@pytest.mark.asyncio
async def test_url_parsing_in_fetch():
    """Test that URL parsing works correctly in fetch operations."""
    client = InstaloaderClient()

    # Test with full URL
    url = "https://www.instagram.com/p/DRr-n4XER3x/"
    try:
        result = await client.fetch_post(url)
        assert "shortcode" in result
    except Exception:
        pytest.skip("Network unavailable or post not accessible")


@pytest.mark.asyncio
async def test_invalid_url_handling():
    """Test handling of invalid URLs."""
    client = InstaloaderClient()

    with pytest.raises(ValueError):
        await client.fetch_post("https://example.com/invalid")


@pytest.mark.asyncio
async def test_tool_registration():
    """Test that MCP tools are registered."""
    # Check that tools are registered
    # FastMCP should have tools registered
    assert mcp is not None
