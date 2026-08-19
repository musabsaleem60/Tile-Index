import json


def format_activity_details(activity) -> str:
    action = getattr(activity, "action_type", "") or ""
    data = _parse_details(getattr(activity, "action_details", None))
    if data is None:
        return getattr(activity, "action_details", None) or ""

    if action in {"Stock IN", "Stock OUT"}:
        return _format_tile_stock(data, include_reason=action == "Stock OUT")
    if action in {"Accessory Stock IN", "Accessory Stock OUT"}:
        return _format_accessory_stock(data, include_reason=action == "Accessory Stock OUT")
    if action == "Invoice Created":
        return _join_sentences([
            f"Invoice {data.get('invoice_number')}" if data.get("invoice_number") else None,
            f"Customer: {data.get('customer_name')}" if data.get("customer_name") else None,
            _money("Total", data.get("grand_total")),
        ])
    if action == "Invoice Voided":
        return _join_sentences([
            f"Voided invoice {data.get('invoice_number')}" if data.get("invoice_number") else None,
            _money("Total", data.get("grand_total")),
            f"Reason: {data.get('reason')}" if data.get("reason") else None,
        ])
    if action == "Cross-Branch Sale":
        return _join_sentences([
            data.get("description"),
            f"Sold by {data.get('selling_branch')}" if data.get("selling_branch") else None,
            f"Source: {data.get('source_branch')}" if data.get("source_branch") else None,
            _quantity(data),
        ])
    if action in {"Product Added", "Product Edited"}:
        name = data.get("name") or data.get("product_name")
        size = data.get("tile_size")
        return _join_sentences([
            f"{name} - {size}" if name and size else name or size,
            f"Area/box: {data.get('area_per_box')} m2" if data.get("area_per_box") is not None else None,
            f"Pieces/box: {data.get('pieces_per_box')}" if data.get("pieces_per_box") is not None else None,
        ])
    if action == "Product Deleted":
        return _join_sentences([
            f"Deleted {data.get('name')}" if data.get("name") else None,
            f"Product ID: {data.get('product_id')}" if data.get("product_id") else None,
        ])
    if action in {"Accessory Added", "Accessory Edited"}:
        return _join_sentences([
            _accessory_label(data),
            f"Category: {data.get('category')}" if data.get("category") else None,
            _money("Price", data.get("unit_price")),
        ])
    if action == "Accessory Deleted":
        return _join_sentences([
            f"Deleted {data.get('name')}" if data.get("name") else None,
            f"Accessory ID: {data.get('accessory_id')}" if data.get("accessory_id") else None,
        ])
    if action in {"User Created", "User Edited", "Password Changed"}:
        return _join_sentences([
            f"User: {data.get('username')}" if data.get("username") else None,
            f"Role: {data.get('role')}" if data.get("role") else None,
            f"Target user ID: {data.get('user_id')}" if data.get("user_id") else None,
        ])
    if action == "Rate Card Updated":
        return _join_sentences([
            f"{data.get('tile_size')} | {data.get('grade')}",
            _rate_change(data),
            _impact(data),
            f"Reason: {data.get('reason')}" if data.get("reason") else None,
        ])
    if action == "Tile Size Added":
        rates = data.get("rates") or {}
        return _join_sentences([
            f"Added size {data.get('tile_size')}",
            f"{data.get('pieces_per_box')} pieces/box | {data.get('area_per_box')} m2/box",
            "Rates: " + ", ".join(f"{grade} Rs. {rate}" for grade, rate in rates.items()) if rates else None,
            f"Reason: {data.get('reason')}" if data.get("reason") else None,
        ])
    if action in {"Product Rate Override Added", "Product Rate Override Updated"}:
        return _join_sentences([
            f"{data.get('product_name')} - {data.get('tile_size')} | {data.get('grade')}",
            _rate_change(data),
            f"Reason: {data.get('reason')}" if data.get("reason") else None,
        ])
    if action == "Product Rate Override Removed":
        return _join_sentences([
            f"Removed override for {data.get('product_name')} - {data.get('tile_size')} | {data.get('grade')}",
            _money("Old override", data.get("old_rate"), "/m2"),
            f"Reason: {data.get('reason')}" if data.get("reason") else None,
        ])

    return _generic(data)


