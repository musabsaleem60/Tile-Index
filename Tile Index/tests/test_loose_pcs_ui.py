import unittest
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from datetime import datetime, timezone

try:
    import pymupdf
except ImportError:
    pymupdf = None

from ui.invoice_window import InvoiceWindow
from utils.invoice_printer import InvoicePrintWindow
from models.invoice_item import InvoiceItem


class Var:
    def __init__(self, value=""):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class Widget:
    def __init__(self, value=""):
        self.value = value
        self.options = {}

    def get(self):
        return self.value

    def configure(self, **kwargs):
        self.options.update(kwargs)

    def __setitem__(self, key, value):
        self.options[key] = value


class LoosePcsInvoiceUiTests(unittest.TestCase):
    def setUp(self):
        self.window = InvoiceWindow.__new__(InvoiceWindow)
        self.window.branches = [SimpleNamespace(id=1, name="Tile Index - Korangi"),
                                SimpleNamespace(id=2, name="Tile Cera - Korangi")]
        self.window.loose_pcs_products = [{"id": 8, "name": "Kitchen Motif", "size": "12x24", "price": 1200}]
        self.window.selected_branch_id = 1
        self.window.item_type_var = Var("Loose Pcs")
        self.window.product_var = Var("Kitchen Motif - 12x24")
        self.window.source_branch_var = Var("Tile Cera - Korangi")
        self.window.source_branch_combo = Widget()
        self.window.add_item_button = Widget()
        self.window.stock_info_label = Widget()
        self.window.item_boxes_entry = Widget("3")
        self.window.item_pieces_entry = Widget("0")
        self.window.invoice_items = []
        self.window.update_items_table = lambda: None
        self.window.update_totals = lambda: None
        self.window.confirm_cross_branch_source = lambda _id: True
        self.window.stock_lookup_confirmed = True
        self.row = {"total_quantity": 5, "branches": [
            {"branch_id": 1, "branch_name": "Tile Index - Korangi", "quantity": 0},
            {"branch_id": 2, "branch_name": "Tile Cera - Korangi", "quantity": 5},
        ]}

    def test_stock_and_line_use_piece_quantity_and_source_branch(self):
        self.window.load_stock_overview_row = lambda *_args, **_kwargs: self.row
        self.window.update_stock_info()
        self.assertIn("5 pieces", self.window.stock_info_label.options["text"])
        self.window.item_boxes_entry.delete = lambda *_: None
        self.window.item_boxes_entry.insert = lambda *_: None
        self.window.item_pieces_entry.delete = lambda *_: None
        self.window.item_pieces_entry.insert = lambda *_: None
        self.window.add_item()
        self.assertEqual(len(self.window.invoice_items), 1)
        line = self.window.invoice_items[0]
        self.assertEqual((line["loose_pcs_product_id"], line["source_branch_id"], line["boxes"]), (8, 2, 3))
        self.assertEqual(line["line_total"], 3600)
        draft_line = self.window._draft_item_payload(line)
        self.assertEqual((draft_line["item_type"], draft_line["quantity"]), ("loose_pcs", 3))

    def test_targeted_lookup_uses_loose_pcs_id(self):
        with patch("ui.invoice_window.api_client.get", return_value={"item": self.row}) as get:
            self.window.load_stock_overview_row("loose_pcs", 8)
        self.assertIn("loose_pcs_product_id=8", get.call_args.args[0])

    def test_draft_resume_uses_current_price_and_stock(self):
        self.window.load_stock_overview_row = lambda *_args, **_kwargs: self.row
        saved = {"item_type": "loose_pcs", "loose_pcs_product_id": 8,
                 "source_branch_id": 2, "quantity": 3, "rate_per_box": 1}
        line = self.window._rebuild_draft_item(saved)
        self.assertEqual(line["line_total"], 3600)
        self.assertEqual(line["_draft_available_units"], 5)
        self.row["branches"][1]["quantity"] = 2
        line = self.window._rebuild_draft_item(saved)
        self.assertIn("Insufficient stock", line["draft_error"])

    @unittest.skipIf(pymupdf is None, "PyMuPDF is not installed")
    def test_pdf_shows_quantity_and_price_in_piece_columns(self):
        with tempfile.TemporaryDirectory() as temp:
            printer = InvoicePrintWindow.__new__(InvoicePrintWindow)
            printer.branch = SimpleNamespace(name="Tile Index - Korangi")
            printer.branches = {1: printer.branch, 2: SimpleNamespace(name="Tile Cera - Korangi")}
            printer.products = {}
            printer.accessories = {}
            printer.sanitary_products = {}
            printer.loose_pcs_products = {8: {"name": "Kitchen Motif", "size": "12x24"}}
            printer.payments = []
            printer.invoice = SimpleNamespace(
                invoice_number="TIK-TEST", branch_id=1, invoice_date=datetime.now(timezone.utc),
                customer_name="Local Customer", customer_contact=None, status="active",
                items=[InvoiceItem(loose_pcs_product_id=8, item_type="loose_pcs",
                                   source_branch_id=2, description="Kitchen Motif - 12x24",
                                   tile_size="12x24", quantity=3, unit_price=1200, line_total=3600)],
                subtotal=3600, discount=0, grand_total=3600, paid_amount=0, balance=3600, remarks=None,
            )
            path = Path(temp) / "sample.pdf"
            printer.next_invoice_pdf_path = lambda: str(path)
            printer.generate_invoice_pdf()
            with pymupdf.open(path) as pdf:
                text = "\n".join(page.get_text() for page in pdf)
            self.assertIn("Kitchen Motif - 12x24", text)
            self.assertIn("Source: Tile Cera - Korangi", text)
            self.assertIn("1200.00", text)
            self.assertTrue(path.stat().st_size > 1000)


if __name__ == "__main__":
    unittest.main()
