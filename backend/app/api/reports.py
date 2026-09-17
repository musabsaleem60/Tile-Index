from collections import defaultdict
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload
from app.api.deps import ensure_branch_access, get_current_user
from app.db.session import get_db
from app.models.entities import Branch, Inventory, Invoice, SanitaryInventory, User
from app.services.tile_pricing import resolve_tile_price


router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/daily-sales/{branch_id}")
def daily_sales(branch_id: int, report_date: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ensure_branch_access(current_user, branch_id)
    invoices = db.scalars(
        select(Invoice).where(
            Invoice.branch_id == branch_id,
            Invoice.status == "active",
        )
    ).all()
    day_invoices = [invoice for invoice in invoices if _business_date(invoice.invoice_date) == report_date]
    return {
        "branch_id": branch_id,
        "date": report_date,
        "total_invoices": len(day_invoices),
        "total_sales": sum(invoice.grand_total for invoice in day_invoices),
        "total_paid": sum(invoice.paid_amount for invoice in day_invoices),
        "total_balance": sum(invoice.balance for invoice in day_invoices),
        "invoices": [
            {
                "invoice_number": invoice.invoice_number,
                "customer_name": invoice.customer_name,
                "invoice_date": invoice.invoice_date,
                "grand_total": invoice.grand_total,
                "paid_amount": invoice.paid_amount,
                "balance": invoice.balance,
            }
            for invoice in day_invoices
        ],
    }


def _business_date(value) -> str:
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(ZoneInfo("Asia/Karachi")).date().isoformat()


@router.get("/stock/{branch_id}")
def branch_stock(branch_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ensure_branch_access(current_user, branch_id)
    branch = db.get(Branch, branch_id)
    tile_rows = db.scalars(
        select(Inventory)
        .where(Inventory.branch_id == branch_id)
        .options(selectinload(Inventory.product))
        .order_by(Inventory.product_id, Inventory.grade)
    ).all()
    sanitary_rows = db.scalars(
        select(SanitaryInventory)
        .where(SanitaryInventory.branch_id == branch_id)
        .options(selectinload(SanitaryInventory.sanitary_product))
    ).all()
    tile_items, tile_total = _tile_stock_items(db, tile_rows)
    sanitary_items, sanitary_total = _sanitary_stock_items(sanitary_rows)
    return {
        "branch_id": branch_id,
        "branch_name": branch.name if branch else f"Branch {branch_id}",
        "tile_stock_lines": len(tile_items),
        "sanitary_stock_lines": len(sanitary_items),
        "total_value": tile_total + sanitary_total,
        "items": tile_items,
        "sanitary_items": sanitary_items,
    }


@router.get("/business-stock")
def business_stock(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    branches = db.scalars(select(Branch).order_by(Branch.name)).all()
    products = db.scalar(select(func.count()).select_from(Inventory)) or 0
    report_branches = []
    grand_total = 0
    total_sanitary = 0
    for branch in branches:
        tile_rows = db.scalars(
            select(Inventory)
            .where(Inventory.branch_id == branch.id)
            .options(selectinload(Inventory.product))
            .order_by(Inventory.product_id, Inventory.grade)
        ).all()
        sanitary_rows = db.scalars(
            select(SanitaryInventory)
            .where(SanitaryInventory.branch_id == branch.id)
            .options(selectinload(SanitaryInventory.sanitary_product))
        ).all()
        items, tile_total = _tile_stock_items(db, tile_rows)
        sanitary_items, sanitary_total = _sanitary_stock_items(sanitary_rows)
        branch_total = tile_total + sanitary_total
        total_sanitary += len(sanitary_items)
        grand_total += branch_total
        report_branches.append({
            "branch_id": branch.id,
            "branch_name": branch.name,
            "items": items,
            "sanitary_items": sanitary_items,
            "branch_total_value": branch_total,
        })
    return {
        "total_branches": len(branches),
        "total_products": products,
        "total_sanitary_products": total_sanitary,
        "total_value": grand_total,
        "branches": report_branches,
    }


@router.get("/monthly-sales")
def monthly_sales(
    date_from: str,
    date_to: str,
    branch_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if branch_id:
        ensure_branch_access(current_user, branch_id)
    branches = {branch.id: branch for branch in db.scalars(select(Branch)).all()}
    query = select(Invoice).where(Invoice.status == "active")
    if current_user.role == "employee" and current_user.branch_id is not None:
        query = query.where(Invoice.branch_id == current_user.branch_id)
    elif branch_id is not None:
        query = query.where(Invoice.branch_id == branch_id)

    rows = db.scalars(query).all()
    buckets = defaultdict(lambda: {"invoice_count": 0, "total_sales": 0.0, "total_paid": 0.0, "total_balance": 0.0})
    for invoice in rows:
        business_day = _business_date(invoice.invoice_date)
        if business_day < date_from or business_day > date_to:
            continue
        month = business_day[:7]
        key = (month, invoice.branch_id)
        bucket = buckets[key]
        bucket["invoice_count"] += 1
        bucket["total_sales"] += float(invoice.grand_total or 0)
        bucket["total_paid"] += float(invoice.paid_amount or 0)
        bucket["total_balance"] += float(invoice.balance or 0)

    items = []
    for (month, bucket_branch_id), data in sorted(buckets.items()):
        branch = branches.get(bucket_branch_id)
        items.append({
            "month": month,
            "branch_id": bucket_branch_id,
            "branch_name": branch.name if branch else f"Branch {bucket_branch_id}",
            **data,
        })

    return {
        "date_from": date_from,
        "date_to": date_to,
        "branch_id": branch_id,
        "items": items,
        "total_invoices": sum(item["invoice_count"] for item in items),
        "total_sales": sum(item["total_sales"] for item in items),
        "total_paid": sum(item["total_paid"] for item in items),
        "total_balance": sum(item["total_balance"] for item in items),
    }


def _tile_stock_items(db: Session, rows: list[Inventory]) -> tuple[list[dict], float]:
    items = []
    total_value = 0.0
    for inv in rows:
        product = inv.product
        if not product:
            continue
        total_pieces = int(inv.boxes or 0) * int(product.pieces_per_box or 0) + int(inv.loose_pieces or 0)
        price = resolve_tile_price(db, product, inv.grade)
        stock_value = None
        if price:
            stock_value = (int(inv.boxes or 0) * price.rate_per_box) + (int(inv.loose_pieces or 0) * price.rate_per_piece)
            total_value += stock_value
        items.append({
            "product_id": product.id,
            "product_name": product.name,
            "tile_size": product.tile_size,
            "grade": inv.grade,
            "boxes": inv.boxes,
            "loose_pieces": inv.loose_pieces,
            "total_pieces": total_pieces,
            "rate_source": price.source if price else None,
            "stock_value": stock_value,
            "value_display": _money(stock_value) if price else "No Rate Set",
        })
    return items, total_value


def _sanitary_stock_items(rows: list[SanitaryInventory]) -> tuple[list[dict], float]:
    items = []
    total_value = 0.0
    for inv in rows:
        product = inv.sanitary_product
        if not product:
            continue
        stock_value = int(inv.quantity or 0) * float(product.sale_price or 0)
        total_value += stock_value
        items.append({
            "sanitary_product_id": product.id,
            "company_name": product.company_name,
            "product_category": product.product_category,
            "color": product.color,
            "sku": product.sku,
            "quantity": inv.quantity,
            "sale_price": product.sale_price,
            "stock_value": stock_value,
            "value_display": _money(stock_value),
        })
    return items, total_value


def _money(value) -> str:
    return f"Rs. {float(value or 0):.2f}"
