from datetime import datetime
from zoneinfo import ZoneInfo


BUSINESS_TZ = ZoneInfo("Asia/Karachi")


def parse_datetime(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        clean = value.strip()
        if not clean:
            return None
        try:
            return datetime.fromisoformat(clean.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def to_business_datetime(value):
    parsed = parse_datetime(value)
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        return parsed
    return parsed.astimezone(BUSINESS_TZ)


def format_business_datetime(value, fallback=None, fmt="%Y-%m-%d %H:%M:%S"):
    converted = to_business_datetime(value)
    if converted is None:
        return fallback if fallback is not None else str(value)
    return converted.strftime(fmt)


def business_date(value):
    converted = to_business_datetime(value)
    if converted is None:
        return None
    return converted.strftime("%Y-%m-%d")
