from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from app.api.deps import ensure_branch_access, get_current_user
from app.db.session import get_db
from app.models.entities import Invoice, InvoicePayment, User
from app.schemas.common import InvoiceCreate, InvoiceOut, InvoicePaymentIn, InvoicePaymentOut, InvoiceVoidRequest
from app.services.invoices import create_invoice, record_invoice_payment, void_invoice


router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.post("", response_model=InvoiceOut)
def create(payload: InvoiceCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ensure_branch_access(current_user, payload.branch_id)
    invoice = create_invoice(db, payload, current_user)
    db.commit()
    db.refresh(invoice)
    return invoice


@router.post("/{invoice_id}/void", response_model=InvoiceOut)
def void(
    invoice_id: int,
    payload: InvoiceVoidRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    invoice = void_invoice(db, invoice_id, payload.reason, current_user)
    db.commit()
    db.refresh(invoice)
    return invoice


@router.post("/{invoice_id}/payments", response_model=InvoiceOut)
def create_payment(
    invoice_id: int,
    payload: InvoicePaymentIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    invoice = db.get(Invoice, invoice_id)
    if invoice:
        ensure_branch_access(current_user, invoice.branch_id)
    updated_invoice = record_invoice_payment(db, invoice_id, payload, current_user)
    db.commit()
    db.refresh(updated_invoice)
    return updated_invoice


@router.get("/{invoice_id}/payments", response_model=list[InvoicePaymentOut])
def list_payments(invoice_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    invoice = db.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    ensure_branch_access(current_user, invoice.branch_id)
    return db.scalars(
        select(InvoicePayment)
        .where(InvoicePayment.invoice_id == invoice_id)
        .order_by(InvoicePayment.payment_date.desc(), InvoicePayment.id.desc())
    ).all()


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
