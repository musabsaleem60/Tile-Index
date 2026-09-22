import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
if str(ROOT / "Tile Index") not in sys.path:
    sys.path.insert(0, str(ROOT / "Tile Index"))

from app.models.base import Base
from app.models.entities import (
    Accessory,
    AccessoryInventory,
    Branch,
    Inventory,
    Invoice,
    InvoiceItem,
    InvoicePayment,
    InvoiceReturn,
    Product,
    StockTransaction,
    TileRate,
    TileSize,
    User,
)
from app.schemas.common import InvoiceReturnCreate, InvoiceReturnOut, ReturnItemIn, ReturnSettlementIn
from app.services.invoices import void_invoice
from app.services.returns import add_settlement, create_return


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture()
def seeded(db):
    branch = Branch(name="Tile Index - Korangi", code="TIK")
    other = Branch(name="Tile Cera - Korangi", code="TCK")
    user = User(username="employee", password_hash="x", role="employee", branch_id=None, is_active=True)
    size = TileSize(tile_size="10x20", pieces_per_box=12, area_per_box=1.53)
    product = Product(name="Return Test Tile", normalized_product_name="return test tile", item_code="TIL-TEST", tile_size="10x20", pieces_per_box=12, area_per_box=1.53)
    accessory = Accessory(name="Test Grout", category="Grout", company="Test", product_name="Grout", colour="White", normalized_identity="grout test white", unit_price=500)
    db.add_all([branch, other, user, size, product, accessory])
    db.flush()
    db.add(TileRate(tile_size="10x20", grade="G1 Prime", rate_per_meter=1000))
    # The original two-box sale was fulfilled entirely from 24 loose pieces.
    tile_stock = Inventory(branch_id=other.id, product_id=product.id, grade="G1 Prime", boxes=0, loose_pieces=1)
    accessory_stock = AccessoryInventory(branch_id=branch.id, accessory_id=accessory.id, quantity=10)
    invoice = Invoice(
        branch_id=branch.id, user_id=user.id, invoice_number="TIK-0001", customer_name="Return Customer",
        subtotal=2336, discount=336, grand_total=2000, paid_amount=2000, balance=0, status="active",
    )
    line = InvoiceItem(
        invoice=invoice, item_type="tile", product_id=product.id, source_branch_id=other.id,
        description="Return Test Tile - 10x20", tile_size="10x20", grade="G1 Prime",
        boxes=2, loose_pieces=0, quantity=24, rate_per_sqm=1000, rate_per_box=1530,
        rate_per_piece=127.5, unit_price=0, line_total=2336,
        boxes_from_boxes=0, pieces_from_loose=24,
    )
    db.add_all([tile_stock, accessory_stock, invoice, line])
    db.commit()
    return branch, other, user, product, accessory, invoice, line


def payload(line_id, boxes=0, loose=0, quantity=0, exchange_items=None, settlement=None):
    return InvoiceReturnCreate(
        return_date=datetime.now(timezone.utc),
        reason="customer return",
        return_items=[ReturnItemIn(invoice_item_id=line_id, boxes=boxes, loose_pieces=loose, quantity=quantity)],
        exchange_items=exchange_items or [],
        settlement=settlement,
    )


def test_two_partial_returns_restore_exact_original_buckets_and_discount(db, seeded):
    _, other, user, product, _, invoice, line = seeded
    first = create_return(db, invoice.id, payload(line.id, boxes=1), user)
    assert InvoiceReturnOut.model_validate(first).return_number.startswith("RET-")
    db.commit()
    stock = db.scalar(select(Inventory).where(Inventory.product_id == product.id, Inventory.branch_id == other.id))
    assert (stock.boxes, stock.loose_pieces) == (0, 13)
    assert first["return_items"][0].boxes_restored_to_boxes == 0
    assert first["return_items"][0].pieces_restored_to_loose == 12
    assert first["returned_value"] == 1000.00

    second = create_return(db, invoice.id, payload(line.id, boxes=1), user)
    db.commit()
    db.refresh(stock)
    assert (stock.boxes, stock.loose_pieces) == (0, 25)
    assert second["return_items"][0].boxes_restored_to_boxes == 0
    assert second["return_items"][0].pieces_restored_to_loose == 12

    with pytest.raises(HTTPException, match="exceeds remaining"):
        create_return(db, invoice.id, payload(line.id, loose=1), user)


