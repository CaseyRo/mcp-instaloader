"""Update checking mechanism for instaloader package."""

import datetime

import httpx
import instaloader

# Cache for update information
_update_cache: dict | None = None
_cache_timestamp: datetime.datetime | None = None
CACHE_DURATION = datetime.timedelta(days=1)


def get_installed_version() -> str:
    """
    Get the currently installed version of instaloader.

    Returns:
        Version string of installed instaloader
    """
    return instaloader.__version__


async def get_latest_version() -> str | None:
    """
    Fetch the latest available version of instaloader from PyPI.

    Returns:
        Latest version string, or None if fetch fails
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://pypi.org/pypi/instaloader/json", timeout=10.0
            )
            response.raise_for_status()
            data = response.json()
            return data.get("info", {}).get("version")
    except Exception:
        return None


def is_cache_valid() -> bool:
    """
    Check if the update cache is still valid (less than 1 day old).

    Returns:
        True if cache is valid, False otherwise
    """
    if _update_cache is None or _cache_timestamp is None:
        return False

    age = datetime.datetime.now() - _cache_timestamp
    return age < CACHE_DURATION


async def check_for_updates() -> dict:
    """
    Check for instaloader updates with caching (refreshes once per day).

    Returns:
        Dictionary with update information:
        - installed_version: str
        - latest_version: Optional[str]
        - update_available: bool
        - update_check_error: Optional[str]
    """
    global _update_cache, _cache_timestamp

    # Return cached result if still valid
    if is_cache_valid() and _update_cache is not None:
        return _update_cache.copy()

    # Fetch new update information
    installed = get_installed_version()
    latest = await get_latest_version()

    result = {
        "installed_version": installed,
        "latest_version": latest,
        "update_available": False,
        "update_check_error": None,
    }

    if latest is None:
        result["update_check_error"] = "Failed to fetch latest version from PyPI"
    elif latest != installed:
        # Compare versions (simple string comparison, PyPI uses semantic versioning)
        result["update_available"] = True

    # Update cache
    _update_cache = result
    _cache_timestamp = datetime.datetime.now()

    return result
