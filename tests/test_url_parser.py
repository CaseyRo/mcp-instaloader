"""Tests for URL parser."""

from mcp_instaloader.url_parser import extract_shortcode, is_valid_instagram_url


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
