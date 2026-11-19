"""Local API regression for piece-only catalogue, stock, invoice, void, and return."""

import os
import sys
import tempfile
import unittest
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "local-loose-pcs-test-only")

from app.api.deps import get_current_user  # noqa: E402
from app.models.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.entities import ActivityLog, Branch, LoosePcsInventory, StockTransaction, User  # noqa: E402


class LocalResponse:
    def __init__(self, status_code, body):
        self.status_code = status_code
        self.text = body.decode()

    def json(self):
        return json.loads(self.text)


class LocalClient:
    """Exercise the real ASGI routes without an optional HTTP test dependency."""

    def request(self, method, url, json_data=None):
        parsed = urlsplit(url)
        body = json.dumps(json_data).encode() if json_data is not None else b""
        messages = []

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            messages.append(message)

        scope = {
            "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
            "method": method, "scheme": "http", "path": parsed.path,
            "raw_path": parsed.path.encode(), "query_string": parsed.query.encode(),
            "root_path": "", "server": ("local", 80), "client": ("local", 0),
            "headers": [(b"host", b"local"), (b"content-type", b"application/json")],
        }
        asyncio.run(app(scope, receive, send))
        status = next(message["status"] for message in messages if message["type"] == "http.response.start")
        response_body = b"".join(message.get("body", b"") for message in messages if message["type"] == "http.response.body")
        return LocalResponse(status, response_body)

    def get(self, url):
        return self.request("GET", url)

    def post(self, url, json):
        return self.request("POST", url, json)

    def put(self, url, json):
        return self.request("PUT", url, json)

    def delete(self, url):
        return self.request("DELETE", url)

    def close(self):
        pass


