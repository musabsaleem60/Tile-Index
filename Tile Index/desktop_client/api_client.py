import json
import socket
import urllib.error
import urllib.request
from contextlib import contextmanager

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

    def get(self, path: str, timeout: int | None = None):
        return self._request("GET", path, timeout=timeout)

    def post(self, path: str, payload: dict, timeout: int | None = None):
        return self._request("POST", path, payload, timeout=timeout)

    def put(self, path: str, payload: dict):
        return self._request("PUT", path, payload)

    def patch(self, path: str, payload: dict):
        return self._request("PATCH", path, payload)

    def delete(self, path: str):
        return self._request("DELETE", path)

    @contextmanager
    def timeout_override(self, timeout: int):
        previous = self.timeout
        self.timeout = timeout
        try:
            yield
        finally:
            self.timeout = previous

    def _request(self, method: str, path: str, payload: dict | None = None, timeout: int | None = None):
        request_timeout = timeout or self.timeout
        body = None
        headers = {"Accept": "application/json"}
        debug_payment_request = method == "POST" and path.endswith("/payments")
        debug_remarks_request = method == "PATCH" and path.endswith("/remarks")
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
        if debug_payment_request:
            print(f"[payment-debug] request {method} {self.base_url}{path} payload={payload}")
        if debug_remarks_request:
            print(f"[remarks-debug] request {method} {self.base_url}{path} payload={payload}")
        try:
            with urllib.request.urlopen(request, timeout=request_timeout) as response:
                data = response.read().decode("utf-8")
                if debug_payment_request:
                    print(f"[payment-debug] response {response.status} body={data}")
                if debug_remarks_request:
                    print(f"[remarks-debug] response {response.status} body={data}")
                return json.loads(data) if data else None
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8")
            if debug_payment_request:
                print(f"[payment-debug] response {exc.code} body={detail}")
            if debug_remarks_request:
                print(f"[remarks-debug] response {exc.code} body={detail}")
            try:
                parsed = json.loads(detail)
                parsed_detail = parsed.get("detail")
                if parsed_detail:
                    raise ApiClientError(str(parsed_detail)) from exc
            except ApiClientError:
                raise
            except Exception:
                pass
            raise ApiClientError(f"API error {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            reason = getattr(exc, "reason", exc)
            raise ApiClientError(
                f"Cannot connect to API within {self.timeout} seconds. "
                "If this is the first open after some time, wait a minute and try again. "
                f"Details: {reason}"
            ) from exc
        except (TimeoutError, socket.timeout) as exc:
            raise ApiClientError(
                f"The API did not respond within {request_timeout} seconds. "
                "If this is the first open after some time, wait a minute and try again."
            ) from exc
