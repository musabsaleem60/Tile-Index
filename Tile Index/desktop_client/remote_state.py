"""Helpers for deciding when the desktop app should use the backend API."""

from desktop_client import session


def is_api_authenticated():
    """Return True when login has established an API token."""
    return bool(session.current_token)
