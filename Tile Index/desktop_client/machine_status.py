import json
import platform
import uuid

from desktop_client.config import APP_VERSION
from desktop_client.update_checker import is_version_older
from desktop_client.updater import is_certificate_trusted, runtime_dir


MACHINE_ID_FILE = "tile_index_machine_id.txt"


def get_machine_id() -> str:
    path = runtime_dir() / MACHINE_ID_FILE
    if path.exists():
        value = path.read_text(encoding="utf-8-sig").strip()
        if value:
            return value
    value = str(uuid.uuid4())
    path.write_text(value, encoding="utf-8")
    return value


def report_desktop_status(api_client, update_info: dict | None):
    info = update_info or {}
    if not info:
        info = api_client.get("/updates/latest") or {}
    thumbprint = info.get("signature_thumbprint")
    latest = info.get("latest_version")
    minimum = info.get("min_desktop_version")
    update_available = bool(latest and is_version_older(APP_VERSION, latest))
    below_minimum = bool(minimum and is_version_older(APP_VERSION, minimum))
    certificate_trusted = is_certificate_trusted(thumbprint) if thumbprint else False
    payload = {
        "machine_id": get_machine_id(),
        "hostname": platform.node(),
        "app_version": APP_VERSION,
        "latest_version": latest,
        "min_desktop_version": minimum,
        "certificate_trusted": certificate_trusted,
        "update_available": bool(info.get("update_available", update_available)),
        "updates_disabled": bool(info.get("updates_disabled", update_available and thumbprint and not certificate_trusted)),
        "details": {
            "mandatory": bool(info.get("mandatory")),
            "is_below_minimum": bool(info.get("is_below_minimum", below_minimum)),
            "has_download_url": bool(info.get("download_url")),
            "has_sha256": bool(info.get("sha256")),
        },
    }
    # Ensure the payload remains simple JSON for the backend.
    json.dumps(payload)
    return api_client.post("/updates/desktop-status", payload)
