"""Local, per-user storage for in-progress invoice drafts."""

import json
import os
import tempfile
from pathlib import Path


DRAFT_SCHEMA_VERSION = 1


class InvoiceDraftStore:
    """Persist one invoice draft per user without touching the backend."""

    def __init__(self, user_id, root=None):
        self.user_id = int(user_id)
        if self.user_id <= 0:
            raise ValueError("A valid user ID is required for invoice drafts")

        if root is None:
            local_app_data = os.environ.get("LOCALAPPDATA")
            if local_app_data:
                root = Path(local_app_data) / "TileIndex" / "drafts"
            else:
                root = Path.home() / "AppData" / "Local" / "TileIndex" / "drafts"
        self.root = Path(root)
        self.path = self.root / f"invoice_draft_user_{self.user_id}.json"

    def exists(self):
        return self.path.is_file()

    def load(self):
        with self.path.open("r", encoding="utf-8") as draft_file:
            data = json.load(draft_file)
        if not isinstance(data, dict):
            raise ValueError("Invoice draft is not a valid object")
        if data.get("schema_version") != DRAFT_SCHEMA_VERSION:
            raise ValueError("Invoice draft was saved by an unsupported app version")
        if data.get("user_id") != self.user_id:
            raise ValueError("Invoice draft belongs to a different user")
        if not isinstance(data.get("items", []), list):
            raise ValueError("Invoice draft items are invalid")
        return data

    def save(self, data):
        payload = dict(data)
        payload["schema_version"] = DRAFT_SCHEMA_VERSION
        payload["user_id"] = self.user_id
        self.root.mkdir(parents=True, exist_ok=True)

        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.root,
                prefix=f".{self.path.stem}_",
                suffix=".tmp",
                delete=False,
            ) as temp_file:
                temp_path = Path(temp_file.name)
                json.dump(payload, temp_file, ensure_ascii=True, indent=2)
                temp_file.flush()
                os.fsync(temp_file.fileno())
            os.replace(temp_path, self.path)
        finally:
            if temp_path and temp_path.exists():
                temp_path.unlink()
        return self.path

    def delete(self):
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass
