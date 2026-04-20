"""Tests for URL parser."""

from mcp_instaloader.url_parser import (
    extract_shortcode,
    is_numeric_media_id,
    is_valid_instagram_url,
)


def test_extract_shortcode_from_full_url():
    """Test extracting shortcode from full Instagram URL."""
    url = "https://www.instagram.com/p/DRr-n4XER3x/"
    assert extract_shortcode(url) == "DRr-n4XER3x"


def test_extract_shortcode_from_url_without_www():
    """Test extracting shortcode from URL without www."""
    url = "https://instagram.com/p/DRr-n4XER3x/"
    assert extract_shortcode(url) == "DRr-n4XER3x"


def test_extract_shortcode_from_reel_url():
    """Test extracting shortcode from reel URL."""
    url = "https://www.instagram.com/reel/ABC123/"
    assert extract_shortcode(url) == "ABC123"


def test_extract_shortcode_direct_input():
    """Test extracting shortcode when shortcode is provided directly."""
    shortcode = "DRr-n4XER3x"
    assert extract_shortcode(shortcode) == "DRr-n4XER3x"


def test_extract_shortcode_invalid_url():
    """Test extracting shortcode from invalid URL."""
    invalid_url = "https://example.com/post/123"
    assert extract_shortcode(invalid_url) is None


def test_is_valid_instagram_url():
    """Test URL validation."""
    assert is_valid_instagram_url("https://www.instagram.com/p/DRr-n4XER3x/") is True
    assert is_valid_instagram_url("DRr-n4XER3x") is True
    assert is_valid_instagram_url("https://example.com/post") is False


def test_numeric_media_id_recognized():
    """Zernio's ig_reel attachments carry numeric media_ids; the parser
    must accept them alongside shortcodes so the MCP can branch to
    Post.from_mediaid downstream."""
    assert is_numeric_media_id("17966020298908086") is True
    assert is_valid_instagram_url("17966020298908086") is True
    # media_ids are NOT shortcodes — extract_shortcode rejects them so
    # callers fall through to the media_id branch cleanly.
    assert extract_shortcode("17966020298908086") is None


def test_numeric_media_id_edge_cases():
    assert is_numeric_media_id("") is False
    assert is_numeric_media_id("   ") is False
    # Too short to be a real IG id (kept as a belt-and-braces filter)
    assert is_numeric_media_id("123") is False
    # Mixed alphanumerics are shortcodes, not media_ids
    assert is_numeric_media_id("ABC123") is False
