import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from models.invoice_item import InvoiceItem
from ui.invoice_window import InvoiceWindow
from ui.master_sanitary_window import MasterSanitaryWindow
from utils.invoice_printer import InvoicePrintWindow
from utils.return_printer import ReturnPrinter

try:
    import pymupdf
except ImportError:
    pymupdf = None


class FakeVar:
    def __init__(self, value=""):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class FakeWidget(FakeVar):
    def __init__(self, value=""):
        super().__init__(value)
        self.options = {}

    def configure(self, **kwargs):
        self.options.update(kwargs)

    def __setitem__(self, key, value):
        self.options[key] = value

    def delete(self, *_args):
        self.value = ""

    def insert(self, _index, value):
        self.value = value


class FakeTree:
    def __init__(self):
        self.rows = {}

    def get_children(self):
        return list(self.rows)

    def delete(self, iid):
        del self.rows[iid]

    def insert(self, _parent, _position, iid, values):
        self.rows[iid] = values


class MasterSanitaryUiTests(unittest.TestCase):
    def setUp(self):
        self.window = InvoiceWindow.__new__(InvoiceWindow)
        self.window.branches = [SimpleNamespace(id=1, name="Tile Index - Korangi"),
                                SimpleNamespace(id=2, name="Tile Cera - Korangi")]
        self.window.master_sanitary_products = [{"id": 8, "name": "Master Basin", "color": "CP"}]
        self.window.selected_branch_id = 1
        self.window.item_type_var = FakeVar("Master Sanitary")
        self.window.product_var = FakeVar("Master Basin - CP")
        self.window.source_branch_var = FakeVar("Tile Cera - Korangi")
        self.window.source_branch_combo = FakeWidget()
        self.window.add_item_button = FakeWidget()
        self.window.stock_info_label = FakeWidget()
        self.window.item_boxes_entry = FakeWidget("3")
        self.window.item_pieces_entry = FakeWidget("0")
        self.window.invoice_items = []
        self.window.update_items_table = lambda: None
        self.window.update_totals = lambda: None
        self.window.confirm_cross_branch_source = lambda _id: True
        self.window.stock_lookup_confirmed = True
        self.row = {"total_quantity": 5, "branches": [
            {"branch_id": 1, "branch_name": "Tile Index - Korangi", "quantity": 0, "unit_price": 2900},
            {"branch_id": 2, "branch_name": "Tile Cera - Korangi", "quantity": 5, "unit_price": 2500},
        ]}

    def test_stock_line_and_draft_revalidation(self):
        self.window.load_stock_overview_row = lambda *_args, **_kwargs: self.row
        self.window.update_stock_info()
        self.assertIn("5 pieces", self.window.stock_info_label.options["text"])
        self.window.add_item()
        line = self.window.invoice_items[0]
        self.assertEqual((line["master_sanitary_product_id"], line["source_branch_id"], line["line_total"]), (8, 2, 7500))
        saved = self.window._draft_item_payload(line)
        self.assertEqual((saved["item_type"], saved["quantity"]), ("master_sanitary", 3))
        rebuilt = self.window._rebuild_draft_item(saved)
        self.assertEqual(rebuilt["line_total"], 7500)
        self.row["branches"][1]["quantity"] = 2
        self.assertIn("Insufficient stock", self.window._rebuild_draft_item(saved)["draft_error"])

    def test_targeted_lookup_uses_master_sanitary_id(self):
        with patch("ui.invoice_window.api_client.get", return_value={"item": self.row}) as get:
            self.window.load_stock_overview_row("master_sanitary", 8)
        self.assertIn("master_sanitary_product_id=8", get.call_args.args[0])

    def test_draft_catalogue_refresh_uses_current_price(self):
        self.window.load_stock_overview_row = lambda *_args, **_kwargs: self.row
        saved = {"item_type": "master_sanitary", "master_sanitary_product_id": 8,
                 "source_branch_id": 2, "quantity": 2, "rate_per_box": 1}
        self.row["branches"][1]["unit_price"] = 3100
        with patch("ui.invoice_window.api_client.get", return_value=[
            {"id": 8, "name": "Master Basin", "color": "CP"},
        ]):
            self.window._refresh_master_sanitary_for_draft([saved])
        self.assertEqual(self.window._rebuild_draft_item(saved)["line_total"], 6200)

    def test_management_table_search_zero_rows_and_currency(self):
        management = MasterSanitaryWindow.__new__(MasterSanitaryWindow)
        management.branches = self.window.branches
        management.branch_var = FakeVar("Tile Index - Korangi")
        management.search_entry = FakeWidget("")
        management.tree = FakeTree()
        management.load_status = FakeWidget()
        management.price_entry = FakeWidget()
        management.selected_id = None
        products = [
            {"id": 8, "name": "Master Basin", "color": "CP", "sku": "MS-000008"},
            {"id": 9, "name": "Master Tap", "color": "Black", "sku": "MS-000009"},
        ]
        responses = {"/catalog/master-sanitary": products,
                     "/inventory/master-sanitary/1": [{"product_id": 8, "quantity": 3, "price": 2500}],
                     "/inventory/master-sanitary/2": [{"product_id": 9, "quantity": 2, "price": 1200}]}
        with patch("ui.master_sanitary_window.api_client.get", side_effect=responses.get):
            management.refresh()
            self.assertEqual(len(management.tree.rows), 2)
            self.assertEqual(management.tree.rows["9:1"][5], 0)
            self.assertEqual(management.tree.rows["8:1"][3], "Rs. 2500.00")
            management.search_entry.value = "black"
            management._populate_table()
            self.assertEqual(list(management.tree.rows), ["9:1"])
            management.search_entry.value = ""
            management.selected_id = 8
            management.branch_var.set("Tile Cera - Korangi")
            management.refresh()
            self.assertEqual(management.tree.rows["9:2"][5], 2)
            self.assertEqual(management.price_entry.get(), "")

    def test_management_commands_send_catalogue_and_stock_payloads(self):
        management = MasterSanitaryWindow.__new__(MasterSanitaryWindow)
        management.branches = [SimpleNamespace(id=1, name="Tile Index - Korangi")]
        management.branch_var = FakeVar("Tile Index - Korangi")
        management.name_entry = FakeWidget("Master Tap")
        management.color_entry = FakeWidget("CP")
        management.price_entry = FakeWidget("1200")
        management.quantity_entry = FakeWidget("3")
        management.reason_entry = FakeWidget("New delivery")
        management.dc_entry = FakeWidget("DC-45")
        management.selected_id = None
        management.refresh = lambda: None
        with patch("ui.master_sanitary_window.api_client.post") as post:
            management.save_product()
            post.assert_called_once_with("/catalog/master-sanitary", {"name": "Master Tap", "color": "CP"})
        management.selected_id = 8
        management.price_entry.value = "1200"
        with patch("ui.master_sanitary_window.api_client.put") as put:
            management.save_price()
            put.assert_called_once_with("/inventory/master-sanitary/8/price", {"branch_id": 1, "price": "1200"})
        management.quantity_entry.value = "3"
        with patch("ui.master_sanitary_window.api_client.post") as post:
            management.adjust_stock("stock-in")
            post.assert_called_once_with("/inventory/master-sanitary/8/stock-in", {
                "branch_id": 1, "quantity": 3, "notes": "New delivery", "dc_number": "DC-45",
            })
        management.quantity_entry.value = "1"
        management.reason_entry.value = "Used for display"
        with patch("ui.master_sanitary_window.api_client.post") as post:
            management.adjust_stock("stock-out")
            post.assert_called_once_with("/inventory/master-sanitary/8/stock-out", {
                "branch_id": 1, "quantity": 1, "notes": "Used for display", "dc_number": "DC-45",
            })

    @unittest.skipIf(pymupdf is None, "PyMuPDF is not installed")
    def test_invoice_pdf_shows_name_color_price_and_source(self):
        with tempfile.TemporaryDirectory() as temp:
            printer = InvoicePrintWindow.__new__(InvoicePrintWindow)
            printer.branch = SimpleNamespace(name="Tile Index - Korangi")
            printer.branches = {1: printer.branch, 2: SimpleNamespace(name="Tile Cera - Korangi")}
            printer.products = {}
            printer.accessories = {}
            printer.sanitary_products = {}
            printer.loose_pcs_products = {}
            printer.master_sanitary_products = {8: {"name": "Master Basin", "color": "CP"}}
            printer.payments = []
            printer.invoice = SimpleNamespace(
                invoice_number="TIK-TEST", branch_id=1, invoice_date=datetime.now(timezone.utc),
                customer_name="Local Customer", customer_contact=None, status="active",
                items=[InvoiceItem(master_sanitary_product_id=8, item_type="master_sanitary",
                                   source_branch_id=2, description="Master Basin - CP", tile_size="CP",
                                   quantity=3, unit_price=2500, line_total=7500)],
                subtotal=7500, discount=0, grand_total=7500, paid_amount=0, balance=7500, remarks=None,
            )
            path = Path(temp) / "sample.pdf"
            printer.next_invoice_pdf_path = lambda: str(path)
            printer.generate_invoice_pdf()
            with pymupdf.open(path) as pdf:
                text = "\n".join(page.get_text() for page in pdf)
            self.assertIn("Master Basin - CP", text)
            self.assertIn("Source: Tile Cera - Korangi", text)
            self.assertIn("2500.00", text)

    @unittest.skipIf(pymupdf is None, "PyMuPDF is not installed")
    def test_return_pdf_shows_master_sanitary_piece_quantity(self):
        original = SimpleNamespace(id=5, description="Master Basin - CP")
        invoice = SimpleNamespace(invoice_number="TIK-TEST", customer_name="Local Customer", items=[original])
        record = {
            "return_number": "RET-TEST", "return_date": "2026-11-16", "reason": "Change of color",
            "return_items": [{"invoice_item_id": 5, "item_type": "master_sanitary", "quantity": 1,
                              "boxes": 0, "loose_pieces": 0, "source_branch_id": 2,
                              "discounted_line_total": 2500}],
            "exchange_items": [{"item_type": "master_sanitary", "description": "Master Basin - Black",
                                "quantity": 1, "boxes": 0, "loose_pieces": 0, "source_branch_id": 2,
                                "line_total": 2800}],
            "difference_amount": -300, "returned_value": 2500, "exchange_value": 2800,
            "settled_amount": 0, "outstanding_amount": 300,
        }
        with tempfile.TemporaryDirectory() as temp, patch.dict("os.environ", {"LOCALAPPDATA": temp}), patch(
            "utils.return_printer.BranchRepository.get_all",
            return_value=[SimpleNamespace(id=2, name="Tile Cera - Korangi")],
        ):
            path = ReturnPrinter(invoice, record).generate_pdf()
            with pymupdf.open(path) as pdf:
                text = "\n".join(page.get_text() for page in pdf)
        self.assertIn("Master Basin - CP", text)
        self.assertIn("Master Basin - Black", text)
        self.assertIn("1 pieces", text)


if __name__ == "__main__":
    unittest.main()
