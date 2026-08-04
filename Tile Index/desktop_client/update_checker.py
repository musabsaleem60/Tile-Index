from desktop_client.api_client import ApiClient
from desktop_client.config import APP_VERSION


OUT_OF_DATE_MESSAGE = (
    "This version is out of date. Stock and prices may display incorrectly. "
    "Please contact your administrator to update."
)


def _version_parts(version: str) -> tuple[int, ...]:
    parts = []
    for part in str(version or "").split("."):
        digits = ""
        for char in part:
            if not char.isdigit():
                break
            digits += char
        parts.append(int(digits or 0))
    return tuple(parts or [0])


def is_version_older(local_version: str, minimum_version: str) -> bool:
    local = list(_version_parts(local_version))
    minimum = list(_version_parts(minimum_version))
    width = max(len(local), len(minimum))
    local.extend([0] * (width - len(local)))
    minimum.extend([0] * (width - len(minimum)))
    return tuple(local) < tuple(minimum)


def check_for_update(api_client: ApiClient) -> dict | None:
    info = api_client.get("/updates/latest")
    minimum = info.get("min_desktop_version")
    if minimum and is_version_older(APP_VERSION, minimum):
        info["local_version"] = APP_VERSION
        info["warning_message"] = OUT_OF_DATE_MESSAGE
        return info
    return None
