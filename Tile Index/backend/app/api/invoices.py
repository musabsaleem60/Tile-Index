from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from app.api.deps import ensure_branch_access, get_current_user
from app.db.session import get_db
from app.models.entities import Invoice, User
from app.schemas.common import InvoiceCreate, InvoiceOut
from app.services.invoices import create_invoice


router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.post("", response_model=InvoiceOut)
def create(payload: InvoiceCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ensure_branch_access(current_user, payload.branch_id)
    invoice = create_invoice(db, payload, current_user)
    db.commit()
    db.refresh(invoice)
    return invoice


@router.get("/{invoice_id}", response_model=InvoiceOut)
def get_invoice(invoice_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    invoice = db.scalar(select(Invoice).where(Invoice.id == invoice_id).options(selectinload(Invoice.items)))
    if invoice:
        ensure_branch_access(current_user, invoice.branch_id)
    return invoice


@router.get("", response_model=list[InvoiceOut])
def search_invoices(
    branch_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Invoice).options(selectinload(Invoice.items)).order_by(Invoice.invoice_date.desc(), Invoice.id.desc())
    if current_user.role == "employee":
        query = query.where(Invoice.branch_id == current_user.branch_id)
    elif branch_id:
        query = query.where(Invoice.branch_id == branch_id)
    return db.scalars(query.limit(200)).all()
