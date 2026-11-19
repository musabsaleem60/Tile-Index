import unittest
from types import SimpleNamespace
from unittest.mock import patch

from scripts.import_loose_pcs import _parse
from ui.loose_pcs_window import LoosePcsWindow


class FakeTree:
    def __init__(self):
        self.rows = {}

    def get_children(self):
        return list(self.rows)

    def delete(self, iid):
        del self.rows[iid]

    def insert(self, _parent, _position, iid, values):
        self.rows[iid] = values


class LoosePcsStockTableTests(unittest.TestCase):
    def test_selected_branch_shows_each_product_once_including_real_zeroes(self):
        catalogue, stock = _parse()
        names = ["Tile Index - Korangi", "Tile Cera - Korangi", "Machi Mor", "DHA"]
        branches = [SimpleNamespace(id=index, name=name) for index, name in enumerate(names, 1)]
        products = [
            {"id": index, "sku": f"LPC-{index:06d}", "name": name, "size": size, "price": str(price)}
            for index, ((name, size), price) in enumerate(catalogue.items(), 1)
        ]
        ids = {(product["name"], product["size"]): product["id"] for product in products}
        responses = {"/catalog/loose-pcs": products}
        for branch in branches:
            responses[f"/inventory/loose-pcs/{branch.id}"] = [
                {"product_id": ids[(name, size)], "quantity": quantity}
                for (name, size, branch_name), quantity in stock.items() if branch_name == branch.name
            ]

        window = LoosePcsWindow.__new__(LoosePcsWindow)
        window.branches = branches
        window.tree = FakeTree()
        window.load_status = SimpleNamespace(configure=lambda **_kwargs: None)
        window.branch_var = SimpleNamespace(get=lambda: window.selected_branch)

        with patch("ui.loose_pcs_window.api_client.get", side_effect=responses.get) as get:
            window.selected_branch = "Tile Index - Korangi"
            window.refresh()
            self.assertEqual(len(window.tree.rows), 29)
            ayat_id = ids[("Ayat Tiles", "12x12")]
            self.assertEqual(window.tree.rows[f"{ayat_id}:1"][5], 2)
            self.assertEqual(window.tree.rows[f"{ayat_id}:1"][3], "Rs. 1000.00")

            window.selected_branch = "Tile Cera - Korangi"
            window.refresh()
            self.assertEqual(len(window.tree.rows), 29)
            self.assertEqual(window.tree.rows[f"{ayat_id}:2"][5], 0)
            self.assertEqual(window.tree.rows[f"{ids[('Golden Border Bunty', '2x24')]}:2"][5], 225)

            for branch in branches[2:]:
                window.selected_branch = branch.name
                window.refresh()
                self.assertEqual(len(window.tree.rows), 29)
                self.assertTrue(all(row[5] == 0 for row in window.tree.rows.values()))

            self.assertEqual({call.args[0] for call in get.call_args_list}, {
                "/catalog/loose-pcs", *[f"/inventory/loose-pcs/{branch.id}" for branch in branches],
            })


if __name__ == "__main__":
    unittest.main()
