import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urlparse


UPDATE_STATE_FILE = "update_state.json"


class UpdateError(Exception):
    pass


def runtime_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def updates_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    root = Path(base) if base else Path.home()
    path = root / "TileIndex" / "Updates"
    path.mkdir(parents=True, exist_ok=True)
    return path


def state_path() -> Path:
    return updates_dir() / UPDATE_STATE_FILE


def write_update_state(state: dict):
    state_path().write_text(json.dumps(state, indent=2), encoding="utf-8")


def read_update_state() -> dict | None:
    path = state_path()
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def clear_update_state():
    path = state_path()
    if path.exists():
        path.unlink()


def backup_config() -> Path | None:
    config_path = runtime_dir() / "tile_index_config.json"
    if not config_path.exists():
        return None
    backup_path = updates_dir() / "tile_index_config.json.bak"
    shutil.copy2(config_path, backup_path)
    return backup_path


def download_update(update_info: dict, progress=None) -> Path:
    url = update_info.get("download_url")
    expected_sha = (update_info.get("sha256") or "").strip().lower()
    expected_size = update_info.get("file_size_bytes")
    if not url:
        raise UpdateError("Update download URL is missing.")
    if not expected_sha:
        raise UpdateError("Update checksum is missing.")

    parsed = urlparse(url)
    filename = Path(parsed.path).name or f"TileIndexSetup-{update_info.get('latest_version', 'latest')}.exe"
    final_path = updates_dir() / filename
    temp_path = final_path.with_suffix(final_path.suffix + ".download")

    sha = hashlib.sha256()
    bytes_read = 0
    try:
        with urllib.request.urlopen(url, timeout=90) as response, temp_path.open("wb") as out:
            total = response.headers.get("Content-Length")
            total = int(total) if total and total.isdigit() else expected_size
            while True:
                chunk = response.read(1024 * 256)
                if not chunk:
                    break
                out.write(chunk)
                sha.update(chunk)
                bytes_read += len(chunk)
                if progress:
                    progress(bytes_read, total)
    except Exception as exc:
        if temp_path.exists():
            temp_path.unlink()
        raise UpdateError(f"Could not download update: {exc}") from exc

    if expected_size is not None and int(expected_size) != bytes_read:
        temp_path.unlink(missing_ok=True)
        raise UpdateError(f"Downloaded file size mismatch. Expected {expected_size}, got {bytes_read}.")

    actual_sha = sha.hexdigest()
    if actual_sha != expected_sha:
        temp_path.unlink(missing_ok=True)
        raise UpdateError("Downloaded update checksum does not match.")

    temp_path.replace(final_path)
    return final_path


def verify_signature(
    installer_path: Path,
    expected_publisher: str | None = None,
    expected_thumbprint: str | None = None,
):
    command = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        (
            "& { param([string]$Path) "
            "$sig = Get-AuthenticodeSignature -LiteralPath $Path; "
            "$subject = if ($sig.SignerCertificate) { $sig.SignerCertificate.Subject } else { '' }; "
            "$thumbprint = if ($sig.SignerCertificate) { $sig.SignerCertificate.Thumbprint } else { '' }; "
            "Write-Output ($sig.Status.ToString() + '|' + $subject + '|' + $thumbprint) }"
        ),
        str(installer_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise UpdateError("Could not verify update signature.")
    output = (result.stdout or "").strip().splitlines()[-1]
    status, _, rest = output.partition("|")
    subject, _, thumbprint = rest.partition("|")
    if expected_thumbprint:
        actual = thumbprint.replace(" ", "").upper()
        expected = expected_thumbprint.replace(" ", "").upper()
        if not actual or actual != expected:
            raise UpdateError("Update signature certificate does not match the expected certificate.")
    elif status != "Valid":
        raise UpdateError(f"Update signature is not trusted: {status}.")
    if expected_publisher and expected_publisher not in subject:
        raise UpdateError("Update signature publisher does not match the expected publisher.")


def is_certificate_trusted(expected_thumbprint: str | None) -> bool:
    if not expected_thumbprint:
        return False
    expected = expected_thumbprint.replace(" ", "").upper()
    stores = [("Root", "-user"), ("TrustedPublisher", "-user"), ("Root", ""), ("TrustedPublisher", "")]
    matches = 0
    for store, scope in stores:
        command = ["certutil"]
        if scope:
            command.append(scope)
        command.extend(["-store", store, expected])
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        except Exception:
            continue
        if result.returncode == 0 and expected in (result.stdout or "").replace(" ", "").upper():
            matches += 1
    return matches >= 2


def launch_installer(installer_path: Path, update_info: dict):
    backup = backup_config()
    write_update_state({
        "status": "installer_started",
        "version": update_info.get("latest_version"),
        "installer": str(installer_path),
        "config_backup": str(backup) if backup else None,
    })
    subprocess.Popen([str(installer_path), "/SP-", "/NORESTART"], close_fds=True)
