from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import ensure_branch_access, get_current_user, require_product_manager
from app.db.session import get_db
from app.models.entities import LoosePcsInventory, LoosePcsProduct, StockTransaction, User
from app.schemas.common import LoosePcsInventoryOut, LoosePcsProductIn, LoosePcsProductOut, SimpleQuantityRequest
from app.services.audit import write_audit_log


catalog_router = APIRouter(prefix="/catalog/loose-pcs", tags=["loose-pcs"])
inventory_router = APIRouter(prefix="/inventory/loose-pcs", tags=["loose-pcs"])


def _label(product: LoosePcsProduct) -> str:
    return f"{product.name} - {product.size}"


def _clean(payload: LoosePcsProductIn) -> dict:
    name, size = payload.name.strip(), payload.size.strip().lower()
    if not name or not size:
        raise HTTPException(status_code=400, detail="Name and size are required")
    return {"name": name, "size": size, "price": payload.price}


@catalog_router.get("", response_model=list[LoosePcsProductOut])
def list_products(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.scalars(select(LoosePcsProduct).order_by(LoosePcsProduct.name, LoosePcsProduct.size)).all()


@catalog_router.post("", response_model=LoosePcsProductOut, dependencies=[Depends(require_product_manager)])
def create_product(payload: LoosePcsProductIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    values = _clean(payload)
    product = LoosePcsProduct(**values, sku=f"PENDING-{uuid4().hex}")
    db.add(product)
    try:
        db.flush()
        product.sku = f"LPC-{product.id:06d}"
        write_audit_log(db, user, "Loose Pcs Added", {"loose_pcs_product_id": product.id, **values, "sku": product.sku}, user.branch_id, loose_pcs_product_id=product.id)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Loose Pcs name and size already exist") from exc
    db.refresh(product)
    return product


@catalog_router.put("/{product_id}", response_model=LoosePcsProductOut, dependencies=[Depends(require_product_manager)])
def update_product(product_id: int, payload: LoosePcsProductIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    product = db.get(LoosePcsProduct, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Loose Pcs product not found")
    before = {"name": product.name, "size": product.size, "price": float(product.price)}
    values = _clean(payload)
    for key, value in values.items():
        setattr(product, key, value)
    write_audit_log(db, user, "Loose Pcs Edited", {"loose_pcs_product_id": product.id, "before": before, "after": values, "name": product.name, "size": product.size}, user.branch_id, loose_pcs_product_id=product.id)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Loose Pcs name and size already exist") from exc
    db.refresh(product)
    return product


@catalog_router.delete("/{product_id}", dependencies=[Depends(require_product_manager)])
def delete_product(product_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    product = db.get(LoosePcsProduct, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Loose Pcs product not found")
    rows = db.scalars(select(LoosePcsInventory).where(LoosePcsInventory.product_id == product_id).with_for_update()).all()
    if any(row.quantity for row in rows):
        raise HTTPException(status_code=409, detail="Remove remaining stock before deleting this product")
    write_audit_log(db, user, "Loose Pcs Deleted", {"loose_pcs_product_id": product.id, "name": product.name, "size": product.size, "sku": product.sku}, user.branch_id)
    try:
        for row in rows:
            db.delete(row)
        db.delete(product)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="This product has stock or sales history and cannot be deleted") from exc
    return {"status": "deleted"}


@inventory_router.get("/{branch_id}", response_model=list[LoosePcsInventoryOut])
def list_inventory(branch_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ensure_branch_access(user, branch_id)
    return db.scalars(select(LoosePcsInventory).where(LoosePcsInventory.branch_id == branch_id)).all()


def _adjust(product_id: int, payload: SimpleQuantityRequest, direction: str, db: Session, user: User):
    ensure_branch_access(user, payload.branch_id)
    product = db.get(LoosePcsProduct, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Loose Pcs product not found")
    reason = (payload.notes or "").strip()
    if direction == "OUT" and len(reason) < 5:
        raise HTTPException(status_code=400, detail="Please enter a reason for removing stock.")
    row = db.scalar(select(LoosePcsInventory).where(
        LoosePcsInventory.branch_id == payload.branch_id,
        LoosePcsInventory.product_id == product_id,
    ).with_for_update())
    if direction == "OUT" and (not row or row.quantity < payload.quantity):
        raise HTTPException(status_code=400, detail="Insufficient Loose Pcs stock")
    if not row:
        row = LoosePcsInventory(branch_id=payload.branch_id, product_id=product_id, quantity=0)
        db.add(row)
    row.quantity += payload.quantity if direction == "IN" else -payload.quantity
    dc_number = (payload.dc_number or "").strip() or None
    db.add(StockTransaction(
        user_id=user.id, branch_id=payload.branch_id, loose_pcs_product_id=product_id,
        item_type="loose_pcs", transaction_type=direction, quantity=payload.quantity,
        notes=reason or None, dc_number=dc_number,
    ))
    write_audit_log(db, user, f"Loose Pcs Stock {direction}", {
        "loose_pcs_product_id": product_id, "name": _label(product), "quantity": payload.quantity,
        "reason": reason or None, "dc_number": dc_number,
    }, payload.branch_id, loose_pcs_product_id=product_id)
    db.commit()
    db.refresh(row)
    return row


@inventory_router.post("/{product_id}/stock-in", response_model=LoosePcsInventoryOut)
def stock_in(product_id: int, payload: SimpleQuantityRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _adjust(product_id, payload, "IN", db, user)


@inventory_router.post("/{product_id}/stock-out", response_model=LoosePcsInventoryOut)
def stock_out(product_id: int, payload: SimpleQuantityRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _adjust(product_id, payload, "OUT", db, user)
