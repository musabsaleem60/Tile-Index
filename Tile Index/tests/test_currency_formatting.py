import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from utils.activity_log_formatter import format_activity_details
from utils.currency import clamp_currency_zero, format_amount, format_currency, normalize_display_amount
from utils.invoice_printer import InvoicePrintWindow
from ui.invoice_window import InvoiceWindow


class CurrencyFormattingTests(unittest.TestCase):
    def test_sub_cent_positive_and_negative_values_display_as_positive_zero(self):
        for value in (-0.009, -0.0, 0, 0.005, 0.009999):
            with self.subTest(value=value):
                self.assertEqual(normalize_display_amount(value), 0)
                self.assertEqual(format_amount(value), "0.00")
                self.assertEqual(format_currency(value), "Rs. 0.00")

    def test_values_at_or_above_one_paisa_are_not_hidden(self):
        self.assertEqual(format_currency(-0.01), "Rs. -0.01")
        self.assertEqual(format_currency(0.01), "Rs. 0.01")
        self.assertEqual(format_currency(1), "Rs. 1.00")

    def test_invoice_pdf_money_helper_uses_shared_normalization(self):
        self.assertEqual(InvoicePrintWindow.money_text(-0.0000001), "Rs. 0.00")

    def test_exact_paid_balance_residue_is_clamped_for_calculation(self):
        subtotal = 8119.999999999999
        grand_total = subtotal - 120
        self.assertLess(grand_total - 8000, 0)
        self.assertEqual(clamp_currency_zero(grand_total - 8000), 0)
        self.assertAlmostEqual(clamp_currency_zero((subtotal - 100) - 8000), 20.0)

    def test_exact_zero_grand_total_residue_is_clamped(self):
        subtotal = 119.99999999999999
        self.assertEqual(clamp_currency_zero(subtotal - 120), 0)

    def test_activity_log_money_uses_shared_normalization(self):
        activity = type(
            "Activity",
            (),
            {
                "action_type": "Invoice Created",
                "action_details": '{"invoice_number":"TIK-TEST","grand_total":-0.000001}',
            },
        )()
        self.assertIn("Total: Rs. 0.00", format_activity_details(activity))

    @patch("ui.invoice_window.InvoicePrintWindow")
    @patch("ui.invoice_window.tk.Toplevel", return_value=object())
    @patch("ui.invoice_window.messagebox.showinfo")
    @patch("ui.invoice_window.messagebox.showerror")
    @patch("ui.invoice_window.InvoiceService.create_invoice")
    @patch("services.auth_service.AuthenticationService.can_access_branch", return_value=True)
    def test_generate_invoice_allows_true_zero_balance_after_clamp(
        self, _can_access, create_invoice, showerror, _showinfo, _toplevel, _print_window
    ):
        window = self._invoice_window(discount="120", paid="8000")
        create_invoice.return_value = SimpleNamespace(id=72, invoice_number="TIK-TEST")

        window.generate_invoice()

        create_invoice.assert_called_once()
        showerror.assert_not_called()

    @patch("ui.invoice_window.messagebox.showerror")
    @patch("ui.invoice_window.InvoiceService.create_invoice")
    def test_generate_invoice_still_blocks_real_negative_balance(self, create_invoice, showerror):
        window = self._invoice_window(discount="120.02", paid="8000")

        window.generate_invoice()

        create_invoice.assert_not_called()
        self.assertIn("Paid amount exceeds invoice total", showerror.call_args.args[1])

    @staticmethod
    def _invoice_window(discount, paid):
        entry = lambda value: SimpleNamespace(get=lambda: value)
        window = InvoiceWindow.__new__(InvoiceWindow)
        window.resumed_from_draft = False
        window.current_user = SimpleNamespace(id=3)
        window.selected_branch_id = 1
        window.customer_name_entry = entry("Customer")
        window.customer_contact_entry = entry("")
        window.remarks_text = SimpleNamespace(get=lambda *_args: "")
        window.discount_entry = entry(discount)
        window.paid_entry = entry(paid)
        window.invoice_items = [{
            "type": "Tiles",
            "product_id": 1,
            "source_branch_id": 1,
            "grade": "G1 Prime",
            "boxes": 4,
            "loose_pieces": 0,
            "line_total": 8119.999999999999,
        }]
        window.parent = object()
        window.draft_store = SimpleNamespace(delete=Mock())
        window.refresh_draft_button = Mock()
        window.clear_invoice = Mock()
        return window


if __name__ == "__main__":
    unittest.main()
