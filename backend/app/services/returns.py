from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.entities import (
    AccessoryInventory,
    Branch,
    Inventory,
    Invoice,
    InvoiceItem,
    InvoiceReturn,
    InvoiceReturnItem,
    Product,
    ReturnExchangeItem,
    ReturnSettlement,
    SanitaryInventory,
    SanitaryStockTransaction,
    StockTransaction,
    User,
)
from app.services.audit import write_audit_log
from app.services.invoices import _build_invoice_item_and_update_stock


MONEY = Decimal("0.01")


def _money(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(MONEY, rounding=ROUND_HALF_UP)


def _load_return(db: Session, return_id: int) -> InvoiceReturn | None:
    return db.scalar(
        select(InvoiceReturn)
        .where(InvoiceReturn.id == return_id)
        .options(
            selectinload(InvoiceReturn.return_items),
            selectinload(InvoiceReturn.exchange_items),
            selectinload(InvoiceReturn.settlements),
        )
    )


def serialize_return(record: InvoiceReturn) -> dict:
    settled = _money(sum(Decimal(str(row.amount)) for row in record.settlements))
    difference = _money(record.difference_amount)
    return {
        "id": record.id,
        "return_number": record.return_number,
        "invoice_id": record.invoice_id,
        "branch_id": record.branch_id,
        "user_id": record.user_id,
        "return_date": record.return_date,
        "reason": record.reason,
        "returned_value": float(record.returned_value),
        "exchange_value": float(record.exchange_value),
        "difference_amount": float(record.difference_amount),
        "status": record.status,
        "created_at": record.created_at,
        "return_items": record.return_items,
        "exchange_items": record.exchange_items,
        "settlements": record.settlements,
        "settled_amount": float(settled),
        "outstanding_amount": float(max(Decimal("0"), abs(difference) - settled)),
        "difference_direction": "refund_to_customer" if difference > 0 else "payment_from_customer" if difference < 0 else "even",
    }


def create_return(db: Session, invoice_id: int, payload, user: User) -> dict:
    clean_reason = payload.reason.strip()
    if len(clean_reason) < 5:
        raise HTTPException(status_code=400, detail="Return reason must be at least 5 characters")
    if not payload.return_items:
        raise HTTPException(status_code=400, detail="Select at least one item to return")

    invoice = db.scalar(
        select(Invoice)
        .where(Invoice.id == invoice_id)
        .options(selectinload(Invoice.items))
        .with_for_update()
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if invoice.status == "void":
        raise HTTPException(status_code=409, detail="A void invoice cannot be returned")

    item_map = {item.id: item for item in invoice.items}
    requested_ids = [row.invoice_item_id for row in payload.return_items]
    if len(requested_ids) != len(set(requested_ids)):
        raise HTTPException(status_code=400, detail="Each invoice item may appear only once in a return")
    locked_items = db.scalars(select(InvoiceItem).where(InvoiceItem.id.in_(requested_ids)).with_for_update()).all()
    if len(locked_items) != len(requested_ids) or any(item.invoice_id != invoice.id for item in locked_items):
        raise HTTPException(status_code=400, detail="A return item does not belong to this invoice")

    record = InvoiceReturn(
        invoice_id=invoice.id,
        branch_id=invoice.branch_id,
        user_id=user.id,
        return_date=payload.return_date,
        reason=clean_reason,
        returned_value=0,
        exchange_value=0,
        difference_amount=0,
        status="completed",
    )
    db.add(record)
    db.flush()
    record.return_number = f"RET-{record.id:06d}"

    discount_factor = Decimal("1")
    if Decimal(str(invoice.subtotal or 0)) > 0:
        discount_factor = Decimal(str(invoice.grand_total)) / Decimal(str(invoice.subtotal))

    returned_total = Decimal("0")
    activity_returns = []
    for request in payload.return_items:
        original = item_map[request.invoice_item_id]
        if original.boxes_from_boxes is None or original.pieces_from_loose is None:
            raise HTTPException(
                status_code=409,
                detail="This invoice cannot be returned because it was created before fulfilment tracking existed",
            )
        line, value = _restore_return_item(db, record, original, request, user, discount_factor)
        record.return_items.append(line)
        returned_total += value
        activity_returns.append({
            "invoice_item_id": original.id,
            "description": original.description,
            "source_branch_id": original.source_branch_id,
            "boxes": request.boxes,
            "loose_pieces": request.loose_pieces,
            "quantity": request.quantity,
            "value": float(value),
        })

    exchange_total = Decimal("0")
    activity_exchanges = []
    fake_invoice = Invoice(
        branch_id=invoice.branch_id,
        invoice_number=f"exchange {record.return_number}",
        customer_name=invoice.customer_name,
    )
    for request in payload.exchange_items:
        prior_new = set(db.new)
        built = _build_invoice_item_and_update_stock(db, fake_invoice, request, user)
        exchange_note = f"Exchange {record.return_number} against invoice {invoice.invoice_number}"
        for pending in set(db.new) - prior_new:
            if isinstance(pending, (StockTransaction, SanitaryStockTransaction)):
                pending.notes = exchange_note
        line = ReturnExchangeItem(
            return_id=record.id,
            product_id=built.product_id,
            accessory_id=built.accessory_id,
            sanitary_product_id=built.sanitary_product_id,
            source_branch_id=built.source_branch_id,
            item_type=built.item_type,
            description=built.description,
            tile_size=built.tile_size,
            grade=built.grade,
            boxes=built.boxes,
            loose_pieces=built.loose_pieces,
            quantity=built.quantity,
            rate_per_sqm=built.rate_per_sqm,
            rate_per_box=built.rate_per_box,
            rate_per_piece=built.rate_per_piece,
            unit_price=built.unit_price,
            line_total=built.line_total,
            boxes_from_boxes=built.boxes_from_boxes,
            pieces_from_loose=built.pieces_from_loose,
        )
        record.exchange_items.append(line)
        exchange_total += _money(built.line_total)
        activity_exchanges.append({
            "description": built.description,
            "source_branch_id": built.source_branch_id,
            "boxes": built.boxes,
            "loose_pieces": built.loose_pieces,
            "quantity": built.quantity,
            "value": float(built.line_total),
        })

    record.returned_value = returned_total.quantize(MONEY, rounding=ROUND_HALF_UP)
    record.exchange_value = exchange_total.quantize(MONEY, rounding=ROUND_HALF_UP)
    record.difference_amount = _money(record.returned_value - record.exchange_value)

    if payload.settlement:
        _add_settlement(db, record, payload.settlement, user)

    write_audit_log(
        db,
        user,
        "Invoice Return Processed",
        {
            "return_number": record.return_number,
            "invoice_number": invoice.invoice_number,
            "returned_items": activity_returns,
            "exchange_items": activity_exchanges,
            "returned_value": float(record.returned_value),
            "exchange_value": float(record.exchange_value),
            "difference_amount": float(record.difference_amount),
            "settlement": payload.settlement.model_dump(mode="json") if payload.settlement else None,
            "reason": clean_reason,
        },
        invoice.branch_id,
    )
    db.flush()
    return serialize_return(_load_return(db, record.id))


def _restore_return_item(db, record, original, request, user, discount_factor):
    original_invoice = db.get(Invoice, original.invoice_id)
    stock_note = f"Return {record.return_number} against invoice {original_invoice.invoice_number}"
    prior_quantity = db.scalar(
        select(func.coalesce(func.sum(InvoiceReturnItem.quantity), 0))
        .join(InvoiceReturn, InvoiceReturn.id == InvoiceReturnItem.return_id)
        .where(InvoiceReturnItem.invoice_item_id == original.id, InvoiceReturn.status == "completed")
    ) or 0

    if original.item_type == "tile":
        product = db.get(Product, original.product_id)
        pieces_per_box = product.pieces_per_box
        requested_quantity = request.boxes * pieces_per_box + request.loose_pieces
    else:
        requested_quantity = request.quantity
    if requested_quantity <= 0:
        raise HTTPException(status_code=400, detail=f"Return quantity is required for {original.description}")
    if prior_quantity + requested_quantity > original.quantity:
        raise HTTPException(status_code=409, detail=f"Return quantity exceeds remaining quantity for {original.description}")

    prior_boxes = db.scalar(
        select(func.coalesce(func.sum(InvoiceReturnItem.boxes_restored_to_boxes), 0))
        .join(InvoiceReturn, InvoiceReturn.id == InvoiceReturnItem.return_id)
        .where(InvoiceReturnItem.invoice_item_id == original.id, InvoiceReturn.status == "completed")
    ) or 0
    prior_loose = db.scalar(
        select(func.coalesce(func.sum(InvoiceReturnItem.pieces_restored_to_loose), 0))
        .join(InvoiceReturn, InvoiceReturn.id == InvoiceReturnItem.return_id)
        .where(InvoiceReturnItem.invoice_item_id == original.id, InvoiceReturn.status == "completed")
    ) or 0

    if original.item_type == "tile":
        cumulative = prior_quantity + requested_quantity
        if cumulative == original.quantity:
            target_boxes = original.boxes_from_boxes
            target_loose = original.pieces_from_loose
        else:
            target_boxes = int(Decimal(original.boxes_from_boxes) * Decimal(cumulative) / Decimal(original.quantity))
            target_loose = cumulative - target_boxes * pieces_per_box
        restore_boxes = target_boxes - prior_boxes
        restore_loose = target_loose - prior_loose
        inventory = db.scalar(select(Inventory).where(
            Inventory.branch_id == original.source_branch_id,
            Inventory.product_id == original.product_id,
            Inventory.grade == original.grade,
        ).with_for_update())
        if not inventory:
            inventory = Inventory(branch_id=original.source_branch_id, product_id=original.product_id, grade=original.grade, boxes=0, loose_pieces=0)
            db.add(inventory)
        inventory.boxes += restore_boxes
        inventory.loose_pieces += restore_loose
        if inventory.boxes < 0 or inventory.loose_pieces < 0:
            raise HTTPException(status_code=409, detail="Return cannot restore tile stock because its stored buckets changed incompatibly")
        db.add(StockTransaction(
            user_id=user.id, branch_id=original.source_branch_id, product_id=original.product_id,
            item_type="tile", grade=original.grade, transaction_type="IN",
            boxes=restore_boxes, loose_pieces=restore_loose,
            notes=stock_note,
        ))
        gross = Decimal(str(original.line_total)) * Decimal(requested_quantity) / Decimal(original.quantity)
    elif original.item_type == "accessory":
        restore_boxes, restore_loose = 0, requested_quantity
        inventory = db.scalar(select(AccessoryInventory).where(
            AccessoryInventory.branch_id == original.source_branch_id,
            AccessoryInventory.accessory_id == original.accessory_id,
        ).with_for_update())
        if not inventory:
            inventory = AccessoryInventory(branch_id=original.source_branch_id, accessory_id=original.accessory_id, quantity=0)
            db.add(inventory)
        inventory.quantity += requested_quantity
        db.add(StockTransaction(
            user_id=user.id, branch_id=original.source_branch_id, accessory_id=original.accessory_id,
            item_type="accessory", transaction_type="IN", quantity=requested_quantity,
            notes=stock_note,
        ))
        gross = Decimal(str(original.line_total)) * Decimal(requested_quantity) / Decimal(original.quantity)
    else:
        restore_boxes, restore_loose = 0, requested_quantity
        inventory = db.scalar(select(SanitaryInventory).where(
            SanitaryInventory.branch_id == original.source_branch_id,
            SanitaryInventory.sanitary_product_id == original.sanitary_product_id,
        ).with_for_update())
        if not inventory:
            inventory = SanitaryInventory(branch_id=original.source_branch_id, sanitary_product_id=original.sanitary_product_id, quantity=0)
            db.add(inventory)
        inventory.quantity += requested_quantity
        note = stock_note
        db.add(StockTransaction(
            user_id=user.id, branch_id=original.source_branch_id, sanitary_product_id=original.sanitary_product_id,
            item_type="sanitary", transaction_type="IN", quantity=requested_quantity, notes=note,
        ))
        db.add(SanitaryStockTransaction(
            user_id=user.id, branch_id=original.source_branch_id, sanitary_product_id=original.sanitary_product_id,
            transaction_type="IN", quantity=requested_quantity, notes=note,
        ))
        gross = Decimal(str(original.line_total)) * Decimal(requested_quantity) / Decimal(original.quantity)

    discounted = (gross * discount_factor).quantize(MONEY, rounding=ROUND_HALF_UP)
    return InvoiceReturnItem(
        return_id=record.id,
        invoice_item_id=original.id,
        source_branch_id=original.source_branch_id,
        item_type=original.item_type,
        boxes=request.boxes if original.item_type == "tile" else 0,
        loose_pieces=request.loose_pieces if original.item_type == "tile" else 0,
        quantity=requested_quantity,
        rate_per_sqm=original.rate_per_sqm,
        rate_per_box=original.rate_per_box,
        rate_per_piece=original.rate_per_piece,
        unit_price=original.unit_price,
        discounted_line_total=discounted,
        boxes_restored_to_boxes=restore_boxes,
        pieces_restored_to_loose=restore_loose,
    ), discounted


def _add_settlement(db: Session, record: InvoiceReturn, payload, user: User) -> ReturnSettlement:
    difference = _money(record.difference_amount)
    expected = "refund_to_customer" if difference > 0 else "payment_from_customer" if difference < 0 else None
    if not expected:
        raise HTTPException(status_code=400, detail="An even exchange does not require a settlement")
    if payload.direction != expected:
        raise HTTPException(status_code=400, detail=f"Settlement direction must be {expected}")
    settled = _money(db.scalar(select(func.coalesce(func.sum(ReturnSettlement.amount), 0)).where(ReturnSettlement.return_id == record.id)) or 0)
    amount = _money(payload.amount)
    if settled + amount > abs(difference):
        raise HTTPException(status_code=400, detail="Settlement amount exceeds the outstanding return difference")
    row = ReturnSettlement(
        return_id=record.id, user_id=user.id, branch_id=record.branch_id,
        direction=payload.direction, amount=amount, method=payload.method,
        settlement_date=payload.settlement_date, notes=payload.notes,
    )
    db.add(row)
    return row


def add_settlement(db: Session, return_id: int, payload, user: User) -> dict:
    record = db.scalar(select(InvoiceReturn).where(InvoiceReturn.id == return_id).with_for_update())
    if not record:
        raise HTTPException(status_code=404, detail="Return not found")
    _add_settlement(db, record, payload, user)
    write_audit_log(
        db,
        user,
        "Return Settlement Recorded",
        {
            "return_number": record.return_number,
            "direction": payload.direction,
            "amount": payload.amount,
            "method": payload.method,
            "settlement_date": payload.settlement_date.isoformat(),
        },
        record.branch_id,
    )
    db.flush()
    return serialize_return(_load_return(db, return_id))


def get_return(db: Session, return_id: int) -> dict | None:
    record = _load_return(db, return_id)
    return serialize_return(record) if record else None


def invoice_return_history(db: Session, invoice: Invoice) -> dict:
    records = db.scalars(
        select(InvoiceReturn).where(InvoiceReturn.invoice_id == invoice.id).order_by(InvoiceReturn.return_date.desc())
    ).all()
    serialized = [serialize_return(_load_return(db, row.id)) for row in records]
    remaining = {}
    for item in invoice.items:
        returned = db.scalar(
            select(func.coalesce(func.sum(InvoiceReturnItem.quantity), 0))
            .join(InvoiceReturn, InvoiceReturn.id == InvoiceReturnItem.return_id)
            .where(InvoiceReturnItem.invoice_item_id == item.id, InvoiceReturn.status == "completed")
        ) or 0
        remaining[item.id] = {
            "description": item.description,
            "item_type": item.item_type,
            "sold_quantity": item.quantity,
            "returned_quantity": returned,
            "remaining_quantity": item.quantity - returned,
        }
    return {"returns": serialized, "remaining_by_item": remaining}
