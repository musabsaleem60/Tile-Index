"""Master Sanitary catalogue and per-branch piece stock."""

from uuid import uuid4
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import ensure_branch_access, get_current_user, require_product_manager
from app.db.session import get_db
from app.models.entities import MasterSanitaryInventory, MasterSanitaryProduct, StockTransaction, User
from app.schemas.common import (
    MasterSanitaryInventoryOut, MasterSanitaryPriceIn, MasterSanitaryProductIn, MasterSanitaryProductOut,
    SimpleQuantityRequest,
)
from app.services.audit import write_audit_log


catalog_router = APIRouter(prefix="/catalog/master-sanitary", tags=["master-sanitary"])
inventory_router = APIRouter(prefix="/inventory/master-sanitary", tags=["master-sanitary"])


def _clean(payload: MasterSanitaryProductIn) -> dict:
    name = " ".join(payload.name.split())
    color = " ".join(payload.color.split())
    if not name or not color:
        raise HTTPException(status_code=400, detail="Name and color are required")
    return {
        "name": name, "color": color,
        "normalized_name": name.casefold(), "normalized_color": color.casefold(),
    }


@catalog_router.get("", response_model=list[MasterSanitaryProductOut])
def list_products(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.scalars(select(MasterSanitaryProduct).order_by(MasterSanitaryProduct.name, MasterSanitaryProduct.color)).all()


@catalog_router.post("", response_model=MasterSanitaryProductOut, dependencies=[Depends(require_product_manager)])
def create_product(payload: MasterSanitaryProductIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    values = _clean(payload)
    product = MasterSanitaryProduct(**values, sku=f"PENDING-{uuid4().hex}")
    db.add(product)
    try:
        db.flush()
        product.sku = f"MS-{product.id:06d}"
        write_audit_log(db, user, "Master Sanitary Added", {
            "master_sanitary_product_id": product.id, "name": product.name,
            "color": product.color, "sku": product.sku,
        }, user.branch_id, master_sanitary_product_id=product.id)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Master Sanitary name and color already exist") from exc
    db.refresh(product)
    return product


@catalog_router.put("/{product_id}", response_model=MasterSanitaryProductOut, dependencies=[Depends(require_product_manager)])
def update_product(product_id: int, payload: MasterSanitaryProductIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    product = db.get(MasterSanitaryProduct, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Master Sanitary product not found")
    before = {"name": product.name, "color": product.color}
    values = _clean(payload)
    for key, value in values.items():
        setattr(product, key, value)
    write_audit_log(db, user, "Master Sanitary Edited", {
        "master_sanitary_product_id": product.id, "before": before,
        "after": {"name": product.name, "color": product.color},
    }, user.branch_id, master_sanitary_product_id=product.id)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Master Sanitary name and color already exist") from exc
    db.refresh(product)
    return product


@catalog_router.delete("/{product_id}", dependencies=[Depends(require_product_manager)])
def delete_product(product_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    product = db.get(MasterSanitaryProduct, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Master Sanitary product not found")
    rows = db.scalars(select(MasterSanitaryInventory).where(MasterSanitaryInventory.product_id == product_id).with_for_update()).all()
    if any(row.quantity for row in rows):
        raise HTTPException(status_code=409, detail="Remove remaining stock before deleting this product")
    write_audit_log(db, user, "Master Sanitary Deleted", {
        "master_sanitary_product_id": product.id, "name": product.name,
        "color": product.color, "sku": product.sku,
    }, user.branch_id)
    try:
        for row in rows:
            db.delete(row)
        db.delete(product)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="This product has stock or sales history and cannot be deleted") from exc
    return {"status": "deleted"}


@inventory_router.get("/{branch_id}", response_model=list[MasterSanitaryInventoryOut])
def list_inventory(branch_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ensure_branch_access(user, branch_id)
    return db.scalars(select(MasterSanitaryInventory).where(MasterSanitaryInventory.branch_id == branch_id)).all()


@inventory_router.put("/{product_id}/price", response_model=MasterSanitaryInventoryOut)
def save_price(product_id: int, payload: MasterSanitaryPriceIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ensure_branch_access(user, payload.branch_id)
    product = db.get(MasterSanitaryProduct, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Master Sanitary product not found")
    row = db.scalar(select(MasterSanitaryInventory).where(
        MasterSanitaryInventory.branch_id == payload.branch_id,
        MasterSanitaryInventory.product_id == product_id,
    ).with_for_update())
    if not row:
        row = MasterSanitaryInventory(branch_id=payload.branch_id, product_id=product_id, quantity=0)
        db.add(row)
    old_price = float(row.price) if row.price is not None else None
    row.price = Decimal(str(payload.price))
    write_audit_log(db, user, "Master Sanitary Price Updated", {
        "master_sanitary_product_id": product_id, "name": f"{product.name} - {product.color}",
        "old_price": old_price, "new_price": float(row.price),
    }, payload.branch_id, event_category="Pricing", master_sanitary_product_id=product_id)
    db.commit()
    db.refresh(row)
    return row


def _adjust(product_id: int, payload: SimpleQuantityRequest, direction: str, db: Session, user: User):
    ensure_branch_access(user, payload.branch_id)
    product = db.get(MasterSanitaryProduct, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Master Sanitary product not found")
    reason = (payload.notes or "").strip()
    if direction == "OUT" and len(reason) < 5:
        raise HTTPException(status_code=400, detail="Please enter a reason for removing stock.")
    row = db.scalar(select(MasterSanitaryInventory).where(
        MasterSanitaryInventory.branch_id == payload.branch_id,
        MasterSanitaryInventory.product_id == product_id,
    ).with_for_update())
    if direction == "OUT" and (not row or row.quantity < payload.quantity):
        raise HTTPException(status_code=400, detail="Insufficient Master Sanitary stock")
    if not row:
        row = MasterSanitaryInventory(branch_id=payload.branch_id, product_id=product_id, quantity=0)
        db.add(row)
    row.quantity += payload.quantity if direction == "IN" else -payload.quantity
    dc_number = (payload.dc_number or "").strip() or None
    db.add(StockTransaction(
        user_id=user.id, branch_id=payload.branch_id, master_sanitary_product_id=product_id,
        item_type="master_sanitary", transaction_type=direction, quantity=payload.quantity,
        notes=reason or None, dc_number=dc_number,
    ))
    write_audit_log(db, user, f"Master Sanitary Stock {direction}", {
        "master_sanitary_product_id": product_id, "name": f"{product.name} - {product.color}",
        "quantity": payload.quantity, "reason": reason or None, "dc_number": dc_number,
    }, payload.branch_id, master_sanitary_product_id=product_id)
    db.commit()
    db.refresh(row)
    return row


@inventory_router.post("/{product_id}/stock-in", response_model=MasterSanitaryInventoryOut)
def stock_in(product_id: int, payload: SimpleQuantityRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _adjust(product_id, payload, "IN", db, user)


@inventory_router.post("/{product_id}/stock-out", response_model=MasterSanitaryInventoryOut)
def stock_out(product_id: int, payload: SimpleQuantityRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _adjust(product_id, payload, "OUT", db, user)
