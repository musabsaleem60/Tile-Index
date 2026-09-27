import json
import inspect
from pathlib import Path
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from repositories.activity_log_repository import ActivityLogRepository
from utils.activity_log_formatter import (
    activity_category,
    activity_reference,
    activity_summary,
    format_activity_details,
    raw_activity_json,
)
from ui.activity_log_window import ActivityLogWindow, DEFAULT_ACTIONS


class ActivityLogRedesignTests(unittest.TestCase):
    def test_named_activity_routes_precede_numeric_catch_all(self):
        backend_route = Path(__file__).resolve().parents[2] / "backend" / "app" / "api" / "activity_log.py"
        source = backend_route.read_text(encoding="utf-8-sig")
        catch_all = source.index('@router.get("/{activity_id}"')
        for route in ('@router.get("/actions")', '@router.get("/products")', '@router.get("/product-history/{product_id}")'):
            self.assertLess(source.index(route), catch_all, route)

    def test_screen_renders_before_scheduling_network_loads(self):
        source = inspect.getsource(ActivityLogWindow.__init__)
        self.assertLess(source.index("self.setup_ui()"), source.index("self.parent.after(50"))
        self.assertIn("Stock IN", DEFAULT_ACTIONS["Stock"])
        self.assertIn("Login", DEFAULT_ACTIONS["Access"])

    def test_historical_entry_infers_category_and_formats_without_new_fields(self):
        activity = SimpleNamespace(
            action_type="Invoice Remarks Updated",
            action_details=json.dumps({
                "invoice_number": "TIK-0024",
                "old_remarks": "old",
                "new_remarks": "new",
            }),
            event_category=None,
        )
        self.assertEqual(activity_category(activity), "Sales")
        self.assertEqual(activity_reference(activity), "TIK-0024")
        self.assertIn("Remarks updated", activity_summary(activity))
        self.assertIn('"new_remarks": "new"', raw_activity_json(activity))

    def test_stock_summary_keeps_reason_and_dc_out_of_timeline_summary(self):
        activity = SimpleNamespace(
            action_type="Stock OUT",
            action_details=json.dumps({
                "product_name": "DC GP 005 Grey White",
                "tile_size": "12x24",
                "grade": "G1 Prime",
                "boxes": 1,
                "loose_pieces": 2,
                "reason": "damaged pieces",
                "dc_number": "401-5",
            }),
            event_category="Stock",
        )
        full = format_activity_details(activity)
        self.assertEqual(full.count("Reason:"), 1)
        self.assertEqual(full.count("DC#"), 1)
        self.assertNotIn("Reason:", activity_summary(activity))
        self.assertNotIn("DC#", activity_summary(activity))

    def test_new_action_types_are_classified_instead_of_omitted(self):
        cases = {
            "Invoice Exported": "Sales",
            "Return Note Reprinted": "Returns",
            "Accessory Stock Counted": "Stock",
            "Product Renamed": "Catalogue",
        }
        for action, expected in cases.items():
            with self.subTest(action=action):
                self.assertEqual(
                    activity_category(SimpleNamespace(action_type=action, event_category=None)),
                    expected,
                )

    @patch("repositories.activity_log_repository.is_api_authenticated", return_value=True)
    @patch("repositories.activity_log_repository.api_client.get")
    def test_repository_sends_structured_filters(self, get, _authenticated):
        get.return_value = []
        ActivityLogRepository.search(
            view="business", event_category="Sales", product_id=42,
            invoice_number="TIK-1", return_number="RET-1",
        )
        url = get.call_args.args[0]
        self.assertIn("view=business", url)
        self.assertIn("event_category=Sales", url)
        self.assertIn("product_id=42", url)
        self.assertIn("invoice_number=TIK-1", url)
        self.assertIn("return_number=RET-1", url)


if __name__ == "__main__":
    unittest.main()
