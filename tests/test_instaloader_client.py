"""Unit tests for InstaloaderClient with mocked instaloader."""

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from instaloader.exceptions import (
    ConnectionException,
    InstaloaderException,
    LoginRequiredException,
    ProfileNotExistsException,
)

from mcp_instaloader.instaloader_client import InstaloaderClient


class TestInstaloaderClientInit:
    """Test client initialization and session loading."""

    def test_init_without_cookie(self):
        """Client initializes without cookie file."""
        client = InstaloaderClient()
        assert client.cookie_file is None
        assert client._session_loaded is False

    def test_init_with_nonexistent_cookie(self):
        """Client gracefully handles nonexistent cookie file."""
        client = InstaloaderClient(cookie_file="/nonexistent/path/session")
        assert client._session_loaded is False

    @patch.object(InstaloaderClient, "_load_session")
    def test_init_calls_load_session_when_file_exists(self, mock_load):
        """Client attempts to load session when cookie file exists."""
        with tempfile.NamedTemporaryFile(prefix="session-", delete=False) as f:
            tmp_path = f.name
        try:
            InstaloaderClient(cookie_file=tmp_path)
            mock_load.assert_called_once_with(tmp_path)
        finally:
            os.unlink(tmp_path)

    @patch.object(InstaloaderClient, "_load_session", side_effect=Exception("fail"))
    def test_init_survives_load_session_failure(self, mock_load):
        """Client continues even if session loading throws."""
        with tempfile.NamedTemporaryFile(prefix="session-", delete=False) as f:
            tmp_path = f.name
        try:
            client = InstaloaderClient(cookie_file=tmp_path)
            # Should not raise; client should still be usable
            assert client is not None
        finally:
            os.unlink(tmp_path)


class TestLoadSession:
    """Test _load_session with various path types."""

    def test_load_session_nonexistent_path(self):
        """Nonexistent path sets _session_loaded to False."""
        client = InstaloaderClient()
        client._load_session("/does/not/exist")
        assert client._session_loaded is False

    @patch("instaloader.Instaloader")
    def test_load_session_directory_with_session_file(self, mock_loader_cls):
        """Directory containing session-username file loads correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_file = os.path.join(tmpdir, "session-testuser")
            with open(session_file, "w") as f:
                f.write("fake session")

            mock_loader = MagicMock()
            mock_loader_cls.return_value = mock_loader

            client = InstaloaderClient()
            client.loader = mock_loader
            client._load_session(tmpdir)

            mock_loader.load_session_from_file.assert_called_once_with(
                "testuser", session_file
            )
            assert client._session_loaded is True

    @patch("instaloader.Instaloader")
    def test_load_session_directory_without_session_files(self, mock_loader_cls):
        """Empty directory sets _session_loaded to False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            client = InstaloaderClient()
            client._load_session(tmpdir)
            assert client._session_loaded is False

    @patch("instaloader.Instaloader")
    def test_load_session_file_with_session_prefix(self, mock_loader_cls):
        """File named session-username extracts username and loads."""
        with tempfile.NamedTemporaryFile(
            prefix="session-myuser", delete=False, dir=tempfile.gettempdir()
        ) as f:
            tmp_path = f.name

        try:
            mock_loader = MagicMock()
            mock_loader_cls.return_value = mock_loader

            client = InstaloaderClient()
            client.loader = mock_loader

            # Rename to have the exact prefix format
            session_path = os.path.join(tempfile.gettempdir(), "session-myuser")
            os.rename(tmp_path, session_path)

            client._load_session(session_path)
            mock_loader.load_session_from_file.assert_called_once_with(
                "myuser", session_path
            )
            assert client._session_loaded is True
        finally:
            if os.path.exists(session_path):
                os.unlink(session_path)


