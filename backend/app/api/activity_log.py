from datetime import date, datetime, timezone
import re
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import String, cast, or_, select
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.session import get_db
from app.models.entities import (
    ActivityLog, Branch, Invoice, InvoiceItem, InvoiceReturn, InvoiceReturnItem,
    Product, ProductClientCode, ReturnExchangeItem, StockTransaction, User,
)
from app.core.currency import format_currency
from app.schemas.common import ActivityLogOut
from app.services.audit import EVENT_CATEGORIES, infer_event_category


router = APIRouter(prefix="/activity-log", tags=["activity-log"])
BUSINESS_TZ = ZoneInfo("Asia/Karachi")


@router.get("", response_model=list[ActivityLogOut])
def search_activity_log(
    user_id: int | None = None,
    branch_id: int | None = None,
    action_type: str | None = None,
    view: str = Query("business", pattern="^(business|access|all)$"),
    event_category: str | None = None,
    product_id: int | None = None,
    invoice_number: str | None = None,
    return_number: str | None = None,
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
    if view == "business":
        query = query.where(
            or_(ActivityLog.event_category.is_(None), ActivityLog.event_category != "Access"),
            ActivityLog.action_type.notin_(("Login", "Logout")),
        )
    elif view == "access":
        query = query.where(or_(ActivityLog.event_category == "Access", ActivityLog.action_type.in_(("Login", "Logout"))))
    if event_category:
        matching_actions = [action for action in db.scalars(select(ActivityLog.action_type).distinct()) if infer_event_category(action) == event_category]
        query = query.where(or_(ActivityLog.event_category == event_category, ActivityLog.action_type.in_(matching_actions)))
    if product_id:
        details_text = cast(ActivityLog.action_details, String)
        query = query.where(or_(
            ActivityLog.product_id == product_id,
            details_text.like(f'%"product_id": {product_id}%'),
            details_text.like(f'%"product_id":{product_id}%'),
        ))
    if invoice_number:
        query = query.where(cast(ActivityLog.action_details, String).ilike(f"%{invoice_number.strip()}%"))
    if return_number:
        query = query.where(cast(ActivityLog.action_details, String).ilike(f"%{return_number.strip()}%"))

    rows = db.scalars(query).all()
    if date_from or date_to:
        rows = [
            row for row in rows
            if _matches_business_date(row.action_date, date_from, date_to)
        ]
    return rows[:limit]


@router.get("/actions")
def activity_actions(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    grouped = {category: [] for category in EVENT_CATEGORIES}
    for action in db.scalars(select(ActivityLog.action_type).distinct().order_by(ActivityLog.action_type)):
        grouped[infer_event_category(action)].append(action)
    return grouped


@router.get("/products")
def activity_products(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    codes = {}
    for product_id, code in db.execute(select(ProductClientCode.product_id, ProductClientCode.client_code)):
        codes.setdefault(product_id, []).append(code)
    return [
        {"id": product.id, "name": product.name, "tile_size": product.tile_size,
         "item_code": product.item_code, "client_codes": codes.get(product.id, [])}
        for product in db.scalars(select(Product).order_by(Product.name, Product.tile_size))
    ]


@router.get("/product-history/{product_id}")
def product_history(
    product_id: int,
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    timeline = []
    stock_rows = db.execute(
        select(StockTransaction, User.username, Branch.name)
        .join(User, User.id == StockTransaction.user_id)
        .join(Branch, Branch.id == StockTransaction.branch_id)
        .where(StockTransaction.product_id == product_id)
    ).all()
    for tx, username, branch_name in stock_rows:
        timeline.append({
            "date": tx.transaction_date, "user": username, "branch": branch_name,
            "category": "Stock", "action": f"Stock {tx.transaction_type}",
            "reference": _stock_reference(tx), "summary": _stock_summary(product, tx),
            "details": tx.notes or "", "raw": {
                "transaction_id": tx.id, "grade": tx.grade, "boxes": tx.boxes,
                "loose_pieces": tx.loose_pieces, "dc_number": tx.dc_number, "notes": tx.notes,
            },
        })
    sale_rows = db.execute(
        select(InvoiceItem, Invoice, User.username, Branch.name)
        .join(Invoice, Invoice.id == InvoiceItem.invoice_id)
        .outerjoin(User, User.id == Invoice.user_id)
        .join(Branch, Branch.id == InvoiceItem.source_branch_id)
        .where(InvoiceItem.product_id == product_id)
    ).all()
    for item, invoice, username, branch_name in sale_rows:
        timeline.append({
            "date": invoice.invoice_date, "user": username or "Unknown", "branch": branch_name,
            "category": "Sales", "action": "Invoice Sale" if invoice.status != "void" else "Voided Invoice Sale",
            "reference": invoice.invoice_number,
            "summary": f"{item.boxes} boxes + {item.loose_pieces} loose | {item.grade} | {format_currency(item.line_total)}",
            "details": f"Customer: {invoice.customer_name}; status: {invoice.status}",
            "raw": {"invoice_id": invoice.id, "invoice_item_id": item.id, "status": invoice.status,
                    "boxes_from_boxes": item.boxes_from_boxes, "pieces_from_loose": item.pieces_from_loose},
        })
    return_rows = db.execute(
        select(InvoiceReturnItem, InvoiceReturn, Invoice, User.username, Branch.name)
        .join(InvoiceReturn, InvoiceReturn.id == InvoiceReturnItem.return_id)
        .join(InvoiceItem, InvoiceItem.id == InvoiceReturnItem.invoice_item_id)
        .join(Invoice, Invoice.id == InvoiceReturn.invoice_id)
        .join(User, User.id == InvoiceReturn.user_id)
        .join(Branch, Branch.id == InvoiceReturnItem.source_branch_id)
        .where(InvoiceItem.product_id == product_id)
    ).all()
    for item, record, invoice, username, branch_name in return_rows:
        timeline.append({
            "date": record.return_date, "user": username, "branch": branch_name,
            "category": "Returns", "action": "Item Returned", "reference": record.return_number,
            "summary": f"{item.boxes} boxes + {item.loose_pieces} loose | {format_currency(item.discounted_line_total)}",
            "details": f"Original invoice: {invoice.invoice_number}; reason: {record.reason}",
            "raw": {"return_id": record.id, "invoice_id": invoice.id, "invoice_item_id": item.invoice_item_id},
        })
    exchange_rows = db.execute(
        select(ReturnExchangeItem, InvoiceReturn, Invoice, User.username, Branch.name)
        .join(InvoiceReturn, InvoiceReturn.id == ReturnExchangeItem.return_id)
        .join(Invoice, Invoice.id == InvoiceReturn.invoice_id)
        .join(User, User.id == InvoiceReturn.user_id)
        .join(Branch, Branch.id == ReturnExchangeItem.source_branch_id)
        .where(ReturnExchangeItem.product_id == product_id)
    ).all()
    for item, record, invoice, username, branch_name in exchange_rows:
        timeline.append({
            "date": record.return_date, "user": username, "branch": branch_name,
            "category": "Returns", "action": "Exchange Item Issued", "reference": record.return_number,
            "summary": f"{item.boxes} boxes + {item.loose_pieces} loose | {format_currency(item.line_total)}",
            "details": f"Original invoice: {invoice.invoice_number}; reason: {record.reason}",
            "raw": {"return_id": record.id, "invoice_id": invoice.id, "exchange_item_id": item.id},
        })
    if date_from or date_to:
        timeline = [row for row in timeline if _matches_business_date(row["date"], date_from, date_to)]
    timeline.sort(key=lambda row: row["date"], reverse=True)
    return {"product": {"id": product.id, "name": product.name, "tile_size": product.tile_size,
                         "item_code": product.item_code}, "timeline": timeline}


def _stock_summary(product: Product, tx: StockTransaction) -> str:
    quantity = f"{tx.boxes} boxes + {tx.loose_pieces} loose" if tx.item_type == "tile" else f"{tx.quantity} units"
    return f"{product.name} - {product.tile_size} | {tx.grade or ''} | {quantity}"


def _stock_reference(tx: StockTransaction) -> str:
    if tx.dc_number:
        return tx.dc_number
    match = re.search(r"(?:invoice|exchange|return)\s+([A-Z]{2,}-[A-Z0-9-]+)", tx.notes or "", re.IGNORECASE)
    return match.group(1) if match else ""


# Keep this numeric catch-all after every named /activity-log sub-route.
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
