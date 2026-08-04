from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import ensure_branch_access, get_current_user
from app.db.session import get_db
from app.models.entities import (
    AccessoryInventory,
    Inventory,
    Product,
    SanitaryInventory,
    SanitaryStockTransaction,
    StockTransaction,
    User,
)
from app.schemas.common import AccessoryInventoryOut, InventoryOut, SanitaryInventoryOut, SimpleQuantityRequest, StockInRequest
from app.services.audit import write_audit_log


router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("/tiles/{branch_id}", response_model=list[InventoryOut])
def list_tile_inventory(branch_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ensure_branch_access(current_user, branch_id)
    return db.scalars(select(Inventory).where(Inventory.branch_id == branch_id).order_by(Inventory.product_id, Inventory.grade)).all()


@router.post("/tiles/stock-in", response_model=InventoryOut)
def tile_stock_in(payload: StockInRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ensure_branch_access(current_user, payload.branch_id)
    if payload.boxes == 0 and payload.loose_pieces == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Stock quantity is required")

    product = db.get(Product, payload.product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    inventory = db.scalar(
        select(Inventory).where(
            Inventory.branch_id == payload.branch_id,
            Inventory.product_id == payload.product_id,
            Inventory.grade == payload.grade,
        ).with_for_update()
    )
    if not inventory:
        inventory = Inventory(
            branch_id=payload.branch_id,
            product_id=payload.product_id,
            grade=payload.grade,
            boxes=0,
            loose_pieces=0,
            rate_per_sqm=payload.rate_per_sqm,
            rate_per_box=payload.rate_per_box,
            rate_per_piece=payload.rate_per_piece,
        )
        db.add(inventory)

    inventory.boxes += payload.boxes
    inventory.loose_pieces += payload.loose_pieces
    while inventory.loose_pieces >= product.pieces_per_box:
        inventory.boxes += 1
        inventory.loose_pieces -= product.pieces_per_box
    inventory.rate_per_sqm = payload.rate_per_sqm
    inventory.rate_per_box = payload.rate_per_box
    inventory.rate_per_piece = payload.rate_per_piece

    db.add(StockTransaction(
        user_id=current_user.id,
        branch_id=payload.branch_id,
        product_id=payload.product_id,
        grade=payload.grade,
        transaction_type="IN",
        boxes=payload.boxes,
        loose_pieces=payload.loose_pieces,
        notes=payload.notes,
    ))
    write_audit_log(db, current_user, "Stock IN", payload.model_dump(), payload.branch_id)
    db.commit()
    db.refresh(inventory)
    return inventory


@router.post("/tiles/stock-out", response_model=InventoryOut)
def tile_stock_out(payload: StockInRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ensure_branch_access(current_user, payload.branch_id)
    if payload.boxes == 0 and payload.loose_pieces == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Stock quantity is required")

    product = db.get(Product, payload.product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    inventory = db.scalar(
        select(Inventory).where(
            Inventory.branch_id == payload.branch_id,
            Inventory.product_id == payload.product_id,
            Inventory.grade == payload.grade,
        ).with_for_update()
    )
    if not inventory:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No stock found")

    available = inventory.boxes * product.pieces_per_box + inventory.loose_pieces
    requested = payload.boxes * product.pieces_per_box + payload.loose_pieces
    if requested > available:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient stock")

    remaining = available - requested
    inventory.boxes = remaining // product.pieces_per_box
    inventory.loose_pieces = remaining % product.pieces_per_box

    db.add(StockTransaction(
        user_id=current_user.id,
        branch_id=payload.branch_id,
        product_id=payload.product_id,
        grade=payload.grade,
        transaction_type="OUT",
        boxes=payload.boxes,
        loose_pieces=payload.loose_pieces,
        notes=payload.notes,
    ))
    write_audit_log(db, current_user, "Stock OUT", payload.model_dump(), payload.branch_id)
    db.commit()
    db.refresh(inventory)
    return inventory


@router.get("/accessories/{branch_id}", response_model=list[AccessoryInventoryOut])
def list_accessory_inventory(branch_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ensure_branch_access(current_user, branch_id)
    return db.scalars(select(AccessoryInventory).where(AccessoryInventory.branch_id == branch_id)).all()


@router.post("/accessories/{accessory_id}/stock-in", response_model=AccessoryInventoryOut)
def accessory_stock_in(accessory_id: int, payload: SimpleQuantityRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ensure_branch_access(current_user, payload.branch_id)
    inventory = db.scalar(
        select(AccessoryInventory).where(
            AccessoryInventory.branch_id == payload.branch_id,
            AccessoryInventory.accessory_id == accessory_id,
        ).with_for_update()
    )
    if not inventory:
        inventory = AccessoryInventory(branch_id=payload.branch_id, accessory_id=accessory_id, quantity=0)
        db.add(inventory)
    inventory.quantity += payload.quantity
    write_audit_log(db, current_user, "Accessory Stock IN", {"accessory_id": accessory_id, **payload.model_dump()}, payload.branch_id)
    db.commit()
    db.refresh(inventory)
    return inventory


@router.post("/accessories/{accessory_id}/stock-out", response_model=AccessoryInventoryOut)
def accessory_stock_out(accessory_id: int, payload: SimpleQuantityRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ensure_branch_access(current_user, payload.branch_id)
    inventory = db.scalar(
        select(AccessoryInventory).where(
            AccessoryInventory.branch_id == payload.branch_id,
            AccessoryInventory.accessory_id == accessory_id,
        ).with_for_update()
    )
    if not inventory or inventory.quantity < payload.quantity:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient accessory stock")
    inventory.quantity -= payload.quantity
    write_audit_log(db, current_user, "Accessory Stock OUT", {"accessory_id": accessory_id, **payload.model_dump()}, payload.branch_id)
    db.commit()
    db.refresh(inventory)
    return inventory


@router.get("/sanitary/{branch_id}", response_model=list[SanitaryInventoryOut])
def list_sanitary_inventory(branch_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ensure_branch_access(current_user, branch_id)
    return db.scalars(select(SanitaryInventory).where(SanitaryInventory.branch_id == branch_id)).all()


@router.post("/sanitary/{sanitary_product_id}/stock-in", response_model=SanitaryInventoryOut)
def sanitary_stock_in(
    sanitary_product_id: int,
    payload: SimpleQuantityRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_branch_access(current_user, payload.branch_id)
    inventory = db.scalar(
        select(SanitaryInventory).where(
            SanitaryInventory.branch_id == payload.branch_id,
            SanitaryInventory.sanitary_product_id == sanitary_product_id,
        ).with_for_update()
    )
    if not inventory:
        inventory = SanitaryInventory(branch_id=payload.branch_id, sanitary_product_id=sanitary_product_id, quantity=0)
        db.add(inventory)
    inventory.quantity += payload.quantity
    db.add(SanitaryStockTransaction(
        user_id=current_user.id,
        branch_id=payload.branch_id,
        sanitary_product_id=sanitary_product_id,
        transaction_type="IN",
        quantity=payload.quantity,
        notes=payload.notes,
    ))
    write_audit_log(db, current_user, "Sanitary Stock IN", {"sanitary_product_id": sanitary_product_id, **payload.model_dump()}, payload.branch_id)
    db.commit()
    db.refresh(inventory)
    return inventory


@router.post("/sanitary/{sanitary_product_id}/stock-out", response_model=SanitaryInventoryOut)
def sanitary_stock_out(
    sanitary_product_id: int,
    payload: SimpleQuantityRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_branch_access(current_user, payload.branch_id)
    inventory = db.scalar(
        select(SanitaryInventory).where(
            SanitaryInventory.branch_id == payload.branch_id,
            SanitaryInventory.sanitary_product_id == sanitary_product_id,
        ).with_for_update()
    )
    if not inventory or inventory.quantity < payload.quantity:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient sanitary stock")

    inventory.quantity -= payload.quantity
    db.add(SanitaryStockTransaction(
        user_id=current_user.id,
        branch_id=payload.branch_id,
        sanitary_product_id=sanitary_product_id,
        transaction_type="OUT",
        quantity=payload.quantity,
        notes=payload.notes,
    ))
    write_audit_log(db, current_user, "Sanitary Stock OUT", {"sanitary_product_id": sanitary_product_id, **payload.model_dump()}, payload.branch_id)
    db.commit()
    db.refresh(inventory)
    return inventory
