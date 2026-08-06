from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from app.models.entities import (
    Accessory,
    AccessoryInventory,
    Inventory,
    Invoice,
    InvoiceItem,
    Product,
    SanitaryInventory,
    SanitaryProduct,
    SanitaryStockTransaction,
    StockTransaction,
    User,
    Branch,
)
from app.schemas.common import InvoiceCreate
from app.services.audit import write_audit_log
from app.services.accessory_labels import accessory_display_label
from stock_math import deduct_verbatim_stock_with_delta, total_pieces


def create_invoice(db: Session, payload: InvoiceCreate, user: User) -> Invoice:
    if not payload.items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invoice must have at least one item")

    branch = db.get(Branch, payload.branch_id)
    if not branch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")

    invoice = Invoice(
        branch_id=payload.branch_id,
        user_id=user.id,
        invoice_number=_next_invoice_number(db, payload.branch_id, branch.code),
        customer_name=payload.customer_name.strip(),
        customer_contact=payload.customer_contact.strip() if payload.customer_contact else None,
        discount=payload.discount,
        paid_amount=payload.paid_amount,
    )

    subtotal = 0.0
    for requested_item in payload.items:
        item = _build_invoice_item_and_update_stock(db, payload.branch_id, requested_item, user)
        invoice.items.append(item)
        subtotal += item.line_total

    if not invoice.items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invoice must have valid items")

    invoice.subtotal = subtotal
    invoice.grand_total = subtotal - payload.discount
    invoice.balance = invoice.grand_total - payload.paid_amount

    db.add(invoice)
    write_audit_log(
        db,
        user,
        "Invoice Created",
        {
            "invoice_number": invoice.invoice_number,
            "customer_name": invoice.customer_name,
            "grand_total": invoice.grand_total,
        },
        payload.branch_id,
    )
    db.flush()
    db.refresh(invoice)
    return db.scalar(
        select(Invoice)
        .where(Invoice.id == invoice.id)
        .options(selectinload(Invoice.items))
    )


def _next_invoice_number(db: Session, branch_id: int, branch_code: str) -> str:
    latest = db.scalar(
        select(Invoice.invoice_number)
        .where(Invoice.branch_id == branch_id)
        .order_by(Invoice.id.desc())
        .limit(1)
    )
    if latest and "-" in latest:
        try:
            next_num = int(latest.split("-")[-1]) + 1
        except ValueError:
            next_num = 1
    else:
        next_num = 1
    return f"{branch_code}-{next_num:04d}"


def _build_invoice_item_and_update_stock(db: Session, branch_id: int, requested_item, user: User) -> InvoiceItem:
    if requested_item.item_type == "tile":
        return _build_tile_item(db, branch_id, requested_item, user)
    if requested_item.item_type == "accessory":
        return _build_accessory_item(db, branch_id, requested_item, user)
    if requested_item.item_type == "sanitary":
        return _build_sanitary_item(db, branch_id, requested_item, user)
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid item type")


