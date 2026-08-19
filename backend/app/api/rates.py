from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_admin, require_product_manager
from app.db.session import get_db
from app.models.entities import Branch, Product, ProductRateOverride, TileRate, TileSize, User
from app.schemas.common import (
    ProductRateOverrideIn,
    ProductRateOverrideRemove,
    RateRemovalReason,
    TileRateUpdate,
    TileSizeCreate,
)
from app.services.audit import write_audit_log


router = APIRouter(prefix="/rates", tags=["rates"])
GRADES = ("G1 Prime", "G2 Standard", "G3 Regular")


@router.get("/card")
def rate_card(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    sizes = db.scalars(select(TileSize).order_by(TileSize.tile_size)).all()
    rates = db.scalars(select(TileRate).where(TileRate.active.is_(True))).all()
    rate_by_key = {(rate.tile_size, rate.grade): rate for rate in rates}
    rows = []
    for size in sizes:
        rows.append({
            "tile_size": size.tile_size,
            "pieces_per_box": size.pieces_per_box,
            "area_per_box": size.area_per_box,
            "active": size.active,
            "rates": {
                grade: _rate_row(rate_by_key.get((size.tile_size, grade)))
                for grade in GRADES
            },
        })
    return rows


@router.get("/impact")
def rate_impact(
    tile_size: str = Query(min_length=1),
    grade: str = Query(min_length=1),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    return _impact(db, tile_size, grade)


@router.get("/size-status")
def size_status(
    tile_size: str = Query(min_length=1),
    db: Session = Depends(get_db),
    _: User = Depends(require_product_manager),
):
    tile_size = tile_size.strip()
    size = db.get(TileSize, tile_size)
    active_rates = db.scalars(
        select(TileRate).where(
            TileRate.tile_size == tile_size,
            TileRate.active.is_(True),
        )
    ).all()
    grades_with_rates = {rate.grade for rate in active_rates}
    missing_grades = [grade for grade in GRADES if grade not in grades_with_rates]
    return {
        "tile_size": tile_size,
        "size_exists": bool(size and size.active),
        "complete_rate_card": bool(size and size.active and not missing_grades),
        "missing_grades": missing_grades,
    }


@router.put("/card")
def update_card_rate(
    tile_size: str,
    grade: str,
    payload: TileRateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    if grade not in GRADES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid grade")
    rate = db.scalar(
        select(TileRate).where(
            TileRate.tile_size == tile_size,
            TileRate.grade == grade,
            TileRate.active.is_(True),
        )
    )
    if not rate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rate card row not found")

    old_rate = rate.rate_per_meter
    rate.rate_per_meter = payload.rate_per_meter
    impact = _impact(db, tile_size, grade)
    write_audit_log(
        db,
        current_user,
        "Rate Card Updated",
        {
            "tile_size": tile_size,
            "grade": grade,
            "old_rate": old_rate,
            "new_rate": payload.rate_per_meter,
            "reason": payload.reason,
            **impact,
        },
        current_user.branch_id,
    )
    db.commit()
    db.refresh(rate)
    return {"status": "updated", "rate": _rate_row(rate), "impact": impact}


@router.post("/sizes")
def create_tile_size(
    payload: TileSizeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    tile_size = payload.tile_size.strip()
    if db.get(TileSize, tile_size):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tile size already exists")

    size = TileSize(
        tile_size=tile_size,
        pieces_per_box=payload.pieces_per_box,
        area_per_box=payload.area_per_box,
        active=True,
    )
    db.add(size)
    grade_rates = {
        "G1 Prime": payload.g1_prime,
        "G2 Standard": payload.g2_standard,
        "G3 Regular": payload.g3_regular,
    }
    for grade, rate in grade_rates.items():
        db.add(TileRate(tile_size=tile_size, grade=grade, rate_per_meter=rate, active=True))

    write_audit_log(
        db,
        current_user,
        "Tile Size Added",
        {
            "tile_size": tile_size,
            "pieces_per_box": payload.pieces_per_box,
            "area_per_box": payload.area_per_box,
            "rates": grade_rates,
            "reason": payload.reason,
        },
        current_user.branch_id,
    )
    db.commit()
    return {"status": "created", "tile_size": tile_size, "rates": grade_rates}


@router.get("/overrides")
def list_overrides(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    overrides = db.scalars(
        select(ProductRateOverride)
        .where(ProductRateOverride.active.is_(True))
        .order_by(ProductRateOverride.product_id, ProductRateOverride.grade)
    ).all()
    return [_override_row(db, override) for override in overrides]


@router.post("/overrides")
def save_override(
    payload: ProductRateOverrideIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    if payload.grade not in GRADES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid grade")
    product = db.get(Product, payload.product_id)
    if not product or not product.active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    override = db.scalar(
        select(ProductRateOverride).where(
            ProductRateOverride.product_id == payload.product_id,
            ProductRateOverride.grade == payload.grade,
        )
    )
    old_rate = override.rate_per_meter if override and override.active else None
    if not override:
        override = ProductRateOverride(
            product_id=payload.product_id,
            grade=payload.grade,
            created_by_user_id=current_user.id,
        )
        db.add(override)
    override.rate_per_meter = payload.rate_per_meter
    override.reason = payload.reason
    override.active = True

    write_audit_log(
        db,
        current_user,
        "Product Rate Override Updated" if old_rate is not None else "Product Rate Override Added",
        {
            "product_id": product.id,
            "product_name": product.name,
            "tile_size": product.tile_size,
            "grade": payload.grade,
            "old_rate": old_rate,
            "new_rate": payload.rate_per_meter,
            "reason": payload.reason,
        },
        current_user.branch_id,
    )
    db.commit()
    db.refresh(override)
    return _override_row(db, override)


@router.delete("/overrides/{product_id}/{grade}")
def remove_override(
    product_id: int,
    grade: str,
    payload: RateRemovalReason,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    override = db.scalar(
        select(ProductRateOverride).where(
            ProductRateOverride.product_id == product_id,
            ProductRateOverride.grade == grade,
            ProductRateOverride.active.is_(True),
        )
    )
    if not override:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active override not found")
    product = db.get(Product, product_id)
    old_rate = override.rate_per_meter
    override.active = False
    override.reason = payload.reason
    write_audit_log(
        db,
        current_user,
        "Product Rate Override Removed",
        {
            "product_id": product_id,
            "product_name": product.name if product else None,
            "tile_size": product.tile_size if product else None,
            "grade": grade,
            "old_rate": old_rate,
            "reason": payload.reason,
        },
        current_user.branch_id,
    )
    db.commit()
    return {"status": "removed"}


@router.post("/overrides/remove")
def remove_override_post(
    payload: ProductRateOverrideRemove,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    override = db.scalar(
        select(ProductRateOverride).where(
            ProductRateOverride.product_id == payload.product_id,
            ProductRateOverride.grade == payload.grade,
            ProductRateOverride.active.is_(True),
        )
    )
    if not override:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active override not found")
    product = db.get(Product, payload.product_id)
    old_rate = override.rate_per_meter
    override.active = False
    override.reason = payload.reason
    write_audit_log(
        db,
        current_user,
        "Product Rate Override Removed",
        {
            "product_id": payload.product_id,
            "product_name": product.name if product else None,
            "tile_size": product.tile_size if product else None,
            "grade": payload.grade,
            "old_rate": old_rate,
            "reason": payload.reason,
        },
        current_user.branch_id,
    )
    db.commit()
    return {"status": "removed"}


def _rate_row(rate: TileRate | None):
    if not rate:
        return None
    return {
        "id": rate.id,
        "tile_size": rate.tile_size,
        "grade": rate.grade,
        "rate_per_meter": rate.rate_per_meter,
        "active": rate.active,
    }


def _override_row(db: Session, override: ProductRateOverride):
    product = db.get(Product, override.product_id)
    card_rate = None
    if product:
        card_rate = db.scalar(
            select(TileRate.rate_per_meter).where(
                TileRate.tile_size == product.tile_size,
                TileRate.grade == override.grade,
                TileRate.active.is_(True),
            )
        )
    return {
        "id": override.id,
        "product_id": override.product_id,
        "product_name": product.name if product else None,
        "tile_size": product.tile_size if product else None,
        "grade": override.grade,
        "rate_per_meter": override.rate_per_meter,
        "card_rate_per_meter": card_rate,
        "reason": override.reason,
        "active": override.active,
    }


def _impact(db: Session, tile_size: str, grade: str):
    product_ids = db.scalars(
        select(Product.id).where(
            Product.tile_size == tile_size,
            Product.active.is_(True),
        )
    ).all()
    product_count = len(product_ids)
    branch_count = db.scalar(select(func.count(Branch.id))) or 0
    return {"affected_products": product_count, "affected_branches": branch_count}
