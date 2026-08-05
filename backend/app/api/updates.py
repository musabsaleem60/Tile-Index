from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, require_admin
from app.core.config import get_settings
from app.db.session import get_db
from app.models.entities import DesktopClientStatus, User
from app.schemas.common import DesktopStatusIn, DesktopStatusOut, UpdateInfo


router = APIRouter(prefix="/updates", tags=["updates"])


@router.get("/latest", response_model=UpdateInfo)
def latest_update():
    settings = get_settings()
    return UpdateInfo(
        latest_version=settings.latest_desktop_version,
        min_desktop_version=settings.min_desktop_version,
        download_url=settings.latest_desktop_download_url,
        release_notes=settings.latest_desktop_release_notes,
        sha256=settings.latest_desktop_sha256,
        file_size_bytes=settings.latest_desktop_file_size_bytes,
        signature_publisher=settings.latest_desktop_signature_publisher,
        signature_thumbprint=settings.latest_desktop_signature_thumbprint,
        mandatory=settings.latest_desktop_mandatory,
    )


@router.post("/desktop-status", response_model=DesktopStatusOut)
def report_desktop_status(
    payload: DesktopStatusIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    status = db.scalar(
        select(DesktopClientStatus).where(DesktopClientStatus.machine_id == payload.machine_id)
    )
    if not status:
        status = DesktopClientStatus(machine_id=payload.machine_id)
        db.add(status)

    status.hostname = payload.hostname
    status.username = current_user.username
    status.user_id = current_user.id
    status.branch_id = current_user.branch_id
    status.app_version = payload.app_version
    status.latest_version = payload.latest_version
    status.min_desktop_version = payload.min_desktop_version
    status.certificate_trusted = payload.certificate_trusted
    status.update_available = payload.update_available
    status.updates_disabled = payload.updates_disabled
    status.details = payload.details
    db.commit()
    db.refresh(status)
    return status


@router.get("/desktop-status", response_model=list[DesktopStatusOut], dependencies=[Depends(require_admin)])
def list_desktop_statuses(db: Session = Depends(get_db)):
    return db.scalars(
        select(DesktopClientStatus).order_by(
            DesktopClientStatus.updates_disabled.desc(),
            DesktopClientStatus.update_available.desc(),
            DesktopClientStatus.last_seen_at.desc(),
        )
    ).all()