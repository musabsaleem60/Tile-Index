from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import ensure_branch_access, get_current_user
from app.db.session import get_db
from app.models.entities import Branch, Invoice, InvoiceReturn, User
from app.schemas.common import InvoiceReturnOut, ReturnSettlementIn
from app.services.returns import add_settlement, get_return


router = APIRouter(prefix="/returns", tags=["returns"])


@router.get("")
def search_returns(
    branch_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    return_number: str | None = Query(default=None, max_length=80),
    invoice_number: str | None = Query(default=None, max_length=80),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Search completed returns without requiring the original invoice first."""
    if branch_id is not None:
        ensure_branch_access(current_user, branch_id)

    stmt = (
        select(InvoiceReturn, Invoice, Branch)
        .join(Invoice, Invoice.id == InvoiceReturn.invoice_id)
        .join(Branch, Branch.id == InvoiceReturn.branch_id)
        .options(selectinload(InvoiceReturn.settlements))
        .order_by(InvoiceReturn.return_date.desc(), InvoiceReturn.id.desc())
    )
    if current_user.role != "admin" and current_user.branch_id is not None:
        stmt = stmt.where(InvoiceReturn.branch_id == current_user.branch_id)
    elif branch_id is not None:
        stmt = stmt.where(InvoiceReturn.branch_id == branch_id)
    business_tz = ZoneInfo("Asia/Karachi")
    if date_from:
        start_utc = datetime.combine(date_from, time.min, tzinfo=business_tz).astimezone(timezone.utc)
        stmt = stmt.where(InvoiceReturn.return_date >= start_utc)
    if date_to:
        end_utc = datetime.combine(date_to, time.max, tzinfo=business_tz).astimezone(timezone.utc)
        stmt = stmt.where(InvoiceReturn.return_date <= end_utc)
    if return_number:
        stmt = stmt.where(InvoiceReturn.return_number.ilike(f"%{return_number.strip()}%"))
    if invoice_number:
        stmt = stmt.where(Invoice.invoice_number.ilike(f"%{invoice_number.strip()}%"))

    rows = []
    for record, invoice, branch in db.execute(stmt).all():
        settled_amount = sum(float(row.amount) for row in record.settlements)
        outstanding_amount = max(0.0, abs(float(record.difference_amount)) - settled_amount)
        rows.append({
            "id": record.id,
            "return_number": record.return_number,
            "return_date": record.return_date,
            "invoice_id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "branch_id": branch.id,
            "branch_name": branch.name,
            "customer_name": invoice.customer_name,
            "returned_value": float(record.returned_value),
            "exchange_value": float(record.exchange_value),
            "difference_amount": float(record.difference_amount),
            "settled_amount": settled_amount,
            "outstanding_amount": outstanding_amount,
            "settlement_status": "Settled" if outstanding_amount <= 0 else "Outstanding",
        })
    return rows


@router.get("/{return_id}", response_model=InvoiceReturnOut)
def detail(return_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    record = db.get(InvoiceReturn, return_id)
    if not record:
        raise HTTPException(status_code=404, detail="Return not found")
    ensure_branch_access(current_user, record.branch_id)
    return get_return(db, return_id)


@router.post("/{return_id}/settlements", response_model=InvoiceReturnOut)
def settle(
    return_id: int,
    payload: ReturnSettlementIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = db.get(InvoiceReturn, return_id)
    if not record:
        raise HTTPException(status_code=404, detail="Return not found")
    ensure_branch_access(current_user, record.branch_id)
    result = add_settlement(db, return_id, payload, current_user)
    db.commit()
    return result
