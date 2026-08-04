"""Tile stock arithmetic that preserves stored box/loose counts."""


def deduct_verbatim_stock(current_boxes, current_loose_pieces, requested_boxes, requested_loose_pieces, pieces_per_box):
    """Deduct requested stock without normalizing surplus loose pieces into boxes.

    Box requests are deducted from boxes first, then from loose pieces as an
    equivalent piece count when boxes are short. Loose-piece requests borrow
    from boxes only when loose pieces run short.
    """
    if min(current_boxes, current_loose_pieces, requested_boxes, requested_loose_pieces) < 0:
        raise ValueError("Stock quantities cannot be negative")
    if pieces_per_box <= 0:
        raise ValueError("Pieces per box must be greater than zero")

    available = current_boxes * pieces_per_box + current_loose_pieces
    requested = requested_boxes * pieces_per_box + requested_loose_pieces
    if requested > available:
        raise ValueError("Insufficient stock")

    boxes = current_boxes
    loose_pieces = current_loose_pieces

    boxes_from_stock = min(boxes, requested_boxes)
    boxes -= boxes_from_stock
    remaining_box_pieces = (requested_boxes - boxes_from_stock) * pieces_per_box
    loose_pieces -= remaining_box_pieces

    loose_pieces -= requested_loose_pieces
    while loose_pieces < 0 and boxes > 0:
        boxes -= 1
        loose_pieces += pieces_per_box

    if boxes < 0 or loose_pieces < 0:
        raise ValueError("Insufficient stock")

    return boxes, loose_pieces


def total_pieces(boxes, loose_pieces, pieces_per_box):
    """Return total pieces represented by stored box and loose counts."""
    return boxes * pieces_per_box + loose_pieces
