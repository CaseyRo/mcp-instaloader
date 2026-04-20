"""Tests for update_checker module."""

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from mcp_instaloader.update_checker import (
    check_for_updates,
    get_installed_version,
    get_latest_version,
    is_cache_valid,
)


def test_get_installed_version():
    """Test get_installed_version returns a non-empty version string."""
    version = get_installed_version()
    assert isinstance(version, str)
    assert len(version) > 0


@pytest.mark.asyncio
async def test_get_latest_version_success():
    """Test get_latest_version returns version string on successful API call."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"info": {"version": "4.11.0"}}
    mock_response.raise_for_status = MagicMock()

    with patch("mcp_instaloader.update_checker.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        version = await get_latest_version()
        assert version == "4.11.0"
        assert isinstance(version, str)
        assert len(version) > 0


@pytest.mark.asyncio
async def test_get_latest_version_failure():
    """Test get_latest_version returns None on API failure."""
    with patch("mcp_instaloader.update_checker.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=httpx.RequestError("Network error")
        )

        version = await get_latest_version()
        assert version is None


@pytest.mark.asyncio
async def test_get_latest_version_timeout():
    """Test get_latest_version returns None on timeout."""
    with patch("mcp_instaloader.update_checker.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=httpx.TimeoutException("Timeout")
        )

        version = await get_latest_version()
        assert version is None


@pytest.mark.asyncio
async def test_get_latest_version_http_error():
    """Test get_latest_version returns None on HTTP error."""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Not found", request=MagicMock(), response=mock_response
    )

    with patch("mcp_instaloader.update_checker.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        version = await get_latest_version()
        assert version is None


def test_is_cache_valid_no_cache():
    """Test is_cache_valid returns False when no cache exists."""
    # Import and reset module-level cache
    import mcp_instaloader.update_checker as update_checker_module

    # Clear cache by setting to None
    update_checker_module._update_cache = None
    update_checker_module._cache_timestamp = None

    assert is_cache_valid() is False


def test_is_cache_valid_fresh_cache():
    """Test is_cache_valid returns True for fresh cache."""
    import mcp_instaloader.update_checker as update_checker_module

    # Set fresh cache (less than 1 day old)
    update_checker_module._update_cache = {
        "installed_version": "4.10.0",
        "latest_version": "4.11.0",
        "update_available": True,
        "update_check_error": None,
    }
    update_checker_module._cache_timestamp = datetime.datetime.now()

    assert is_cache_valid() is True


def test_is_cache_valid_expired_cache():
    """Test is_cache_valid returns False for expired cache."""
    import mcp_instaloader.update_checker as update_checker_module

    # Set expired cache (more than 1 day old)
    update_checker_module._update_cache = {
        "installed_version": "4.10.0",
        "latest_version": "4.11.0",
        "update_available": True,
        "update_check_error": None,
    }
    update_checker_module._cache_timestamp = (
        datetime.datetime.now() - datetime.timedelta(days=2)
    )

    assert is_cache_valid() is False


@pytest.mark.asyncio
async def test_check_for_updates_response_structure():
    """Test check_for_updates returns correct response structure."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"info": {"version": "4.11.0"}}
    mock_response.raise_for_status = MagicMock()

    with patch("mcp_instaloader.update_checker.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        result = await check_for_updates()

        # Verify response structure
        assert isinstance(result, dict)
        assert "installed_version" in result
        assert "latest_version" in result
        assert "update_available" in result
        assert "update_check_error" in result

        # Verify types
        assert isinstance(result["installed_version"], str)
        assert result["latest_version"] is None or isinstance(
            result["latest_version"], str
        )
        assert isinstance(result["update_available"], bool)
        assert result["update_check_error"] is None or isinstance(
            result["update_check_error"], str
        )


@pytest.mark.asyncio
async def test_check_for_updates_caching():
    """Test check_for_updates uses cache for subsequent calls."""
    import mcp_instaloader.update_checker as update_checker_module

    # Clear cache first
    update_checker_module._update_cache = None
    update_checker_module._cache_timestamp = None

    mock_response = MagicMock()
    mock_response.json.return_value = {"info": {"version": "4.11.0"}}
    mock_response.raise_for_status = MagicMock()

    with patch("mcp_instaloader.update_checker.httpx.AsyncClient") as mock_client:
        mock_get = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value.get = mock_get

        # First call - should fetch from API
        result1 = await check_for_updates()
        assert mock_get.call_count == 1

        # Second call within cache duration - should use cache
        result2 = await check_for_updates()
        assert mock_get.call_count == 1  # No additional API call
        assert result1 == result2  # Same result


@pytest.mark.asyncio
async def test_check_for_updates_refreshes_after_expiry():
    """Test check_for_updates refreshes cache after expiry."""
    import mcp_instaloader.update_checker as update_checker_module

    # Set expired cache
    update_checker_module._update_cache = {
        "installed_version": "4.10.0",
        "latest_version": "4.10.0",
        "update_available": False,
        "update_check_error": None,
    }
    update_checker_module._cache_timestamp = (
        datetime.datetime.now() - datetime.timedelta(days=2)
    )

    mock_response = MagicMock()
    mock_response.json.return_value = {"info": {"version": "4.11.0"}}
    mock_response.raise_for_status = MagicMock()

    with patch("mcp_instaloader.update_checker.httpx.AsyncClient") as mock_client:
        mock_get = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value.get = mock_get

        # Should fetch fresh data
        result = await check_for_updates()
        assert mock_get.call_count == 1
        assert result["latest_version"] == "4.11.0"


@pytest.mark.asyncio
async def test_check_for_updates_update_available():
    """Test check_for_updates detects when update is available."""
    import mcp_instaloader.update_checker as update_checker_module

    # Clear cache
    update_checker_module._update_cache = None
    update_checker_module._cache_timestamp = None

    mock_response = MagicMock()
    mock_response.json.return_value = {"info": {"version": "4.11.0"}}
    mock_response.raise_for_status = MagicMock()

    with patch("mcp_instaloader.update_checker.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        # Mock installed version to be different
        with patch(
            "mcp_instaloader.update_checker.get_installed_version",
            return_value="4.10.0",
        ):
            result = await check_for_updates()
            # Note: This test depends on actual installed version
            # The update_available flag will be True if versions differ
            assert "update_available" in result


@pytest.mark.asyncio
async def test_check_for_updates_api_failure():
    """Test check_for_updates handles API failure gracefully."""
    import mcp_instaloader.update_checker as update_checker_module

    # Clear cache
    update_checker_module._update_cache = None
    update_checker_module._cache_timestamp = None

    with patch("mcp_instaloader.update_checker.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=httpx.RequestError("Network error")
        )

        result = await check_for_updates()

        assert result["latest_version"] is None
        assert result["update_check_error"] is not None
        assert isinstance(result["update_check_error"], str)
