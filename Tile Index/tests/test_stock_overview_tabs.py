import unittest
from types import SimpleNamespace
from unittest.mock import patch

from ui.stock_overview_window import StockOverviewWindow


class StockOverviewTabTests(unittest.TestCase):
    def test_each_tab_switch_reconfigures_and_refreshes_live_data(self):
        calls = []
        window = SimpleNamespace(
            active_tab=None,
            configure_for_tab=lambda: calls.append(("configure", window.active_tab)),
            refresh_data=lambda: calls.append(("refresh", window.active_tab)),
        )

        for label, item_type in (
            ("Accessories", "accessories"),
            ("Sanitary", "sanitary"),
            ("Tiles", "tiles"),
        ):
            calls.clear()
            StockOverviewWindow.on_tab_change(window, label)
            self.assertEqual(window.active_tab, item_type)
            self.assertEqual(calls, [("configure", item_type), ("refresh", item_type)])

    @patch("ui.stock_overview_window.api_client.get")
    def test_default_and_show_all_counts_follow_active_tab(self, get):
        def response(url):
            include_zero = "include_zero=true" in url
            if "item_type=accessories" in url:
                count = 84 if include_zero else 39
                return {"branches": [], "tiles": [], "accessories": [{"id": n} for n in range(count)], "sanitary": []}
            if "item_type=sanitary" in url:
                count = 214 if include_zero else 110
                return {"branches": [], "tiles": [], "accessories": [], "sanitary": [{"id": n} for n in range(count)]}
            count = 10 if include_zero else 5
            return {"branches": [], "tiles": [{"id": n} for n in range(count)], "accessories": [], "sanitary": []}

        get.side_effect = response
        show_all = SimpleNamespace(value=False, get=lambda: show_all.value)
        window = SimpleNamespace(
            active_tab="accessories",
            show_all_var=show_all,
            search_var=SimpleNamespace(get=lambda: ""),
            grade_var=SimpleNamespace(get=lambda: "All"),
            category_var=SimpleNamespace(get=lambda: "All"),
            selected_branch_id=lambda: None,
            update_branch_filter=lambda: None,
            populate_table=lambda: None,
            branches=[], tiles=[], accessories=[], sanitary=[],
        )

        StockOverviewWindow.refresh_data(window)
        self.assertEqual(len(window.accessories), 39)
        window.active_tab = "sanitary"
        StockOverviewWindow.refresh_data(window)
        self.assertEqual(len(window.sanitary), 110)
        window.active_tab = "tiles"
        StockOverviewWindow.refresh_data(window)
        self.assertEqual(len(window.tiles), 5)

        show_all.value = True
        window.active_tab = "accessories"
        StockOverviewWindow.refresh_data(window)
        self.assertEqual(len(window.accessories), 84)
        window.active_tab = "sanitary"
        StockOverviewWindow.refresh_data(window)
        self.assertEqual(len(window.sanitary), 214)
        window.active_tab = "tiles"
        StockOverviewWindow.refresh_data(window)
        self.assertEqual(len(window.tiles), 10)


if __name__ == "__main__":
    unittest.main()
