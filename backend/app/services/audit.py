import json
from sqlalchemy.orm import Session
from app.models.entities import ActivityLog, Branch, User


EVENT_CATEGORIES = ("Stock", "Sales", "Returns", "Pricing", "Catalogue", "Users", "Access")


def infer_event_category(action_type: str) -> str:
    value = (action_type or "").lower()
    if "login" in value or "logout" in value or value == "access" or value.startswith("access "):
        return "Access"
    if "return" in value or "refund" in value or "settlement" in value:
        return "Returns"
    if "stock" in value or "inventory" in value:
        return "Stock"
    if "rate" in value or "price" in value or "tile size" in value:
        return "Pricing"
    if "user" in value or "password" in value:
        return "Users"
    if "invoice" in value or "payment" in value or "sale" in value or "void" in value or "remarks" in value:
        return "Sales"
    return "Catalogue"


def write_audit_log(
    db: Session,
    user: User,
    action_type: str,
    action_details: dict | str | None = None,
    branch_id: int | None = None,
    ip_address: str | None = None,
    *,
    event_category: str | None = None,
    product_id: int | None = None,
    accessory_id: int | None = None,
    sanitary_product_id: int | None = None,
    invoice_id: int | None = None,
    return_id: int | None = None,
) -> ActivityLog:
    branch_name = None
    if branch_id:
        branch = db.get(Branch, branch_id)
        branch_name = branch.name if branch else None

    detail_data = action_details if isinstance(action_details, dict) else {}
    product_id = product_id or detail_data.get("product_id")
    accessory_id = accessory_id or detail_data.get("accessory_id")
    sanitary_product_id = sanitary_product_id or detail_data.get("sanitary_product_id")
    invoice_id = invoice_id or detail_data.get("invoice_id")
    return_id = return_id or detail_data.get("return_id")

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
        event_category=event_category or infer_event_category(action_type),
        product_id=product_id,
        accessory_id=accessory_id,
        sanitary_product_id=sanitary_product_id,
        invoice_id=invoice_id,
        return_id=return_id,
    )
    db.add(entry)
    return entry
