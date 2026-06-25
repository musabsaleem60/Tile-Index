import json
import urllib.error
import urllib.request

from .config import API_TIMEOUT_SECONDS


class ApiClientError(Exception):
    pass


class ApiClient:
    """Small standard-library API client for the Tkinter app."""

    def __init__(self, base_url: str, token: str | None = None, timeout: int = API_TIMEOUT_SECONDS):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    def set_token(self, token: str):
        self.token = token

    def get(self, path: str):
        return self._request("GET", path)

    def post(self, path: str, payload: dict):
        return self._request("POST", path, payload)

    def put(self, path: str, payload: dict):
        return self._request("PUT", path, payload)

    def delete(self, path: str):
        return self._request("DELETE", path)

    def _request(self, method: str, path: str, payload: dict | None = None):
        body = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=body,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = response.read().decode("utf-8")
                return json.loads(data) if data else None
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8")
            raise ApiClientError(f"API error {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            reason = getattr(exc, "reason", exc)
            raise ApiClientError(
                f"Cannot connect to API within {self.timeout} seconds. "
                "If this is the first open after some time, wait a minute and try again. "
                f"Details: {reason}"
            ) from exc
