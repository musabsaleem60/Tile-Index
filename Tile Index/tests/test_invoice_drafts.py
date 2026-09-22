import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from ui.invoice_window import InvoiceWindow
from utils.invoice_draft_store import DRAFT_SCHEMA_VERSION, InvoiceDraftStore


class InvoiceDraftStoreTests(unittest.TestCase):
    def test_atomic_round_trip_and_user_isolation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            first = InvoiceDraftStore(10, root=temp_dir)
            second = InvoiceDraftStore(11, root=temp_dir)
            first.save({"saved_at": "2026-09-22T12:00:00+05:00", "items": [{"product_id": 7}]})
            second.save({"saved_at": "2026-09-22T12:01:00+05:00", "items": []})

            self.assertNotEqual(first.path, second.path)
            self.assertEqual(first.load()["items"][0]["product_id"], 7)
            self.assertEqual(second.load()["items"], [])
            self.assertEqual(first.load()["schema_version"], DRAFT_SCHEMA_VERSION)
            self.assertEqual(list(Path(temp_dir).glob("*.tmp")), [])

    def test_overwrite_replaces_complete_document(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = InvoiceDraftStore(4, root=temp_dir)
            store.save({"saved_at": "first", "items": [{"product_id": 1}]})
            store.save({"saved_at": "second", "items": [{"product_id": 2}]})
            self.assertEqual(store.load()["saved_at"], "second")
            self.assertEqual(store.load()["items"], [{"product_id": 2}])

    def test_rejects_draft_for_different_user(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = InvoiceDraftStore(8, root=temp_dir)
            store.root.mkdir(parents=True, exist_ok=True)
            store.path.write_text(
                json.dumps({"schema_version": 1, "user_id": 9, "items": []}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "different user"):
                store.load()


class InvoiceDraftResumeTests(unittest.TestCase):
    def setUp(self):
        self.window = InvoiceWindow.__new__(InvoiceWindow)
        self.window.branches = [SimpleNamespace(id=1, name="Tile Index - Korangi")]
        self.window.products = [
            SimpleNamespace(id=20, name="Long Tile Product", tile_size="12x24", pieces_per_box=8)
        ]
        self.window.accessories = []
        self.window.sanitary_products = []
        self.stock = {
            "branches": [{
                "branch_id": 1,
                "branch_name": "Tile Index - Korangi",
                "boxes": 5,
                "loose_pieces": 2,
                "total_pieces": 42,
                "rate_per_box": 2304,
                "rate_per_piece": 288,
                "rate_missing": False,
            }]
        }
        self.window.load_stock_overview_row = lambda *args, **kwargs: self.stock

    @staticmethod
    def saved_tile(**overrides):
        item = {
            "item_type": "tile",
            "product_id": 20,
            "source_branch_id": 1,
            "grade": "G1 Prime",
            "boxes": 1,
            "loose_pieces": 2,
            "quantity": 0,
            "display_label": "Long Tile Product",
            "rate_per_box": 1,
            "rate_per_piece": 1,
            "line_total": 3,
        }
        item.update(overrides)
        return item

    def test_resume_uses_current_pricing_not_saved_reference_rates(self):
        item = self.window._rebuild_draft_item(self.saved_tile())
        self.assertNotIn("draft_error", item)
        self.assertEqual(item["rate_per_box"], 2304)
        self.assertEqual(item["rate_per_piece"], 288)
        self.assertEqual(item["line_total"], 2880)

    def test_resume_flags_insufficient_current_stock(self):
        item = self.window._rebuild_draft_item(self.saved_tile(boxes=6, loose_pieces=0))
        self.assertIn("Insufficient stock", item["draft_error"])

    def test_resume_flags_deleted_product(self):
        self.window.products = []
        item = self.window._rebuild_draft_item(self.saved_tile())
        self.assertIn("deleted", item["draft_error"])

    def test_resume_flags_missing_rate(self):
        self.stock["branches"][0]["rate_missing"] = True
        item = self.window._rebuild_draft_item(self.saved_tile())
        self.assertEqual(item["draft_error"], "No rate set for this size and grade")

    def test_repeated_lines_cannot_exceed_stock_together(self):
        first = self.window._rebuild_draft_item(self.saved_tile(boxes=3, loose_pieces=0))
        second = self.window._rebuild_draft_item(self.saved_tile(boxes=3, loose_pieces=0))
        items = self.window._flag_combined_draft_shortages([first, second])
        self.assertNotIn("draft_error", items[0])
        self.assertIn("Combined draft quantity exceeds", items[1]["draft_error"])

    @patch("ui.invoice_window.InvoicePrintWindow")
    @patch("ui.invoice_window.tk.Toplevel", return_value=object())
    @patch("ui.invoice_window.messagebox.showinfo")
    @patch("ui.invoice_window.InvoiceService.create_invoice")
    @patch("services.auth_service.AuthenticationService.can_access_branch", return_value=True)
    def test_successful_resumed_invoice_deletes_draft(
        self, _can_access, create_invoice, _showinfo, _toplevel, _print_window
    ):
        entry = lambda value: SimpleNamespace(get=lambda: value)
        self.window.current_user = SimpleNamespace(id=3)
        self.window.selected_branch_id = 1
        self.window.customer_name_entry = entry("Customer")
        self.window.customer_contact_entry = entry("")
        self.window.remarks_text = SimpleNamespace(get=lambda *_args: "")
        self.window.discount_entry = entry("0")
        self.window.paid_entry = entry("0")
        self.window.invoice_items = [self.window._rebuild_draft_item(self.saved_tile())]
        self.window.resumed_from_draft = True
        self.window.refresh_resumed_draft_lines = lambda show_result=False: []
        self.window.parent = object()
        self.window.draft_store = SimpleNamespace(delete=Mock())
        self.window.clear_invoice = Mock()
        create_invoice.return_value = SimpleNamespace(id=91, invoice_number="TIK-0091")

        self.window.generate_invoice()

        self.window.draft_store.delete.assert_called_once_with()
        self.window.clear_invoice.assert_called_once_with(prompt_for_saved_draft=False)


if __name__ == "__main__":
    unittest.main()
