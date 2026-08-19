from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Product, ProductRateOverride, TileRate


@dataclass(frozen=True)
class TilePrice:
    rate_per_sqm: float
    rate_per_box: float
    rate_per_piece: float
    source: str


def resolve_tile_price(db: Session, product: Product, grade: str) -> TilePrice | None:
    override = db.scalar(
        select(ProductRateOverride).where(
            ProductRateOverride.product_id == product.id,
            ProductRateOverride.grade == grade,
            ProductRateOverride.active.is_(True),
        )
    )
    if override:
        return _price_from_meter_rate(product, override.rate_per_meter, "override")

    card_rate = db.scalar(
        select(TileRate).where(
            TileRate.tile_size == product.tile_size,
            TileRate.grade == grade,
            TileRate.active.is_(True),
        )
    )
    if card_rate:
        return _price_from_meter_rate(product, card_rate.rate_per_meter, "card")

    return None


def _price_from_meter_rate(product: Product, rate_per_meter: float, source: str) -> TilePrice:
    rate_per_box = float(rate_per_meter) * float(product.area_per_box)
    rate_per_piece = rate_per_box / int(product.pieces_per_box)
    return TilePrice(
        rate_per_sqm=float(rate_per_meter),
        rate_per_box=rate_per_box,
        rate_per_piece=rate_per_piece,
        source=source,
    )
