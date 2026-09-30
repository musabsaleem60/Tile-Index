from __future__ import annotations

from decimal import Decimal, InvalidOperation


DISPLAY_ZERO_EPSILON = Decimal("0.01")


def normalize_currency_amount(value) -> Decimal:
    try:
        amount = Decimal(str(value or 0))
    except (InvalidOperation, TypeError, ValueError):
        amount = Decimal("0")
    if abs(amount) < DISPLAY_ZERO_EPSILON:
        return Decimal("0")
    return amount


def clamp_currency_zero(value) -> float:
    return float(normalize_currency_amount(value))


def format_currency(value) -> str:
    return f"Rs. {normalize_currency_amount(value):.2f}"
