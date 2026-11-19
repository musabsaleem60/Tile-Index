"""Local API regression for Master Sanitary catalogue and sale workflows."""

import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "local-master-sanitary-test-only")

from app.api.deps import get_current_user  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.base import Base  # noqa: E402
from app.models.entities import ActivityLog, Branch, MasterSanitaryInventory, StockTransaction, User  # noqa: E402
from test_loose_pcs import LocalClient  # noqa: E402


class MasterSanitaryApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.engine = create_engine(f"sqlite:///{Path(self.temp.name) / 'local.db'}")

        @event.listens_for(self.engine, "connect")
        def enable_foreign_keys(connection, _record):
            connection.execute("PRAGMA foreign_keys=ON")

        Base.metadata.create_all(self.engine)
        with Session(self.engine) as db:
            db.add_all([
                Branch(id=1, name="Tile Index - Korangi", code="TIK"),
                Branch(id=2, name="Tile Cera - Korangi", code="TCK"),
                User(id=1, username="local_admin", password_hash="unused", role="admin", is_active=True),
            ])
            db.commit()

        def local_db():
            with Session(self.engine) as db:
                yield db

        def local_user():
            with Session(self.engine) as db:
                return db.get(User, 1)

        app.dependency_overrides[get_db] = local_db
        app.dependency_overrides[get_current_user] = local_user
        self.client = LocalClient()

    def tearDown(self):
        app.dependency_overrides.clear()
        self.engine.dispose()
        self.temp.cleanup()

    def ok(self, response, expected=200):
        self.assertEqual(response.status_code, expected, response.text)
        return response.json()

    def create_product(self, name="  Master   Basin  ", color=" CP "):
        return self.ok(self.client.post("/catalog/master-sanitary", json={"name": name, "color": color}))

    def set_price(self, product_id, branch_id, price):
        return self.ok(self.client.put(f"/inventory/master-sanitary/{product_id}/price", json={
            "branch_id": branch_id, "price": price,
        }))

    def stock(self, product_id, branch_id):
        rows = self.ok(self.client.get(f"/inventory/master-sanitary/{branch_id}"))
        return next((row["quantity"] for row in rows if row["product_id"] == product_id), 0)

    def test_catalogue_stock_sale_return_void_exchange(self):
        product = self.create_product()
        product_id = product["id"]
        self.assertEqual((product["name"], product["color"], product["sku"]),
                         ("Master Basin", "CP", f"MS-{product_id:06d}"))
        self.ok(self.client.post("/catalog/master-sanitary", json={"name": "master basin", "color": "cp"}), 409)
        self.ok(self.client.put(f"/catalog/master-sanitary/{product_id}", json={"name": "Master  Basin", "color": "Cp"}))
        second = self.create_product("Master Shower", "Chrome")
        self.ok(self.client.put(f"/catalog/master-sanitary/{second['id']}", json={"name": "MASTER BASIN", "color": " cP "}), 409)
        row = self.set_price(product_id, 2, 2600)
        self.assertEqual((row["quantity"], row["price"]), (0, 2600))
        self.set_price(product_id, 1, 2900)
        self.set_price(second["id"], 2, 1800)
        self.ok(self.client.post(f"/inventory/master-sanitary/{product_id}/stock-in", json={
            "branch_id": 2, "quantity": 10, "notes": "Opening stock", "dc_number": "DC-42",
        }))
        self.ok(self.client.post(f"/inventory/master-sanitary/{second['id']}/stock-in", json={"branch_id": 2, "quantity": 5}))
        self.ok(self.client.post(f"/inventory/master-sanitary/{product_id}/stock-out", json={
            "branch_id": 2, "quantity": 1, "notes": "Used for display", "dc_number": "DC-43",
        }))
        self.ok(self.client.post(f"/inventory/master-sanitary/{product_id}/stock-out", json={"branch_id": 2, "quantity": 1}), 400)
        self.ok(self.client.post(f"/inventory/master-sanitary/{product_id}/stock-out", json={
            "branch_id": 2, "quantity": 100, "notes": "Too many items",
        }), 400)
        self.assertEqual(self.stock(product_id, 2), 9)
        self.assertEqual(next(row["price"] for row in self.ok(self.client.get("/inventory/master-sanitary/2")) if row["product_id"] == product_id), 2600)
        overview = self.ok(self.client.get("/stock/overview?item_type=master_sanitary"))
        self.assertEqual(len(overview["master_sanitary"]), 2)
        item = self.ok(self.client.get(f"/stock/item?item_type=master_sanitary&master_sanitary_product_id={product_id}"))["item"]
        branch_prices = {row["branch_id"]: row["unit_price"] for row in item["branches"]}
        self.assertEqual((item["total_quantity"], branch_prices[2]), (9, 2600))
        self.assertEqual(branch_prices[1], 2900)
        request = {"branch_id": 1, "customer_name": "Local Customer", "items": [{
            "item_type": "master_sanitary", "master_sanitary_product_id": product_id,
            "source_branch_id": 2, "quantity": 3,
        }]}
        invoice = self.ok(self.client.post("/invoices", json=request))
        self.assertEqual((invoice["grand_total"], invoice["items"][0]["description"]), (7800, "Master Basin - Cp"))
        self.assertEqual(self.stock(product_id, 2), 6)
        self.set_price(product_id, 2, 2800)
        self.assertEqual(self.ok(self.client.get(f"/invoices/{invoice['id']}"))["items"][0]["unit_price"], 2600)
        returned = self.ok(self.client.post(f"/invoices/{invoice['id']}/returns", json={
            "return_date": datetime.now(timezone.utc).isoformat(), "reason": "Customer changed mind",
            "return_items": [{"invoice_item_id": invoice["items"][0]["id"], "quantity": 1}],
            "exchange_items": [{"item_type": "master_sanitary", "master_sanitary_product_id": second["id"],
                                "source_branch_id": 2, "quantity": 1}],
        }))
        self.assertEqual((returned["returned_value"], returned["exchange_value"]), (2600, 1800))
        self.assertEqual(returned["exchange_items"][0]["master_sanitary_product_id"], second["id"])
        self.assertEqual((self.stock(product_id, 2), self.stock(second["id"], 2)), (7, 4))
        self.ok(self.client.post(f"/invoices/{invoice['id']}/returns", json={
            "return_date": datetime.now(timezone.utc).isoformat(), "reason": "Excessive return request",
            "return_items": [{"invoice_item_id": invoice["items"][0]["id"], "quantity": 3}],
        }), 409)
        another = self.ok(self.client.post("/invoices", json=request))
        self.ok(self.client.post(f"/invoices/{another['id']}/void", json={"reason": "Local test correction"}))
        self.assertEqual(self.stock(product_id, 2), 7)
        logs = self.ok(self.client.get(f"/activity-log?master_sanitary_product_id={product_id}&view=all"))
        actions = {row["action_type"] for row in logs}
        self.assertTrue({"Master Sanitary Added", "Master Sanitary Edited", "Master Sanitary Price Updated", "Master Sanitary Stock IN",
                         "Master Sanitary Stock OUT", "Master Sanitary Sold", "Master Sanitary Returned",
                         "Master Sanitary Sale Voided"} <= actions)
        exchange_logs = self.ok(self.client.get(f"/activity-log?master_sanitary_product_id={second['id']}&view=all"))
        self.assertIn("Master Sanitary Exchanged", {row["action_type"] for row in exchange_logs})
        with Session(self.engine) as db:
            price_logs = db.scalars(select(ActivityLog).where(ActivityLog.action_type == "Master Sanitary Price Updated", ActivityLog.master_sanitary_product_id == product_id)).all()
            self.assertTrue(any('"old_price": 2600.0' in (row.action_details or "") and '"new_price": 2800.0' in (row.action_details or "") for row in price_logs))
            transactions = db.scalars(select(StockTransaction).where(StockTransaction.master_sanitary_product_id == product_id)).all()
            self.assertGreaterEqual(len(transactions), 6)
            self.assertEqual(transactions[0].dc_number, "DC-42")
            self.assertEqual(db.scalar(select(MasterSanitaryInventory).where(MasterSanitaryInventory.product_id == product_id)).quantity, 7)

    def test_delete_and_branch_access(self):
        product = self.create_product()
        self.ok(self.client.delete(f"/catalog/master-sanitary/{product['id']}"))
        product = self.create_product()
        with Session(self.engine) as db:
            user = db.get(User, 1)
            user.role = "employee"
            user.branch_id = 1
            db.commit()
        self.ok(self.client.post(f"/inventory/master-sanitary/{product['id']}/stock-in", json={"branch_id": 2, "quantity": 1}), 403)
        self.ok(self.client.post(f"/inventory/master-sanitary/{product['id']}/stock-in", json={"branch_id": 1, "quantity": 1}))
        self.ok(self.client.delete(f"/catalog/master-sanitary/{product['id']}"), 409)

    def test_missing_price_blocks_sale_and_quantities_are_whole(self):
        product = self.create_product()
        self.ok(self.client.post(f"/inventory/master-sanitary/{product['id']}/stock-in", json={
            "branch_id": 2, "quantity": 2,
        }))
        request = {"branch_id": 1, "customer_name": "Local Customer", "items": [{
            "item_type": "master_sanitary", "master_sanitary_product_id": product["id"],
            "source_branch_id": 2, "quantity": 1,
        }]}
        error = self.ok(self.client.post("/invoices", json=request), 400)
        self.assertIn("No Master Sanitary price set", error["detail"])
        self.assertEqual(self.stock(product["id"], 2), 2)
        self.ok(self.client.post(f"/inventory/master-sanitary/{product['id']}/stock-in", json={
            "branch_id": 2, "quantity": 1.5,
        }), 422)
        request["items"][0]["quantity"] = 1.5
        self.ok(self.client.post("/invoices", json=request), 422)


if __name__ == "__main__":
    unittest.main()
