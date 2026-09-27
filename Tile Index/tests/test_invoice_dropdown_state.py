import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from ui.invoice_window import InvoiceWindow


class Variable:
    def __init__(self, value=""):
        self.value = value
    def get(self): return self.value
    def set(self, value): self.value = value


class Widget:
    def __init__(self):
        self.values = []
    def configure(self, **_kwargs): pass
    def __setitem__(self, key, value):
        if key == "values": self.values = list(value)
    def grid(self): pass
    def grid_remove(self): pass
    def set_completion_list(self, values): self.values = list(values)


class InvoiceDropdownStateTests(unittest.TestCase):
    def setUp(self):
        self.window = InvoiceWindow.__new__(InvoiceWindow)
        self.window.products = [SimpleNamespace(name="Tile One", tile_size="10x20")]
        self.window.accessories = [SimpleNamespace(
            company="Shabir", colour="White", product_name=None, size=None,
            category="Grout", name="Shabir - White",
        )]
        self.window.sanitary_products = [SimpleNamespace(
            company_name="Heritage", product_category="Basin", color="White", sku="SAN-1",
        )]
        self.window.item_type_var = Variable("Tiles")
        self.window.product_var = Variable()
        self.window.source_branch_var = Variable()
        for name in (
            "product_label", "product_combo", "grade_label", "grade_combo",
            "source_branch_label", "source_branch_combo", "boxes_label",
            "pieces_label", "item_pieces_entry",
        ):
            setattr(self.window, name, Widget())
        self.window.update_stock_info = Mock()

    def test_ten_rapid_item_type_switches_keep_each_catalogue_populated(self):
        expected = {"Tiles": "Tile One - 10x20", "Accessories": "Grout - Shabir - White", "Sanitary": "Heritage - Basin - White"}
        sequence = ["Sanitary", "Tiles", "Accessories", "Tiles", "Sanitary"] * 2
        for item_type in sequence:
            self.window.item_type_var.set(item_type)
            self.window.on_item_type_change(None)
            self.assertIn(expected[item_type], self.window.product_combo.values)

    def test_new_product_defaults_source_to_invoice_branch_but_override_is_preserved(self):
        self.window.invoice_branch_name = lambda: "Machi Mor"
        observed = []
        self.window.update_stock_info = lambda: observed.append(self.window.source_branch_var.get())
        self.window.on_product_select(None)
        self.assertEqual(observed, ["Machi Mor"])

        self.window.source_branch_options = []
        self.window.source_branch_var.set("DHA")
        self.window.branches = [SimpleNamespace(id=1, name="Machi Mor")]
        self.window.selected_branch_id = 1
        InvoiceWindow.update_source_branch_options(self.window, {
            "branches": [
                {"branch_id": 1, "branch_name": "Machi Mor"},
                {"branch_id": 4, "branch_name": "DHA"},
            ]
        })
        self.assertEqual(self.window.source_branch_var.get(), "DHA")


if __name__ == "__main__":
    unittest.main()