def test_return_exchange_and_later_settlement(db, seeded):
    branch, _, user, _, accessory, invoice, line = seeded
    exchange = [{
        "item_type": "accessory", "accessory_id": accessory.id, "source_branch_id": branch.id,
        "boxes": 1, "loose_pieces": 0, "quantity": 1,
    }]
    result = create_return(db, invoice.id, payload(line.id, boxes=1, exchange_items=exchange), user)
    db.commit()
    assert result["returned_value"] == 1000
    assert result["exchange_value"] == 500
    assert result["difference_amount"] == 500
    stock = db.scalar(select(AccessoryInventory).where(AccessoryInventory.accessory_id == accessory.id))
    assert stock.quantity == 9

    settlement = ReturnSettlementIn(
        amount=500, direction="refund_to_customer", settlement_date=datetime.now(timezone.utc), method="cash"
    )
    settled = add_settlement(db, result["id"], settlement, user)
    db.commit()
    assert settled["settled_amount"] == 500
    assert settled["outstanding_amount"] == 0


def test_full_return_with_initial_refund_settlement(db, seeded):
    _, other, user, product, _, invoice, line = seeded
    settlement = ReturnSettlementIn(
        amount=2000, direction="refund_to_customer", settlement_date=datetime.now(timezone.utc), method="cash"
    )
    result = create_return(db, invoice.id, payload(line.id, boxes=2, settlement=settlement), user)
    db.commit()
    stock = db.scalar(select(Inventory).where(Inventory.product_id == product.id, Inventory.branch_id == other.id))
    assert (stock.boxes, stock.loose_pieces) == (0, 25)
    assert result["returned_value"] == 2000
    assert result["settled_amount"] == 2000
    assert result["outstanding_amount"] == 0
    transaction = db.scalar(select(StockTransaction).where(StockTransaction.transaction_type == "IN"))
    assert (transaction.boxes, transaction.loose_pieces) == (0, 24)


def test_void_guards_for_completed_return_and_payment(db, seeded):
    _, _, user, _, _, invoice, line = seeded
    create_return(db, invoice.id, payload(line.id, boxes=1), user)
    db.commit()
    with pytest.raises(HTTPException, match="completed return"):
        void_invoice(db, invoice.id, "return already processed", user)

    second = Invoice(branch_id=invoice.branch_id, user_id=user.id, invoice_number="TIK-0002", customer_name="Paid", subtotal=1, grand_total=1, paid_amount=1, balance=0, status="active")
    db.add(second)
    db.flush()
    db.add(InvoicePayment(invoice_id=second.id, branch_id=invoice.branch_id, user_id=user.id, amount=1, payment_date=datetime.now(timezone.utc)))
    db.commit()
    with pytest.raises(HTTPException, match="recorded payments"):
        void_invoice(db, second.id, "payment already recorded", user)


def test_employee_branch_access_is_enforced_by_api_dependency(seeded):
    branch, other, user, *_ = seeded
    from app.api.deps import ensure_branch_access
    user.branch_id = branch.id
    ensure_branch_access(user, branch.id)
    with pytest.raises(HTTPException, match="Branch access denied"):
        ensure_branch_access(user, other.id)


def test_exchange_dialog_maps_overview_collections_and_stocked_branches():
    from ui.invoice_return_dialog import InvoiceReturnDialog

    tile = {
        "product": "Example Tile",
        "branches": [
            {"branch_id": 1, "branch_name": "Empty", "total_pieces": 0},
            {"branch_id": 2, "branch_name": "Stocked", "total_pieces": 24},
        ],
    }
    payload = {"tiles": [tile], "accessories": [], "sanitary": []}
    assert InvoiceReturnDialog._catalog_rows_from_response(payload, "tile") == [tile]
    assert [row["branch_name"] for row in InvoiceReturnDialog._stocked_branches(tile)] == ["Stocked"]
    with pytest.raises(ValueError, match="missing the 'tiles' list"):
        InvoiceReturnDialog._catalog_rows_from_response({"rows": [tile]}, "tile")
