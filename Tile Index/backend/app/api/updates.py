from fastapi import APIRouter
from app.core.config import get_settings
from app.schemas.common import UpdateInfo


router = APIRouter(prefix="/updates", tags=["updates"])


@router.get("/latest", response_model=UpdateInfo)
def latest_update():
    settings = get_settings()
    return UpdateInfo(
        latest_version=settings.latest_desktop_version,
        download_url=settings.latest_desktop_download_url,
        release_notes=settings.latest_desktop_release_notes,
    )
