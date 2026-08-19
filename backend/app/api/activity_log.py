from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.session import get_db
from app.models.entities import ActivityLog, User
from app.schemas.common import ActivityLogOut


router = APIRouter(prefix="/activity-log", tags=["activity-log"])
BUSINESS_TZ = ZoneInfo("Asia/Karachi")


@router.get("", response_model=list[ActivityLogOut])
def search_activity_log(
    user_id: int | None = None,
    branch_id: int | None = None,
    action_type: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = Query(1000, ge=1, le=5000),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    query = select(ActivityLog).order_by(ActivityLog.action_date.desc(), ActivityLog.id.desc())
    if user_id:
        query = query.where(ActivityLog.user_id == user_id)
    if branch_id:
        query = query.where(ActivityLog.branch_id == branch_id)
    if action_type:
        query = query.where(ActivityLog.action_type == action_type)

    rows = db.scalars(query).all()
    if date_from or date_to:
        rows = [
            row for row in rows
            if _matches_business_date(row.action_date, date_from, date_to)
        ]
    return rows[:limit]


@router.get("/{activity_id}", response_model=ActivityLogOut)
def get_activity_log(
    activity_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    entry = db.get(ActivityLog, activity_id)
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activity log entry not found")
    return entry


def _matches_business_date(value, date_from: date | None, date_to: date | None) -> bool:
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    business_day = value.astimezone(BUSINESS_TZ).date()
    if date_from and business_day < date_from:
        return False
    if date_to and business_day > date_to:
        return False
    return True
