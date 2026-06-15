import json
import os
import sys
from pathlib import Path


APP_VERSION = "1.0.0"


def _runtime_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def _load_config_file():
    config_path = _runtime_dir() / "tile_index_config.json"
    if not config_path.exists():
        return {}
    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


_config = _load_config_file()
API_BASE_URL = os.environ.get("TILE_INDEX_API_URL") or _config.get("api_base_url") or "http://localhost:8000"
CHECK_UPDATES = bool(_config.get("check_updates", True))
