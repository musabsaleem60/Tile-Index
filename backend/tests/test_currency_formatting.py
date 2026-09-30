import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.core.currency import clamp_currency_zero, format_currency
from app.models.entities import InvoiceItem
from app.schemas.common import InvoiceCreate, InvoiceItemIn
from app.services.invoices import create_invoice


class CurrencyFormattingTests(unittest.TestCase):
    def test_sub_cent_residue_displays_as_positive_zero(self):
        self.assertEqual(format_currency(-0.0000001), "Rs. 0.00")
        self.assertEqual(format_currency(0.005), "Rs. 0.00")

    def test_real_values_are_preserved(self):
        self.assertEqual(format_currency(-0.01), "Rs. -0.01")
        self.assertEqual(format_currency(1), "Rs. 1.00")

    def test_invoice_balance_residue_is_zero_but_real_negative_is_preserved(self):
        subtotal = 8119.999999999999
        grand_total = subtotal - 120
        self.assertEqual(clamp_currency_zero(grand_total - 8000), 0)
        self.assertLess(clamp_currency_zero(grand_total - 8000.02), 0)

    @patch("app.services.invoices.write_audit_log")
    @patch("app.services.invoices._next_invoice_number", return_value="TIK-TEST")
    @patch("app.services.invoices._build_invoice_item_and_update_stock")
    def test_backend_create_accepts_epsilon_zero_balance(
        self, build_item, _next_number, _write_audit
    ):
        build_item.return_value = InvoiceItem(
            source_branch_id=1,
            item_type="tile",
            description="Test tile",
            tile_size="8x12",
            grade="G3 Regular",
            boxes=4,
            loose_pieces=0,
            quantity=92,
            rate_per_sqm=1450,
            rate_per_box=2029.9999999999998,
            rate_per_piece=88.26086956521738,
            unit_price=0,
            line_total=8119.999999999999,
        )
        payload = InvoiceCreate(
            branch_id=1,
            customer_name="Customer",
            discount=120,
            paid_amount=8000,
            items=[InvoiceItemIn(item_type="tile", product_id=1, grade="G3 Regular", boxes=4)],
        )
        holder = {}
        db = Mock()
        db.get.return_value = SimpleNamespace(id=1, code="TIK", name="Tile Index - Korangi")
        db.add.side_effect = lambda invoice: holder.setdefault("invoice", invoice)
        db.scalar.side_effect = lambda _statement: holder["invoice"]

        invoice = create_invoice(db, payload, SimpleNamespace(id=1))

        self.assertEqual(invoice.balance, 0)
        db.add.assert_called_once()

    @patch("app.services.invoices.write_audit_log")
    @patch("app.services.invoices._next_invoice_number", return_value="TIK-TEST")
    @patch("app.services.invoices._build_invoice_item_and_update_stock")
    def test_backend_create_rejects_real_negative_balance(
        self, build_item, _next_number, _write_audit
    ):
        build_item.return_value = InvoiceItem(
            source_branch_id=1, item_type="tile", description="Test tile",
            boxes=4, loose_pieces=0, quantity=92, rate_per_sqm=1450,
            rate_per_box=2030, rate_per_piece=88.26, unit_price=0,
            line_total=8119.999999999999,
        )
        payload = InvoiceCreate(
            branch_id=1, customer_name="Customer", discount=120.02,
            paid_amount=8000,
            items=[InvoiceItemIn(item_type="tile", product_id=1, grade="G3 Regular", boxes=4)],
        )
        db = Mock()
        db.get.return_value = SimpleNamespace(id=1, code="TIK", name="Tile Index - Korangi")

        with self.assertRaisesRegex(Exception, "Paid amount exceeds invoice total"):
            create_invoice(db, payload, SimpleNamespace(id=1))

        db.add.assert_not_called()


if __name__ == "__main__":
    unittest.main()