class TestFetchPost:
    """Test fetch_post with mocked instaloader Post."""

    @pytest.mark.asyncio
    @patch("mcp_instaloader.instaloader_client.Post")
    async def test_fetch_post_success(self, mock_post_cls):
        """Successful fetch returns expected dict structure."""
        mock_post = MagicMock()
        mock_post.shortcode = "ABC123"
        mock_post.caption = "Test caption"
        mock_post.owner_username = "testuser"
        mock_post.date_utc.isoformat.return_value = "2025-01-01T00:00:00"
        mock_post.likes = 42
        mock_post.comments = 5
        mock_post.is_video = False
        mock_post.typename = "GraphImage"
        mock_post_cls.from_shortcode.return_value = mock_post

        client = InstaloaderClient()
        result = await client.fetch_post("https://www.instagram.com/p/ABC123/")

        assert result["shortcode"] == "ABC123"
        assert result["text"] == "Test caption"
        assert result["author"] == "testuser"
        assert result["likes"] == 42
        assert result["is_video"] is False

    @pytest.mark.asyncio
    @patch("mcp_instaloader.instaloader_client.Post")
    async def test_fetch_post_empty_caption(self, mock_post_cls):
        """Post with no caption returns empty string for text."""
        mock_post = MagicMock()
        mock_post.shortcode = "NOCAP1"
        mock_post.caption = None
        mock_post.owner_username = "someone"
        mock_post.date_utc.isoformat.return_value = "2025-01-01T00:00:00"
        mock_post.likes = 0
        mock_post.comments = 0
        mock_post.is_video = False
        mock_post.typename = "GraphImage"
        mock_post_cls.from_shortcode.return_value = mock_post

        client = InstaloaderClient()
        result = await client.fetch_post("NOCAP1")

        assert result["text"] == ""

    @pytest.mark.asyncio
    async def test_fetch_post_invalid_url_raises_value_error(self):
        """Invalid URL raises ValueError."""
        client = InstaloaderClient()
        with pytest.raises(ValueError, match="Invalid Instagram URL"):
            await client.fetch_post("https://example.com/not-instagram")

    @pytest.mark.asyncio
    @patch("mcp_instaloader.instaloader_client.Post")
    async def test_fetch_post_login_required(self, mock_post_cls):
        """LoginRequiredException propagates with helpful message."""
        mock_post_cls.from_shortcode.side_effect = LoginRequiredException(
            "Login required"
        )

        client = InstaloaderClient()
        with pytest.raises(LoginRequiredException, match="private"):
            await client.fetch_post("https://www.instagram.com/p/PRIV1/")

    @pytest.mark.asyncio
    @patch("mcp_instaloader.instaloader_client.Post")
    async def test_fetch_post_profile_not_exists(self, mock_post_cls):
        """ProfileNotExistsException becomes ValueError."""
        mock_post_cls.from_shortcode.side_effect = ProfileNotExistsException(
            "Not found"
        )

        client = InstaloaderClient()
        with pytest.raises(ValueError, match="Post not found"):
            await client.fetch_post("https://www.instagram.com/p/GONE1/")

    @pytest.mark.asyncio
    @patch("mcp_instaloader.instaloader_client.Post")
    async def test_fetch_post_connection_error(self, mock_post_cls):
        """ConnectionException propagates."""
        mock_post_cls.from_shortcode.side_effect = ConnectionException("Timeout")

        client = InstaloaderClient()
        with pytest.raises(ConnectionException, match="Network error"):
            await client.fetch_post("https://www.instagram.com/p/ABC123/")

    @pytest.mark.asyncio
    @patch("mcp_instaloader.instaloader_client.Post")
    async def test_fetch_post_generic_instaloader_error(self, mock_post_cls):
        """InstaloaderException propagates."""
        mock_post_cls.from_shortcode.side_effect = InstaloaderException("Unknown error")

        client = InstaloaderClient()
        with pytest.raises(InstaloaderException, match="Error fetching post"):
            await client.fetch_post("https://www.instagram.com/p/ABC123/")


class TestFetchReel:
    """Test fetch_reel delegates to fetch_post."""

    @pytest.mark.asyncio
    @patch("mcp_instaloader.instaloader_client.Post")
    async def test_fetch_reel_delegates_to_fetch_post(self, mock_post_cls):
        """fetch_reel uses the same logic as fetch_post."""
        mock_post = MagicMock()
        mock_post.shortcode = "REEL1"
        mock_post.caption = "Reel caption"
        mock_post.owner_username = "reeler"
        mock_post.date_utc.isoformat.return_value = "2025-06-01T00:00:00"
        mock_post.likes = 100
        mock_post.comments = 10
        mock_post.is_video = True
        mock_post.typename = "GraphVideo"
        mock_post_cls.from_shortcode.return_value = mock_post

        client = InstaloaderClient()
        result = await client.fetch_reel("https://www.instagram.com/reel/REEL1/")

        assert result["shortcode"] == "REEL1"
        assert result["is_video"] is True

    @pytest.mark.asyncio
    async def test_fetch_reel_invalid_url(self):
        """Invalid URL raises ValueError via fetch_post."""
        client = InstaloaderClient()
        with pytest.raises(ValueError):
            await client.fetch_reel("https://example.com/not-instagram")