class LoosePcsApiTests(unittest.TestCase):
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
        self.client.close()
        app.dependency_overrides.clear()
        self.engine.dispose()
        self.temp.cleanup()

    def _ok(self, response, expected=200):
        self.assertEqual(response.status_code, expected, response.text)
        return response.json()

    def test_catalogue_stock_invoice_void_return(self):
        product = self._ok(self.client.post("/catalog/loose-pcs", json={
            "name": "Kitchen Motif", "size": "12x24", "price": 1200,
        }))
        product_id = product["id"]
        self.assertEqual(product["sku"], f"LPC-{product_id:06d}")
        self._ok(self.client.post("/catalog/loose-pcs", json={
            "name": "Kitchen Motif", "size": "12x24", "price": 1200,
        }), 409)
        self._ok(self.client.put(f"/catalog/loose-pcs/{product_id}", json={
            "name": "Kitchen Motif", "size": "12x24", "price": 1250,
        }))
        self._ok(self.client.post(f"/inventory/loose-pcs/{product_id}/stock-in", json={
            "branch_id": 2, "quantity": 10, "notes": "Initial stock", "dc_number": "DC-1",
        }))
        self._ok(self.client.post(f"/inventory/loose-pcs/{product_id}/stock-out", json={
            "branch_id": 2, "quantity": 1, "notes": "Used for display",
        }))
        self.assertEqual(self._ok(self.client.get("/inventory/loose-pcs/2"))[0]["quantity"], 9)
        overview = self._ok(self.client.get("/stock/overview?item_type=loose_pcs"))
        self.assertEqual(overview["loose_pcs"][0]["total_quantity"], 9)
        item = self._ok(self.client.get(f"/stock/item?item_type=loose_pcs&loose_pcs_product_id={product_id}"))["item"]
        self.assertEqual(next(b["quantity"] for b in item["branches"] if b["branch_id"] == 2), 9)
        request = {"branch_id": 1, "customer_name": "Local Customer", "paid_amount": 0, "items": [{
            "item_type": "loose_pcs", "loose_pcs_product_id": product_id, "source_branch_id": 2,
            "quantity": 3, "boxes": 0, "loose_pieces": 0,
        }]}
        invoice = self._ok(self.client.post("/invoices", json=request))
        self.assertEqual(invoice["grand_total"], 3750)
        self.assertEqual(invoice["items"][0]["unit_price"], 1250)
        self.assertEqual(self._ok(self.client.get("/inventory/loose-pcs/2"))[0]["quantity"], 6)
        self._ok(self.client.put(f"/catalog/loose-pcs/{product_id}", json={
            "name": "Kitchen Motif", "size": "12x24", "price": 1300,
        }))
        returned = self._ok(self.client.post(f"/invoices/{invoice['id']}/returns", json={
            "return_date": datetime.now(timezone.utc).isoformat(), "reason": "Customer changed mind",
            "return_items": [{"invoice_item_id": invoice["items"][0]["id"], "quantity": 1}],
        }))
        self.assertEqual(returned["returned_value"], 1250)
        self.assertEqual(self._ok(self.client.get("/inventory/loose-pcs/2"))[0]["quantity"], 7)
        history = self._ok(self.client.get(f"/activity-log?loose_pcs_product_id={product_id}&view=all"))
        self.assertTrue(history)
        self.assertTrue(all(row["loose_pcs_product_id"] == product_id for row in history))
        second = self._ok(self.client.post("/invoices", json=request))
        self._ok(self.client.post(f"/invoices/{second['id']}/void", json={"reason": "Local test correction"}))
        self.assertEqual(self._ok(self.client.get("/inventory/loose-pcs/2"))[0]["quantity"], 7)
        with Session(self.engine) as db:
            logs = db.scalars(select(ActivityLog).where(ActivityLog.loose_pcs_product_id == product_id)).all()
            actions = {row.action_type for row in logs}
            self.assertTrue({"Loose Pcs Added", "Loose Pcs Edited", "Loose Pcs Stock IN", "Loose Pcs Stock OUT", "Loose Pcs Sold", "Loose Pcs Returned", "Loose Pcs Sale Voided"} <= actions)
            transactions = db.scalars(select(StockTransaction).where(StockTransaction.loose_pcs_product_id == product_id)).all()
            self.assertGreaterEqual(len(transactions), 6)
            self.assertEqual(db.scalar(select(LoosePcsInventory).where(LoosePcsInventory.branch_id == 2)).quantity, 7)

    def test_employee_branch_access(self):
        product = self._ok(self.client.post("/catalog/loose-pcs", json={
            "name": "Silver Border", "size": "2x24", "price": 220,
        }))
        with Session(self.engine) as db:
            user = db.get(User, 1)
            user.role = "employee"
            user.branch_id = 1
            db.commit()
        self._ok(self.client.post(f"/inventory/loose-pcs/{product['id']}/stock-in", json={
            "branch_id": 2, "quantity": 3,
        }), 403)
        self._ok(self.client.post(f"/inventory/loose-pcs/{product['id']}/stock-in", json={
            "branch_id": 1, "quantity": 3,
        }))
        with Session(self.engine) as db:
            db.get(User, 1).branch_id = None
            db.commit()
        self._ok(self.client.post(f"/inventory/loose-pcs/{product['id']}/stock-in", json={
            "branch_id": 2, "quantity": 3,
        }))

    def test_catalogue_delete_rejects_stock_and_allows_empty_product(self):
        product = self._ok(self.client.post("/catalog/loose-pcs", json={
            "name": "Silver Border", "size": "2x24", "price": 220,
        }))
        self._ok(self.client.delete(f"/catalog/loose-pcs/{product['id']}"))
        product = self._ok(self.client.post("/catalog/loose-pcs", json={
            "name": "Silver Border", "size": "2x24", "price": 220,
        }))
        self._ok(self.client.post(f"/inventory/loose-pcs/{product['id']}/stock-in", json={
            "branch_id": 1, "quantity": 2,
        }))
        self._ok(self.client.delete(f"/catalog/loose-pcs/{product['id']}"), 409)

    def test_loose_pcs_exchange_uses_current_price_and_stock(self):
        old = self._ok(self.client.post("/catalog/loose-pcs", json={
            "name": "Kitchen Motif", "size": "12x24", "price": 1200,
        }))
        new = self._ok(self.client.post("/catalog/loose-pcs", json={
            "name": "Ayat Tiles", "size": "12x24", "price": 1000,
        }))
        for product in (old, new):
            self._ok(self.client.post(f"/inventory/loose-pcs/{product['id']}/stock-in", json={
                "branch_id": 2, "quantity": 5,
            }))
        invoice = self._ok(self.client.post("/invoices", json={
            "branch_id": 1, "customer_name": "Exchange Customer", "items": [{
                "item_type": "loose_pcs", "loose_pcs_product_id": old["id"],
                "source_branch_id": 2, "quantity": 2,
            }],
        }))
        returned = self._ok(self.client.post(f"/invoices/{invoice['id']}/returns", json={
            "return_date": datetime.now(timezone.utc).isoformat(), "reason": "Exchange motif design",
            "return_items": [{"invoice_item_id": invoice["items"][0]["id"], "quantity": 1}],
            "exchange_items": [{"item_type": "loose_pcs", "loose_pcs_product_id": new["id"],
                                "source_branch_id": 2, "quantity": 1}],
        }))
        self.assertEqual((returned["returned_value"], returned["exchange_value"], returned["difference_amount"]), (1200, 1000, 200))
        self.assertEqual(returned["exchange_items"][0]["loose_pcs_product_id"], new["id"])
        by_product = {row["product_id"]: row["quantity"] for row in self._ok(self.client.get("/inventory/loose-pcs/2"))}
        self.assertEqual(by_product, {old["id"]: 4, new["id"]: 4})


if __name__ == "__main__":
    unittest.main()
