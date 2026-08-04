import json
from sqlalchemy.orm import Session
from app.models.entities import ActivityLog, Branch, User


def write_audit_log(
    db: Session,
    user: User,
    action_type: str,
    action_details: dict | str | None = None,
    branch_id: int | None = None,
    ip_address: str | None = None,
) -> ActivityLog:
    branch_name = None
    if branch_id:
        branch = db.get(Branch, branch_id)
        branch_name = branch.name if branch else None

    if isinstance(action_details, dict):
        details = json.dumps(action_details, ensure_ascii=True)
    else:
        details = action_details or ""

    entry = ActivityLog(
        user_id=user.id,
        username=user.username,
        user_role=user.role,
        branch_id=branch_id,
        branch_name=branch_name,
        action_type=action_type,
        action_details=details,
        ip_address=ip_address,
    )
    db.add(entry)
    return entry
