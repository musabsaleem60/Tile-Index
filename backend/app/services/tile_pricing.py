from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Product, ProductRateOverride, TileRate, TileSize


@dataclass(frozen=True)
class TilePrice:
    rate_per_sqm: float
    rate_per_box: float
    rate_per_piece: float
    source: str


@dataclass(frozen=True)
class TilePriceContext:
    """Request-scoped pricing data for bulk catalogue operations."""

    overrides: dict[tuple[int, str], float]
    card_rates: dict[tuple[str, str], float]
    sizes: dict[str, TileSize]


def load_tile_price_context(db: Session) -> TilePriceContext:
    """Load the complete active rate card once for bulk price resolution."""
    overrides = db.scalars(
        select(ProductRateOverride).where(ProductRateOverride.active.is_(True))
    ).all()
    rates = db.scalars(select(TileRate).where(TileRate.active.is_(True))).all()
    sizes = db.scalars(select(TileSize).where(TileSize.active.is_(True))).all()
    return TilePriceContext(
        overrides={(row.product_id, row.grade): float(row.rate_per_meter) for row in overrides},
        card_rates={(row.tile_size, row.grade): float(row.rate_per_meter) for row in rates},
        sizes={row.tile_size: row for row in sizes},
    )


def resolve_tile_price_from_context(
    context: TilePriceContext,
    product: Product,
    grade: str,
) -> TilePrice | None:
    """Resolve override -> card without issuing database queries."""
    override_rate = context.overrides.get((product.id, grade))
    if override_rate is not None:
        return _price_from_meter_rate(product, override_rate, "override")

    card_rate = context.card_rates.get((product.tile_size, grade))
    if card_rate is not None:
        return _price_from_meter_rate(product, card_rate, "card")

    return None


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
