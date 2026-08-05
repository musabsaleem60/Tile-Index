def accessory_display_label(accessory) -> str:
    """Build the user-facing accessory label from structured fields."""
    category = getattr(accessory, "category", None)
    company = getattr(accessory, "company", None)
    product_name = getattr(accessory, "product_name", None)
    colour = getattr(accessory, "colour", None)
    size = getattr(accessory, "size", None)

    if category == "Grout":
        parts = [company, colour]
    elif category == "Bond":
        parts = [company]
    elif category == "Spacer":
        parts = [product_name or getattr(accessory, "name", None), size]
    elif category == "Floor Waste":
        parts = [company, product_name or getattr(accessory, "product_type", None), colour]
    else:
        parts = [company, product_name, colour, size]

    return " — ".join(str(part) for part in parts if part) or getattr(accessory, "name", None) or "Accessory"
