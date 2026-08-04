from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.api.deps import ensure_branch_access, get_current_user, require_admin
from app.db.session import get_db
from app.models.entities import Inventory, Invoice, SanitaryInventory, User


router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/daily-sales/{branch_id}")
def daily_sales(branch_id: int, report_date: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ensure_branch_access(current_user, branch_id)
    rows = db.execute(
        select(
            func.count(Invoice.id),
            func.coalesce(func.sum(Invoice.grand_total), 0),
            func.coalesce(func.sum(Invoice.paid_amount), 0),
            func.coalesce(func.sum(Invoice.balance), 0),
        ).where(Invoice.branch_id == branch_id, func.date(Invoice.invoice_date) == report_date)
    ).one()
    return {
        "branch_id": branch_id,
        "date": report_date,
        "total_invoices": rows[0],
        "total_sales": rows[1],
        "total_paid": rows[2],
        "total_balance": rows[3],
    }


@router.get("/stock/{branch_id}")
def branch_stock(branch_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ensure_branch_access(current_user, branch_id)
    tile_rows = db.scalars(select(Inventory).where(Inventory.branch_id == branch_id)).all()
    sanitary_rows = db.scalars(select(SanitaryInventory).where(SanitaryInventory.branch_id == branch_id)).all()
    return {
        "branch_id": branch_id,
        "tile_stock_lines": len(tile_rows),
        "sanitary_stock_lines": len(sanitary_rows),
    }


@router.get("/business-stock", dependencies=[Depends(require_admin)])
def business_stock(db: Session = Depends(get_db)):
    tile_lines = db.scalar(select(func.count(Inventory.id))) or 0
    sanitary_lines = db.scalar(select(func.count(SanitaryInventory.id))) or 0
    return {
        "tile_stock_lines": tile_lines,
        "sanitary_stock_lines": sanitary_lines,
    }
