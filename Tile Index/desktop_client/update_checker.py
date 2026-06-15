from desktop_client.api_client import ApiClient
from desktop_client.config import APP_VERSION


def check_for_update(api_client: ApiClient) -> dict | None:
    info = api_client.get("/updates/latest")
    latest = info.get("latest_version")
    if latest and latest != APP_VERSION:
        return info
    return None
