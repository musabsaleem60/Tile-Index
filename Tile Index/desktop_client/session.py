"""
Runtime session state for the desktop client.
Keeps the API client and authenticated user token in memory only.
"""

from desktop_client.api_client import ApiClient
from desktop_client.config import API_BASE_URL


api_client = ApiClient(API_BASE_URL)
current_token = None
cache = {}


def set_authenticated_session(token: str):
    """Store the active API token for this desktop runtime."""
    global current_token
    current_token = token
    api_client.set_token(token)
    cache.clear()


def clear_authenticated_session():
    """Clear the active API token."""
    global current_token
    current_token = None
    api_client.set_token(None)
    cache.clear()


def get_cached(key: str):
    return cache.get(key)


def set_cached(key: str, value):
    cache[key] = value
    return value


def invalidate_cache(prefix: str | None = None):
    if prefix is None:
        cache.clear()
        return
    for key in list(cache.keys()):
        if key.startswith(prefix):
            del cache[key]