def activity_reason(activity) -> str:
    data = _parse_details(getattr(activity, "action_details", None))
    if not data:
        return ""
    return str(data.get("reason") or data.get("notes") or "").strip()


def _parse_details(raw):
    if not raw:
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


def _format_tile_stock(data, include_reason):
    product = data.get("product_name") or _product_name(data.get("product_id"))
    size = data.get("tile_size") or _product_size(data.get("product_id"))
    head = f"{product} - {size}" if product and size else product or "Tile"
    parts = [head]
    if data.get("grade"):
        parts.append(str(data.get("grade")))
    parts.append(_quantity(data))
    lines = [" | ".join(part for part in parts if part)]
    reason = data.get("reason") or data.get("notes")
    if include_reason and reason:
        lines.append(f"Reason: {reason}")
    return "\n".join(lines)


def _format_accessory_stock(data, include_reason):
    label = data.get("accessory_name") or _accessory_name(data.get("accessory_id")) or "Accessory"
    quantity = data.get("quantity")
    lines = [f"{label} | {quantity} units" if quantity is not None else label]
    reason = data.get("reason") or data.get("notes")
    if include_reason and reason:
        lines.append(f"Reason: {reason}")
    return "\n".join(lines)


def _quantity(data):
    boxes = int(data.get("boxes") or 0)
    loose = int(data.get("loose_pieces") or 0)
    quantity = data.get("quantity")
    if boxes or loose:
        return f"{boxes} boxes + {loose} loose"
    if quantity is not None:
        return f"{quantity} units"
    return ""


def _product_name(product_id):
    product = _product(product_id)
    return getattr(product, "name", None) if product else None


def _product_size(product_id):
    product = _product(product_id)
    return getattr(product, "tile_size", None) if product else None


def _product(product_id):
    if not product_id:
        return None
    try:
        from repositories.product_repository import ProductRepository
        return ProductRepository.get_by_id(int(product_id))
    except Exception:
        return None


def _accessory_name(accessory_id):
    if not accessory_id:
        return None
    try:
        from repositories.accessory_repository import AccessoryRepository
        from utils.accessory_labels import accessory_display_label
        accessory = AccessoryRepository.get_by_id(int(accessory_id))
        return accessory_display_label(accessory) if accessory else None
    except Exception:
        return None


def _accessory_label(data):
    return " - ".join(str(part) for part in [
        data.get("company"),
        data.get("product_name"),
        data.get("colour"),
        data.get("size"),
    ] if part) or data.get("name")


def _money(label, value, suffix=""):
    if value is None:
        return None
    try:
        return f"{label}: Rs. {float(value):.2f}{suffix}"
    except Exception:
        return f"{label}: {value}{suffix}"


def _rate_change(data):
    old_rate = data.get("old_rate")
    new_rate = data.get("new_rate")
    if old_rate is None:
        return _money("New rate", new_rate, "/m2")
    return f"Rate: Rs. {float(old_rate):.2f}/m2 -> Rs. {float(new_rate):.2f}/m2"


def _impact(data):
    products = data.get("affected_products")
    branches = data.get("affected_branches")
    if products is None or branches is None:
        return None
    return f"Affects {products} products across {branches} branches"


def _join_sentences(parts):
    return "\n".join(str(part) for part in parts if part) or ""


def _generic(data):
    skipped = {"rate_per_sqm", "rate_per_box", "rate_per_piece", "rate_fields_ignored"}
    return "\n".join(
        f"{key.replace('_', ' ').title()}: {value}"
        for key, value in data.items()
        if key not in skipped and value not in (None, "")
    )
