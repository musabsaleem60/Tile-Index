from desktop_client.api_client import ApiClient
from desktop_client.config import APP_VERSION
from desktop_client.updater import is_certificate_trusted


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
    latest = info.get("latest_version")
    is_below_minimum = bool(minimum and is_version_older(APP_VERSION, minimum))
    is_below_latest = bool(latest and is_version_older(APP_VERSION, latest))
    if is_below_minimum or is_below_latest:
        info["local_version"] = APP_VERSION
        info["is_below_minimum"] = is_below_minimum
        info["update_available"] = is_below_latest
        signature_thumbprint = info.get("signature_thumbprint")
        if is_below_latest and signature_thumbprint and not is_certificate_trusted(signature_thumbprint):
            info["updates_disabled"] = True
            info["warning_message"] = (
                "This version is out of date. Stock and prices may display incorrectly. "
                "Updates are disabled because the Tile Index update certificate is not trusted "
                "on this machine. Please contact your administrator."
            )
            return info
        label = "Required update available." if info.get("mandatory") else "Update available."
        info["warning_message"] = f"{OUT_OF_DATE_MESSAGE} {label}"
        return info
    return None
