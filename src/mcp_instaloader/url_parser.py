"""URL parsing utilities for extracting Instagram shortcodes from URLs."""

import re


def is_numeric_media_id(value: str) -> bool:
    """True when the input looks like an Instagram numeric media_id
    (e.g. ``17966020298908086`` from a Zernio ig_reel webhook attachment).

    Distinct from shortcodes, which mix letters, digits, ``-`` and ``_``.
    Callers use this to branch to ``Post.from_mediaid`` instead of
    ``Post.from_shortcode``.
    """
    s = (value or "").strip().strip("/")
    return bool(s) and s.isdigit() and len(s) >= 10


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
        # Reject pure-numeric strings — those are media_ids, not shortcodes.
        # Genuine shortcodes always contain at least one letter.
        if is_numeric_media_id(shortcode):
            return None
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
    Check if a string is a valid Instagram URL or media_id format.

    Args:
        url: String to validate

    Returns:
        True if it's either a parseable shortcode URL OR a numeric media_id.
    """
    return extract_shortcode(url) is not None or is_numeric_media_id(url)
