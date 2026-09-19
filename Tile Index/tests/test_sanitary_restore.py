import sys
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
if str(ROOT / "Tile Index") not in sys.path:
    sys.path.insert(0, str(ROOT / "Tile Index"))

from app.api.stock import _sanitary_item_row, _sanitary_rows
from app.models.base import Base
from app.models.entities import (
    Branch,
    Invoice,
    SanitaryInventory,
    SanitaryProduct,
    SanitaryStockTransaction,
    User,
)
from app.schemas.common import InvoiceCreate, InvoiceItemIn
from app.services.invoices import create_invoice, void_invoice


def test_sanitary_stock_invoice_and_void_round_trip(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'sanitary.db'}")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        selling_branch = Branch(name="Tile Index - Korangi", code="TIK")
        source_branch = Branch(name="Tile Cera - Korangi", code="TCK")
        user = User(username="employee", password_hash="unused", role="employee", branch_id=None)
        product = SanitaryProduct(
            company_name="Heritage",
            product_category="Floor Mounted Commode (Nova)",
            color="White",
            purchase_price=0,
            sale_price=18500,
            sku="SAN-TEST-001",
        )
        zero_product = SanitaryProduct(
            company_name="Sunny Ceramic",
            product_category="Zero Stock Basin",
            color="Off-White",
            purchase_price=0,
            sale_price=6000,
            sku="SAN-TEST-002",
        )
        db.add_all([selling_branch, source_branch, user, product, zero_product])
        db.flush()
        stock = SanitaryInventory(
            branch_id=source_branch.id,
            sanitary_product_id=product.id,
            quantity=7,
        )
        db.add(stock)
        db.commit()

        branches = db.scalars(select(Branch).order_by(Branch.name)).all()
        item_row = _sanitary_item_row(db, branches, product)
        assert item_row["product"] == "Heritage - Floor Mounted Commode (Nova) - White"
        assert item_row["total_quantity"] == 7
        assert item_row["unit_price"] == 18500
        assert any(
            row["branch_id"] == source_branch.id and row["quantity"] == 7
            for row in item_row["branches"]
        )
        overview_rows = _sanitary_rows(db, branches, "nova", None, False)
        assert len(overview_rows) == 1
        source_row = next(
            row for row in overview_rows[0]["branches"]
            if row["branch_id"] == source_branch.id
        )
        assert source_row["quantity"] == 7
        assert _sanitary_rows(db, branches, "zero stock", None, False) == []
        assert len(_sanitary_rows(db, branches, "zero stock", None, True)) == 1

        payload = InvoiceCreate(
            branch_id=selling_branch.id,
            customer_name="Local Sanitary Test",
            discount=0,
            paid_amount=0,
            items=[InvoiceItemIn(
                item_type="sanitary",
                sanitary_product_id=product.id,
                source_branch_id=source_branch.id,
                quantity=2,
            )],
        )
        invoice = create_invoice(db, payload, user)
        db.commit()
        assert stock.quantity == 5
        assert invoice.grand_total == 37000
        assert invoice.items[0].source_branch_id == source_branch.id

        void_invoice(db, invoice.id, "Local sanitary test void", user)
        db.commit()
        db.refresh(stock)
        db.refresh(invoice)
        assert stock.quantity == 7
        assert invoice.status == "void"
        transactions = db.scalars(
            select(SanitaryStockTransaction).order_by(SanitaryStockTransaction.id)
        ).all()
        assert [(row.transaction_type, row.quantity) for row in transactions] == [
            ("OUT", 2),
            ("IN", 2),
        ]
    engine.dispose()


def test_sanitary_stock_routes_accept_query_values(tmp_path):
    from app.main import app

    routes = {
        route.path: route for route in app.routes
        if route.path in {"/stock/overview", "/stock/item"}
    }
    for path in ("/stock/overview", "/stock/item"):
        item_type = next(
            field for field in routes[path].dependant.query_params
            if field.name == "item_type"
        )
        value, error = item_type.validate(
            "sanitary", {}, loc=("query", "item_type")
        )
        assert error is None
        assert value == "sanitary"
