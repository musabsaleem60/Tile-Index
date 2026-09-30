from __future__ import annotations

from decimal import Decimal, InvalidOperation


DISPLAY_ZERO_EPSILON = Decimal("0.01")


def normalize_display_amount(value) -> Decimal:
    """Normalize sub-cent residue for display without changing stored data."""
    try:
        amount = Decimal(str(value or 0))
    except (InvalidOperation, TypeError, ValueError):
        amount = Decimal("0")
    if abs(amount) < DISPLAY_ZERO_EPSILON:
        return Decimal("0")
    return amount


def clamp_currency_zero(value) -> float:
    """Return exact zero for sub-cent residue used in money calculations."""
    return float(normalize_display_amount(value))


def format_amount(value) -> str:
    return f"{normalize_display_amount(value):.2f}"


def format_currency(value) -> str:
    return f"Rs. {format_amount(value)}"
