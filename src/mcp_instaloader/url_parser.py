"""URL parsing utilities for extracting Instagram shortcodes from URLs."""

import re


def extract_shortcode(url_or_shortcode: str) -> str | None:
    """
    Extract shortcode from an Instagram URL or return the shortcode if already provided.

    Supports:
    - https://www.instagram.com/p/{shortcode}/
    - https://instagram.com/p/{shortcode}/ (without www)
    - https://www.instagram.com/reel/{shortcode}/ (for reels)
    - Direct shortcode input

    Args:
        url_or_shortcode: Instagram URL or shortcode string

    Returns:
        Extracted shortcode, or None if URL format is invalid
    """
    # If it's already a shortcode (no http/https and no slashes except at start/end)
    if not url_or_shortcode.startswith("http"):
        # Clean up any trailing/leading whitespace or slashes
        shortcode = url_or_shortcode.strip().strip("/")
        # Validate it looks like a shortcode (alphanumeric, hyphens, underscores)
        if re.match(r"^[a-zA-Z0-9_-]+$", shortcode):
            return shortcode

    # Patterns for Instagram URLs
    patterns = [
        r"instagram\.com/p/([a-zA-Z0-9_-]+)",
        r"instagram\.com/reel/([a-zA-Z0-9_-]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, url_or_shortcode)
        if match:
            return match.group(1)

    return None


def is_valid_instagram_url(url: str) -> bool:
    """
    Check if a string is a valid Instagram URL format.

    Args:
        url: String to validate

    Returns:
        True if valid Instagram URL format, False otherwise
    """
    return extract_shortcode(url) is not None
