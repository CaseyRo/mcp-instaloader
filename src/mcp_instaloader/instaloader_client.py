"""Client wrapper for instaloader to fetch Instagram posts and reels."""

import asyncio
import os
from typing import Any

import instaloader
from instaloader import Post
from instaloader.exceptions import (
    ConnectionException,
    InstaloaderException,
    LoginRequiredException,
    ProfileNotExistsException,
)

from .url_parser import extract_shortcode, is_numeric_media_id


def _post_to_dict(post: Post) -> dict[str, Any]:
    """Serialize a Post (or Reel — both use the same class) into the
    MCP's public return shape.

    ``display_url`` is the creator-curated cover image. For GraphImage it's
    the image itself; for GraphVideo (reels) it's the creator-chosen
    poster frame that instaloader extracts from the GraphQL response —
    never a random still. ``video_url`` is the mp4 URL for videos only.
    """
    caption = post.caption if post.caption else ""
    # `post.url` is the canonical media URL: image for GraphImage, poster
    # frame for GraphVideo. `getattr` with fallback because instaloader
    # occasionally shifts these attributes across minor versions.
    display_url = getattr(post, "url", None)
    video_url = getattr(post, "video_url", None) if post.is_video else None
    return {
        "shortcode": post.shortcode,
        "text": caption,
        "author": post.owner_username,
        "timestamp": post.date_utc.isoformat() if post.date_utc else None,
        "likes": post.likes,
        "comments": post.comments,
        "is_video": post.is_video,
        "typename": post.typename,
        "display_url": display_url,
        "video_url": video_url,
    }


class InstaloaderClient:
    """Wrapper around instaloader for fetching Instagram content."""

    def __init__(self, cookie_file: str | None = None):
        """
        Initialize the Instaloader client.

        Args:
            cookie_file: Optional path to cookie file for authenticated sessions
        """
        self.loader = instaloader.Instaloader()
        self.cookie_file = cookie_file
        self._session_loaded = False

        # Load session from cookie file if provided
        if cookie_file and os.path.exists(cookie_file):
            try:
                # Try to load session from file
                # instaloader expects session files in a specific format
                # For now, we'll handle this in a basic way
                # In practice, users would need to export cookies in instaloader format
                self._load_session(cookie_file)
            except Exception:
                # If loading fails, continue without authentication
                pass

    def _load_session(self, cookie_file: str) -> None:
        """
        Load session from cookie file using instaloader's native API.

        Note: Instaloader expects session files in its own format, typically
        created by running `instaloader --login username`. The cookie_file
        path can be:
        - A directory containing session files (e.g., `/root/.config/instaloader/`)
        - A specific session file path (e.g., `/root/.config/instaloader/session-username`)
        - A username string (instaloader will use default session path)

        This method uses instaloader's `load_session_from_file()` API to properly
        load the session.
        """
        try:
            if not os.path.exists(cookie_file):
                # Path doesn't exist, mark session as not loaded
                self._session_loaded = False
                return

            # Check if cookie_file is a directory or file
            if os.path.isdir(cookie_file):
                # It's a directory - try to find session files
                # Instaloader stores sessions as "session-{username}" files
                session_files = [
                    f
                    for f in os.listdir(cookie_file)
                    if f.startswith("session-")
                    and os.path.isfile(os.path.join(cookie_file, f))
                ]
                if session_files:
                    # Extract username from first session file found
                    # Format: session-{username}
                    username = session_files[0].replace("session-", "", 1)
                    session_path = os.path.join(cookie_file, session_files[0])
                    self.loader.load_session_from_file(username, session_path)
                    self._session_loaded = True
                else:
                    # No session files found in directory
                    self._session_loaded = False
            elif os.path.isfile(cookie_file):
                # It's a file - try to extract username from filename
                # Format: session-{username} or just the file path
                filename = os.path.basename(cookie_file)
                if filename.startswith("session-"):
                    username = filename.replace("session-", "", 1)
                    self.loader.load_session_from_file(username, cookie_file)
                    self._session_loaded = True
                else:
                    # File doesn't match expected format, try as username
                    # This handles cases where cookie_file is just a username
                    self.loader.load_session_from_file(cookie_file)
                    self._session_loaded = True
            else:
                # Treat as username string (instaloader will use default path)
                self.loader.load_session_from_file(cookie_file)
                self._session_loaded = True
        except FileNotFoundError:
            # Session file doesn't exist
            self._session_loaded = False
        except Exception:
            # Any other error during session loading
            # Continue without authentication
            self._session_loaded = False

    async def fetch_post(self, url_or_shortcode: str) -> dict[str, Any]:
        """
        Fetch an Instagram post by URL, shortcode, or numeric media_id.

        The numeric media_id path exists because IG's webhook-style payloads
        (e.g. Zernio's ``ig_reel`` attachments) expose a numeric
        ``reel_video_id`` / asset_id rather than a shortcode.

        Args:
            url_or_shortcode: Instagram post URL, shortcode, or numeric media_id

        Returns:
            Dictionary with post data including caption, author, and the
            creator-curated ``display_url`` / ``video_url``.

        Raises:
            ValueError: If the input matches no known IG identifier shape
            InstaloaderException: If the post cannot be fetched
            LoginRequiredException: If authentication is required for private content
        """
        media_id: int | None = None
        shortcode = extract_shortcode(url_or_shortcode)
        if not shortcode:
            if is_numeric_media_id(url_or_shortcode):
                media_id = int(url_or_shortcode.strip().strip("/"))
            else:
                raise ValueError(
                    f"Invalid Instagram URL, shortcode, or media_id: {url_or_shortcode}"
                )

        identifier = shortcode if shortcode else str(media_id)

        def _fetch_post_sync():
            try:
                if media_id is not None:
                    post = Post.from_mediaid(self.loader.context, media_id)
                else:
                    post = Post.from_shortcode(self.loader.context, shortcode)
                return _post_to_dict(post)
            except LoginRequiredException:
                raise LoginRequiredException(
                    "This post is private and requires authentication. "
                    "Please provide a valid session cookie file via COOKIE_FILE environment variable."
                ) from None
            except ProfileNotExistsException:
                raise ValueError(f"Post not found: {identifier}") from None
            except ConnectionException as e:
                raise ConnectionException(
                    f"Network error while fetching post: {e!s}"
                ) from e
            except InstaloaderException as e:
                raise InstaloaderException(f"Error fetching post: {e!s}") from e

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _fetch_post_sync)

    async def fetch_reel(self, url_or_shortcode: str) -> dict[str, Any]:
        """
        Fetch an Instagram reel by URL or shortcode.

        Note: Instagram reels are essentially posts with typename "GraphVideo".
        This method uses the same underlying logic as fetch_post.

        Args:
            url_or_shortcode: Instagram reel URL or shortcode

        Returns:
            Dictionary with reel data including text and metadata

        Raises:
            ValueError: If URL is invalid
            InstaloaderException: If reel cannot be fetched
            LoginRequiredException: If authentication is required for private content
        """
        # Reels are posts with video content, so we can use the same logic
        return await self.fetch_post(url_or_shortcode)
