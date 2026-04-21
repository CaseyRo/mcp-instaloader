"""Client wrapper for instaloader to fetch Instagram posts and reels."""

import asyncio
import json
import logging
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

logger = logging.getLogger(__name__)

# Cookies the Instagram web client needs for an authenticated session.
# Pulled in order of name-availability; `sessionid` + `csrftoken` are
# load-bearing, the rest help IG's fingerprinting keep the session warm.
_KNOWN_COOKIE_NAMES = ("csrftoken", "sessionid", "ds_user_id", "mid", "ig_did", "rur")


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

        Three auth paths, tried in order:
          1. ``INSTALOADER_SESSION_JSON`` env — JSON blob of cookie name/value
             pairs (``sessionid``, ``csrftoken``, etc.), injected directly
             into the requests session. Operator pastes these once from a
             logged-in browser's DevTools → Storage → Cookies panel.
             Recommended for Komodo/Docker deployments — never touches disk.
          2. ``cookie_file`` argument — path to an instaloader-native
             pickle session file (created by ``instaloader --login``).
             File-on-disk path, still supported for existing deployments.
          3. No auth. Instagram will 401 on most graphql calls.

        Args:
            cookie_file: Optional path to cookie file (path #2 above)
        """
        self.loader = instaloader.Instaloader()
        self.cookie_file = cookie_file
        self._session_loaded = False

        session_json = os.getenv("INSTALOADER_SESSION_JSON", "").strip()
        if session_json:
            try:
                self._inject_cookies_from_json(session_json)
            except Exception as e:
                logger.warning("instaloader_session_json_invalid: %s", e)

        if not self._session_loaded and cookie_file and os.path.exists(cookie_file):
            try:
                self._load_session(cookie_file)
            except Exception:
                pass

    def _inject_cookies_from_json(self, session_json: str) -> None:
        """Parse an ``INSTALOADER_SESSION_JSON`` blob and set cookies on
        the loader's internal requests.Session.

        Accepts either a flat ``{cookie_name: value}`` object or a
        ``{"cookies": {...}, "username": "..."}`` wrapper. The username
        is optional — instaloader only uses it as a local label.
        """
        parsed = json.loads(session_json)
        if isinstance(parsed, dict) and isinstance(parsed.get("cookies"), dict):
            cookies = parsed["cookies"]
            username = str(parsed.get("username") or "").strip() or None
        elif isinstance(parsed, dict):
            cookies = parsed
            username = None
        else:
            raise ValueError(
                "expected a JSON object (flat {name: value} or {cookies, username})"
            )

        if not cookies.get("sessionid") or not cookies.get("csrftoken"):
            raise ValueError("sessionid and csrftoken are required")

        jar = self.loader.context._session.cookies
        # instaloader's default Instaloader() pre-populates the jar with
        # empty placeholder cookies at no-domain — if we leave those in
        # place, `jar['sessionid']` raises CookieConflictError. Clear any
        # existing entry for a name we're about to set.
        for name in _KNOWN_COOKIE_NAMES:
            value = cookies.get(name)
            if value is None:
                continue
            # `jar.clear(domain, path, name)` raises if missing; wrap each
            # known-cookie clear so we can tolerate either the empty
            # placeholder or a previously-set value being absent.
            for dom in ("", ".instagram.com"):
                try:
                    jar.clear(dom, "/", name)
                except KeyError:
                    pass
            jar.set(str(name), str(value), domain=".instagram.com", path="/")

        # Mirror what instaloader's load_session_from_file does so the
        # session is indistinguishable from a file-loaded one.
        self.loader.context._session.headers.update(
            {"X-CSRFToken": cookies["csrftoken"]}
        )
        if username:
            self.loader.context.username = username
        self._session_loaded = True
        logger.info(
            "instaloader_session_loaded_from_env keys=%s username=%s",
            sorted(k for k in cookies if k in _KNOWN_COOKIE_NAMES),
            username or "(unset)",
        )

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
