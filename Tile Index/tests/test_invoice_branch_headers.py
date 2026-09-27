from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from utils.invoice_printer import InvoicePrintWindow


class InvoiceBranchHeaderTests(unittest.TestCase):
    CASES = [
        ("DHA", "Tile Index DHA"),
        ("Tile Index - Korangi", "Tile Index Korangi"),
        ("Tile Cera - Korangi", "Tile Cera"),
        ("Machi Mor", "Machi Mor"),
    ]

    def test_invoice_pdf_uses_one_branch_specific_heading(self):
        contact_lines = InvoicePrintWindow.company_contact_lines()
        self.assertIn("Cell# 03330214142  Qaim", contact_lines)
        self.assertFalse(any("Shafaq" in line or "Anas" in line for line in contact_lines))
        with tempfile.TemporaryDirectory() as temp_dir:
            for branch_id, (branch_name, expected) in enumerate(self.CASES, 1):
                with self.subTest(branch=branch_name):
                    printer = InvoicePrintWindow.__new__(InvoicePrintWindow)
                    printer.branch = SimpleNamespace(id=branch_id, name=branch_name)
                    printer.branches = {branch_id: printer.branch}
                    printer.products = {}
                    printer.accessories = {}
                    printer.sanitary_products = {}
                    printer.payments = []
                    printer.invoice = SimpleNamespace(
                        id=branch_id, branch_id=branch_id, invoice_number=f"TEST-{branch_id}",
                        invoice_date=datetime(2026, 9, 25, 12, 0),
                        customer_name="PDF Test Customer", customer_contact=None,
                        subtotal=0, discount=0, grand_total=0, paid_amount=0, balance=0,
                        status="active", void_reason=None, remarks=None, items=[],
                    )
                    printer.invoice_pdf_dir = lambda: temp_dir
                    self.assertEqual(printer.company_heading(), expected)
                    path = Path(printer.generate_invoice_pdf())
                    self.assertTrue(path.is_file())
                    self.assertGreater(path.stat().st_size, 1_000)


if __name__ == "__main__":
    unittest.main()
