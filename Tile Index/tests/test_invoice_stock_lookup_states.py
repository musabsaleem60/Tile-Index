import unittest
from types import SimpleNamespace
from unittest.mock import patch

from desktop_client.api_client import ApiClientError
from ui.invoice_window import InvoiceWindow
from ui.theme import COLORS


class FakeVar:
    def __init__(self, value=""):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class FakeWidget:
    def __init__(self):
        self.options = {}
        self.values = []

    def configure(self, **kwargs):
        self.options.update(kwargs)

    def __setitem__(self, key, value):
        if key == "values":
            self.values = list(value)
        else:
            self.options[key] = value


class InvoiceStockLookupStateTests(unittest.TestCase):
    def setUp(self):
        self.window = InvoiceWindow.__new__(InvoiceWindow)
        self.window.products = [SimpleNamespace(id=10, name="Test Tile", tile_size="12x24")]
        self.window.accessories = []
        self.window.sanitary_products = []
        self.window.branches = [SimpleNamespace(id=1, name="Tile Index - Korangi")]
        self.window.selected_branch_id = 1
        self.window.item_type_var = FakeVar("Tiles")
        self.window.product_var = FakeVar("Test Tile - 12x24")
        self.window.grade_var = FakeVar("G1 Prime")
        self.window.source_branch_var = FakeVar("Tile Index - Korangi")
        self.window.source_branch_options = []
        self.window.current_stock_overview_row = None
        self.window.stock_lookup_confirmed = False
        self.window.source_branch_combo = FakeWidget()
        self.window.add_item_button = FakeWidget()
        self.window.stock_info_label = FakeWidget()

    @staticmethod
    def stock_row(boxes):
        return {
            "total_pieces": boxes * 8,
            "branches": [{
                "branch_id": 1,
                "branch_name": "Tile Index - Korangi",
                "boxes": boxes,
                "loose_pieces": 0,
                "total_pieces": boxes * 8,
                "rate_missing": False,
                "rate_per_box": 2304.0,
                "rate_per_piece": 288.0,
            }],
        }

    def test_successful_positive_stock_is_displayed_and_controls_enabled(self):
        self.window.load_stock_overview_row = lambda *args, **kwargs: self.stock_row(6)

        self.window.update_stock_info()

        self.assertTrue(self.window.stock_lookup_confirmed)
        self.assertIn("6 boxes + 0 loose", self.window.stock_info_label.options["text"])
        self.assertEqual(self.window.source_branch_combo.options["state"], "readonly")
        self.assertEqual(self.window.add_item_button.options["state"], "normal")

    def test_successful_zero_stock_is_not_reported_as_connection_failure(self):
        self.window.load_stock_overview_row = lambda *args, **kwargs: self.stock_row(0)

        self.window.update_stock_info()

        self.assertTrue(self.window.stock_lookup_confirmed)
        self.assertEqual(self.window.stock_info_label.options["text"], "No stock available for this grade")
        self.assertEqual(self.window.stock_info_label.options["text_color"], COLORS["danger"])
        self.assertEqual(self.window.add_item_button.options["state"], "normal")

    def test_failed_lookup_blocks_line_until_successful_retry(self):
        self.window.load_stock_overview_row = lambda *args, **kwargs: (_ for _ in ()).throw(
            ApiClientError("connection timed out")
        )

        with self.assertLogs("ui.invoice_window", level="WARNING") as logs:
            self.window.update_stock_info()

        self.assertFalse(self.window.stock_lookup_confirmed)
        self.assertIn("Could not check stock", self.window.stock_info_label.options["text"])
        self.assertEqual(self.window.stock_info_label.options["text_color"], COLORS["warning"])
        self.assertEqual(self.window.source_branch_combo.options["state"], "disabled")
        self.assertEqual(self.window.add_item_button.options["state"], "disabled")
        self.assertTrue(any("connection timed out" in line for line in logs.output))

        self.window.load_stock_overview_row = lambda *args, **kwargs: self.stock_row(2)
        self.window.update_stock_info()

        self.assertTrue(self.window.stock_lookup_confirmed)
        self.assertEqual(self.window.source_branch_combo.options["state"], "readonly")
        self.assertEqual(self.window.add_item_button.options["state"], "normal")

    def test_stock_loader_propagates_api_errors(self):
        with patch("ui.invoice_window.api_client.get", side_effect=ApiClientError("offline")):
            with self.assertRaisesRegex(ApiClientError, "offline"):
                self.window.load_stock_overview_row("tiles", 10, "G1 Prime")


if __name__ == "__main__":
    unittest.main()