def _build_tile_item(db: Session, branch_id: int, requested_item, user: User) -> InvoiceItem:
    if not requested_item.product_id or not requested_item.grade:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tile product and grade are required")

    product = db.get(Product, requested_item.product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    inventory = db.scalar(
        select(Inventory)
        .where(
            Inventory.branch_id == branch_id,
            Inventory.product_id == requested_item.product_id,
            Inventory.grade == requested_item.grade,
        )
        .with_for_update()
    )
    if not inventory:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No stock found for tile")

    requested_pieces = total_pieces(requested_item.boxes, requested_item.loose_pieces, product.pieces_per_box)
    available_pieces = total_pieces(inventory.boxes, inventory.loose_pieces, product.pieces_per_box)
    if requested_pieces <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tile quantity is required")
    if requested_pieces > available_pieces:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient tile stock")

    try:
        inventory.boxes, inventory.loose_pieces, boxes_from_boxes, pieces_from_loose = deduct_verbatim_stock_with_delta(
            inventory.boxes,
            inventory.loose_pieces,
            requested_item.boxes,
            requested_item.loose_pieces,
            product.pieces_per_box,
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient tile stock")

    line_total = requested_item.boxes * inventory.rate_per_box + requested_item.loose_pieces * inventory.rate_per_piece

    db.add(StockTransaction(
        user_id=user.id,
        branch_id=branch_id,
        product_id=product.id,
        grade=requested_item.grade,
        transaction_type="OUT",
        boxes=requested_item.boxes,
        loose_pieces=requested_item.loose_pieces,
        notes="Invoice sale",
    ))

    return InvoiceItem(
        item_type="tile",
        product_id=product.id,
        description=f"{product.name} - {product.tile_size}",
        tile_size=product.tile_size,
        grade=requested_item.grade,
        boxes=requested_item.boxes,
        loose_pieces=requested_item.loose_pieces,
        quantity=requested_pieces,
        rate_per_sqm=inventory.rate_per_sqm,
        rate_per_box=inventory.rate_per_box,
        rate_per_piece=inventory.rate_per_piece,
        unit_price=0,
        line_total=line_total,
        boxes_from_boxes=boxes_from_boxes,
        pieces_from_loose=pieces_from_loose,
    )


def _build_accessory_item(db: Session, branch_id: int, requested_item, user: User) -> InvoiceItem:
    if not requested_item.accessory_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Accessory is required")

    accessory = db.get(Accessory, requested_item.accessory_id)
    if not accessory:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Accessory not found")

    inventory = db.scalar(
        select(AccessoryInventory)
        .where(
            AccessoryInventory.branch_id == branch_id,
            AccessoryInventory.accessory_id == accessory.id,
        )
        .with_for_update()
    )
    quantity = requested_item.quantity or requested_item.boxes
    if quantity <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Accessory quantity is required")
    if not inventory or inventory.quantity < quantity:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient accessory stock")

    inventory.quantity -= quantity
    db.add(StockTransaction(
        user_id=user.id,
        branch_id=branch_id,
        accessory_id=accessory.id,
        item_type="accessory",
        transaction_type="OUT",
        quantity=quantity,
        notes="Invoice sale",
    ))
    return InvoiceItem(
        item_type="accessory",
        accessory_id=accessory.id,
        description=accessory_display_label(accessory),
        tile_size=accessory.category,
        grade="-",
        boxes=quantity,
        quantity=quantity,
        rate_per_box=accessory.unit_price,
        unit_price=accessory.unit_price,
        line_total=quantity * accessory.unit_price,
        boxes_from_boxes=0,
        pieces_from_loose=quantity,
    )


def _build_sanitary_item(db: Session, branch_id: int, requested_item, user: User) -> InvoiceItem:
    if not requested_item.sanitary_product_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sanitary product is required")

    product = db.get(SanitaryProduct, requested_item.sanitary_product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sanitary product not found")

    inventory = db.scalar(
        select(SanitaryInventory)
        .where(
            SanitaryInventory.branch_id == branch_id,
            SanitaryInventory.sanitary_product_id == product.id,
        )
        .with_for_update()
    )
    quantity = requested_item.quantity or requested_item.boxes
    if quantity <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sanitary quantity is required")
    if not inventory or inventory.quantity < quantity:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient sanitary stock")

    inventory.quantity -= quantity
    db.add(SanitaryStockTransaction(
        user_id=user.id,
        branch_id=branch_id,
        sanitary_product_id=product.id,
        transaction_type="OUT",
        quantity=quantity,
        notes="Invoice sale",
    ))

    return InvoiceItem(
        item_type="sanitary",
        sanitary_product_id=product.id,
        description=f"{product.company_name} - {product.product_category}",
        tile_size=product.color,
        grade=product.sku,
        boxes=quantity,
        quantity=quantity,
        rate_per_box=product.sale_price,
        unit_price=product.sale_price,
        line_total=quantity * product.sale_price,
        boxes_from_boxes=0,
        pieces_from_loose=quantity,
    )


def void_invoice(db: Session, invoice_id: int, reason: str, user: User) -> Invoice:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can void invoices")

    clean_reason = reason.strip()
    if len(clean_reason) < 10:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Void reason must be at least 10 characters")

    invoice = db.scalar(
        select(Invoice)
        .where(Invoice.id == invoice_id)
        .options(selectinload(Invoice.items))
        .with_for_update()
    )
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    if invoice.status == "void":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invoice is already void")

    for item in invoice.items:
        if item.boxes_from_boxes is None or item.pieces_from_loose is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This invoice cannot be voided because it was created before fulfilment tracking existed",
            )
        if item.item_type == "tile":
            _restore_tile_item(db, invoice, item, user)
        elif item.item_type == "accessory":
            _restore_accessory_item(db, invoice, item, user)
        elif item.item_type == "sanitary":
            _restore_sanitary_item(db, invoice, item, user)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported invoice item type: {item.item_type}")

    invoice.status = "void"
    invoice.voided_at = datetime.now(timezone.utc)
    invoice.voided_by_user_id = user.id
    invoice.void_reason = clean_reason
    write_audit_log(
        db,
        user,
        "Invoice Voided",
        {
            "invoice_number": invoice.invoice_number,
            "reason": clean_reason,
            "grand_total": invoice.grand_total,
        },
        invoice.branch_id,
    )
    db.flush()
    db.refresh(invoice)
    return invoice


def _restore_tile_item(db: Session, invoice: Invoice, item: InvoiceItem, user: User) -> None:
    inventory = db.scalar(
        select(Inventory)
        .where(
            Inventory.branch_id == invoice.branch_id,
            Inventory.product_id == item.product_id,
            Inventory.grade == item.grade,
        )
        .with_for_update()
    )
    if not inventory:
        inventory = Inventory(
            branch_id=invoice.branch_id,
            product_id=item.product_id,
            grade=item.grade,
            boxes=0,
            loose_pieces=0,
            rate_per_sqm=item.rate_per_sqm,
            rate_per_box=item.rate_per_box,
            rate_per_piece=item.rate_per_piece,
        )
        db.add(inventory)
    inventory.boxes += item.boxes_from_boxes
    inventory.loose_pieces += item.pieces_from_loose
    if inventory.boxes < 0 or inventory.loose_pieces < 0:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot void invoice because tile stock changed incompatibly")
    db.add(StockTransaction(
        user_id=user.id,
        branch_id=invoice.branch_id,
        product_id=item.product_id,
        item_type="tile",
        grade=item.grade,
        transaction_type="IN",
        boxes=item.boxes_from_boxes,
        loose_pieces=item.pieces_from_loose,
        notes=f"Void invoice {invoice.invoice_number}",
    ))


def _restore_accessory_item(db: Session, invoice: Invoice, item: InvoiceItem, user: User) -> None:
    inventory = db.scalar(
        select(AccessoryInventory)
        .where(
            AccessoryInventory.branch_id == invoice.branch_id,
            AccessoryInventory.accessory_id == item.accessory_id,
        )
        .with_for_update()
    )
    if not inventory:
        inventory = AccessoryInventory(branch_id=invoice.branch_id, accessory_id=item.accessory_id, quantity=0)
        db.add(inventory)
    inventory.quantity += item.pieces_from_loose
    if inventory.quantity < 0:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot void invoice because accessory stock changed incompatibly")
    db.add(StockTransaction(
        user_id=user.id,
        branch_id=invoice.branch_id,
        accessory_id=item.accessory_id,
        item_type="accessory",
        transaction_type="IN",
        quantity=item.pieces_from_loose,
        notes=f"Void invoice {invoice.invoice_number}",
    ))


def _restore_sanitary_item(db: Session, invoice: Invoice, item: InvoiceItem, user: User) -> None:
    inventory = db.scalar(
        select(SanitaryInventory)
        .where(
            SanitaryInventory.branch_id == invoice.branch_id,
            SanitaryInventory.sanitary_product_id == item.sanitary_product_id,
        )
        .with_for_update()
    )
    if not inventory:
        inventory = SanitaryInventory(branch_id=invoice.branch_id, sanitary_product_id=item.sanitary_product_id, quantity=0)
        db.add(inventory)
    inventory.quantity += item.pieces_from_loose
    if inventory.quantity < 0:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot void invoice because sanitary stock changed incompatibly")
    db.add(StockTransaction(
        user_id=user.id,
        branch_id=invoice.branch_id,
        sanitary_product_id=item.sanitary_product_id,
        item_type="sanitary",
        transaction_type="IN",
        quantity=item.pieces_from_loose,
        notes=f"Void invoice {invoice.invoice_number}",
    ))
    db.add(SanitaryStockTransaction(
        user_id=user.id,
        branch_id=invoice.branch_id,
        sanitary_product_id=item.sanitary_product_id,
        transaction_type="IN",
        quantity=item.pieces_from_loose,
        notes=f"Void invoice {invoice.invoice_number}",
    ))
