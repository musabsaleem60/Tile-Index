from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.entities import Accessory, Branch, Product, SanitaryProduct, User
from app.schemas.common import (
    AccessoryIn,
    AccessoryOut,
    BranchOut,
    ProductIn,
    ProductOut,
    SanitaryProductIn,
    SanitaryProductOut,
)
from app.services.audit import write_audit_log


router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/branches", response_model=list[BranchOut])
def list_branches(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = select(Branch).order_by(Branch.name)
    if current_user.role == "employee":
        query = query.where(Branch.id == current_user.branch_id)
    return db.scalars(query).all()


@router.get("/products", response_model=list[ProductOut])
def list_products(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.scalars(select(Product).order_by(Product.name, Product.tile_size)).all()


@router.post("/products", response_model=ProductOut, dependencies=[Depends(require_admin)])
def create_product(payload: ProductIn, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    product = Product(**payload.model_dump())
    db.add(product)
    write_audit_log(db, current_user, "Product Added", payload.model_dump())
    db.commit()
    db.refresh(product)
    return product


@router.put("/products/{product_id}", response_model=ProductOut, dependencies=[Depends(require_admin)])
def update_product(product_id: int, payload: ProductIn, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    for key, value in payload.model_dump().items():
        setattr(product, key, value)
    write_audit_log(db, current_user, "Product Edited", {"product_id": product_id, **payload.model_dump()})
    db.commit()
    db.refresh(product)
    return product


@router.delete("/products/{product_id}", dependencies=[Depends(require_admin)])
def delete_product(product_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    write_audit_log(db, current_user, "Product Deleted", {"product_id": product_id, "name": product.name})
    db.delete(product)
    db.commit()
    return {"status": "deleted"}


@router.get("/accessories", response_model=list[AccessoryOut])
def list_accessories(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.scalars(select(Accessory).order_by(Accessory.category, Accessory.company)).all()


@router.post("/accessories", response_model=AccessoryOut, dependencies=[Depends(require_admin)])
def create_accessory(payload: AccessoryIn, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    accessory = Accessory(**payload.model_dump())
    db.add(accessory)
    write_audit_log(db, current_user, "Accessory Added", payload.model_dump())
    db.commit()
    db.refresh(accessory)
    return accessory


@router.put("/accessories/{accessory_id}", response_model=AccessoryOut, dependencies=[Depends(require_admin)])
def update_accessory(accessory_id: int, payload: AccessoryIn, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    accessory = db.get(Accessory, accessory_id)
    if not accessory:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Accessory not found")
    for key, value in payload.model_dump().items():
        setattr(accessory, key, value)
    write_audit_log(db, current_user, "Accessory Edited", {"accessory_id": accessory_id, **payload.model_dump()})
    db.commit()
    db.refresh(accessory)
    return accessory


@router.delete("/accessories/{accessory_id}", dependencies=[Depends(require_admin)])
def delete_accessory(accessory_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    accessory = db.get(Accessory, accessory_id)
    if not accessory:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Accessory not found")
    write_audit_log(db, current_user, "Accessory Deleted", {"accessory_id": accessory_id, "name": accessory.name})
    db.delete(accessory)
    db.commit()
    return {"status": "deleted"}


@router.get("/sanitary", response_model=list[SanitaryProductOut])
def list_sanitary_products(
    company: str | None = None,
    category: str | None = None,
    color: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = select(SanitaryProduct)
    if company:
        query = query.where(SanitaryProduct.company_name == company)
    if category:
        query = query.where(SanitaryProduct.product_category == category)
    if color:
        query = query.where(SanitaryProduct.color == color)
    return db.scalars(query.order_by(SanitaryProduct.company_name, SanitaryProduct.product_category, SanitaryProduct.color)).all()


@router.post("/sanitary", response_model=SanitaryProductOut, dependencies=[Depends(require_admin)])
def create_sanitary_product(payload: SanitaryProductIn, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    product = SanitaryProduct(**payload.model_dump())
    db.add(product)
    write_audit_log(db, current_user, "Sanitary Product Added", payload.model_dump())
    db.commit()
    db.refresh(product)
    return product


@router.put("/sanitary/{sanitary_product_id}", response_model=SanitaryProductOut, dependencies=[Depends(require_admin)])
def update_sanitary_product(sanitary_product_id: int, payload: SanitaryProductIn, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    product = db.get(SanitaryProduct, sanitary_product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sanitary product not found")
    for key, value in payload.model_dump().items():
        setattr(product, key, value)
    write_audit_log(db, current_user, "Sanitary Product Edited", {"sanitary_product_id": sanitary_product_id, **payload.model_dump()})
    db.commit()
    db.refresh(product)
    return product


@router.delete("/sanitary/{sanitary_product_id}", dependencies=[Depends(require_admin)])
def delete_sanitary_product(sanitary_product_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    product = db.get(SanitaryProduct, sanitary_product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sanitary product not found")
    write_audit_log(db, current_user, "Sanitary Product Deleted", {"sanitary_product_id": sanitary_product_id, "sku": product.sku})
    db.delete(product)
    db.commit()
    return {"status": "deleted"}
