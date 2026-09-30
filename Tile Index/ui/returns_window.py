import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

import customtkinter as ctk

from repositories.branch_repository import BranchRepository
from services.auth_service import AuthenticationService
from services.invoice_service import InvoiceService
from ui.theme import COLORS, FONTS, SIZES, SPACING
from utils.datetime_format import format_business_datetime
from utils.currency import clamp_currency_zero, format_amount, format_currency
from utils.return_printer import ReturnPrinter
from utils.searchable_combobox import SearchableCombobox


class ReturnsWindow:
    """Search, inspect, print, and settle return/exchange records."""

    def __init__(self, parent, current_user):
        self.parent = parent
        self.current_user = current_user
        self.branches = BranchRepository.get_all()
        self.branch_scoped_employee = (
            AuthenticationService.is_employee(current_user) and current_user.branch_id is not None
        )
        self.return_ids = {}
        self._build()
        self.parent.after_idle(self.search)

    def _build(self):
        ctk.CTkLabel(
            self.parent, text="Returns", font=FONTS["section"], fg_color=COLORS["surface"],
            text_color=COLORS["text"], height=48,
        ).pack(fill=tk.X)
        page = ctk.CTkFrame(self.parent, fg_color=COLORS["app_bg"], corner_radius=0)
        page.pack(fill=tk.BOTH, expand=True, padx=SPACING["page_x"], pady=SPACING["page_y"])

        filters = self._panel(page, "Search Criteria")
        filters.pack(fill=tk.X, pady=(0, 12))
        self.branch_var = tk.StringVar()
        options = [b.name for b in self.branches]
        if not self.branch_scoped_employee:
            options.insert(0, "All Branches")
        self._label(filters, "Branch:").grid(row=1, column=0, padx=8, pady=5, sticky=tk.W)
        self.branch_combo = SearchableCombobox(filters, textvariable=self.branch_var, width=22, font=FONTS["small"])
        self.branch_combo.set_completion_list(options)
        self.branch_combo.grid(row=1, column=1, padx=8, pady=5, sticky=tk.W)
        if self.branch_scoped_employee and self.branches:
            self.branch_var.set(self.branches[0].name)
            self.branch_combo.configure(state="disabled")
        self.return_number = self._field(filters, "Return Number:", 1, 2)
        self.invoice_number = self._field(filters, "Original Invoice:", 1, 4)
        self.date_from = self._field(filters, "Date From:", 2, 0)
        self.date_to = self._field(filters, "Date To:", 2, 2)
        # Blank dates intentionally mean all history. A today-only default
        # made existing returns look as though they did not exist.
        self._button(filters, "Search", self.search, 130).grid(row=2, column=4, columnspan=2, padx=8, pady=8)

        results = self._panel(page, "Return Results")
        results.pack(fill=tk.BOTH, expand=True, pady=(0, 12))
        results.grid_rowconfigure(1, weight=1)
        results.grid_columnconfigure(0, weight=1)
        columns = ("Return Number", "Date", "Original Invoice", "Branch", "Customer", "Returned", "Exchange", "Difference", "Settlement")
        self.tree = ttk.Treeview(results, columns=columns, show="headings", height=12)
        widths = (120, 110, 125, 150, 160, 100, 100, 100, 105)
        for column, width in zip(columns, widths):
            self.tree.heading(column, text=column)
            self.tree.column(column, width=width, minwidth=width, anchor=tk.CENTER, stretch=False)
        self.tree.grid(row=1, column=0, sticky=tk.NSEW, padx=(12, 0), pady=(0, 12))
        ttk.Scrollbar(results, orient=tk.VERTICAL, command=self.tree.yview).grid(row=1, column=1, sticky=tk.NS, padx=(0, 12), pady=(0, 12))
        self.tree.bind("<<TreeviewSelect>>", self.load_detail)

        detail = self._panel(page, "Return Details")
        detail.pack(fill=tk.X, pady=(0, 10))
        self.detail_text = ctk.CTkTextbox(
            detail, height=160, font=FONTS["small"], fg_color=COLORS["app_bg"],
            border_color=COLORS["border"], border_width=1, text_color=COLORS["text"]
        )
        self.detail_text.grid(row=1, column=0, columnspan=4, sticky=tk.EW, padx=12, pady=(0, 8))
        self.detail_text.configure(state="disabled")
        actions = ctk.CTkFrame(page, fg_color="transparent")
        actions.pack()
        self._button(actions, "View / Print Return Note", self.print_return, 210).pack(side=tk.LEFT, padx=6)
        self.settle_button = self._button(actions, "Record Settlement", self.record_settlement, 180)
        self.settle_button.pack(side=tk.LEFT, padx=6)
        self.current_return = None

    def _panel(self, parent, title):
        panel = ctk.CTkFrame(parent, fg_color=COLORS["surface"], corner_radius=SIZES["corner_radius"], border_width=1, border_color=COLORS["border"])
        ctk.CTkLabel(panel, text=title, font=FONTS["body_bold"], text_color=COLORS["text"], height=SIZES["section_label_height"]).grid(row=0, column=0, columnspan=6, sticky=tk.EW, padx=12, pady=(10, 8))
        return panel

    def _label(self, parent, text):
        return ctk.CTkLabel(parent, text=text, font=FONTS["small"], text_color=COLORS["text"], height=SIZES["small_label_height"])

    def _entry(self, parent, width=180):
        return ctk.CTkEntry(parent, width=width, height=SIZES["input_height"], font=FONTS["small"], fg_color=COLORS["app_bg"], border_color=COLORS["border"], text_color=COLORS["text"])

    def _field(self, parent, label, row, column):
        self._label(parent, label).grid(row=row, column=column, padx=8, pady=5, sticky=tk.W)
        entry = self._entry(parent)
        entry.grid(row=row, column=column + 1, padx=8, pady=5, sticky=tk.W)
        return entry

    def _button(self, parent, text, command, width):
        return ctk.CTkButton(parent, text=text, command=command, width=width, height=34, fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"], text_color=COLORS["text"], font=FONTS["small_bold"], corner_radius=SIZES["corner_radius"])

    def _branch_id(self):
        selected = self.branch_var.get()
        return next((b.id for b in self.branches if b.name == selected), None)

    def search(self):
        try:
            rows = InvoiceService.search_returns(
                branch_id=self._branch_id(), date_from=self.date_from.get().strip(), date_to=self.date_to.get().strip(),
                return_number=self.return_number.get().strip(), invoice_number=self.invoice_number.get().strip(),
            )
            self.return_ids.clear()
            for item in self.tree.get_children():
                self.tree.delete(item)
            for row in rows:
                item = self.tree.insert("", tk.END, values=(
                    row["return_number"], format_business_datetime(row["return_date"], fmt="%Y-%m-%d"),
                    row["invoice_number"], row["branch_name"], row["customer_name"],
                    format_currency(row['returned_value']), format_currency(row['exchange_value']),
                    format_currency(row['difference_amount']), row["settlement_status"],
                ))
                self.return_ids[item] = (row["id"], row["invoice_id"])
            if not rows:
                messagebox.showinfo("Returns", "No returns found matching the criteria.")
        except Exception as exc:
            messagebox.showerror("Returns", f"Search failed: {exc}")

    def _selected_ids(self):
        selection = self.tree.selection()
        return self.return_ids.get(selection[0]) if selection else None

    def load_detail(self, _event=None):
        ids = self._selected_ids()
        if not ids:
            return
        try:
            self.current_return = InvoiceService.get_return(ids[0])
            invoice = InvoiceService.get_invoice(ids[1])
            invoice_items = {item.id: item for item in invoice.items}
            branch_names = {branch.id: branch.name for branch in self.branches}
            lines = [
                f"Return: {self.current_return['return_number']} | Reason: {self.current_return['reason']}",
                f"Returned value: {format_currency(self.current_return['returned_value'])} | Exchange value: {format_currency(self.current_return['exchange_value'])}",
                f"Difference: {format_currency(self.current_return['difference_amount'])} | Outstanding: {format_currency(self.current_return['outstanding_amount'])}",
                "", "Returned items:",
            ]
            lines.extend(self._return_item_lines(self.current_return.get("return_items", []), invoice_items, branch_names))
            lines.append("\nExchange items:")
            lines.extend(self._exchange_item_lines(self.current_return.get("exchange_items", []), branch_names))
            lines.append("\nSettlements:")
            lines.extend(self._settlement_lines(self.current_return.get("settlements", [])))
            self.detail_text.configure(state="normal")
            self.detail_text.delete("1.0", tk.END)
            self.detail_text.insert("1.0", "\n".join(lines))
            self.detail_text.configure(state="disabled")
            outstanding = clamp_currency_zero(self.current_return["outstanding_amount"])
            self.settle_button.configure(state=tk.NORMAL if outstanding > 0 else tk.DISABLED)
        except Exception as exc:
            messagebox.showerror("Return Details", str(exc))

    @staticmethod
    def _return_item_lines(rows, invoice_items, branch_names):
        result = []
        for row in rows:
            item = invoice_items.get(row["invoice_item_id"])
            label = getattr(item, "description", None) or f"Invoice item {row['invoice_item_id']}"
            source = branch_names.get(row["source_branch_id"], f"Branch {row['source_branch_id']}")
            result.append(f"{label} | Source: {source} | {row['boxes']} boxes + {row['loose_pieces']} loose | {row['quantity']} units | {format_currency(row['discounted_line_total'])}")
        return result or ["None"]

    @staticmethod
    def _exchange_item_lines(rows, branch_names):
        return [f"{r['description']} | Source: {branch_names.get(r['source_branch_id'], r['source_branch_id'])} | {r['boxes']} boxes + {r['loose_pieces']} loose | {r['quantity']} units | {format_currency(r['line_total'])}" for r in rows] or ["None"]

    @staticmethod
    def _settlement_lines(rows):
        return [f"{format_business_datetime(r['settlement_date'], fmt='%Y-%m-%d')} | {r['direction']} | {format_currency(r['amount'])} | {r.get('method') or '-'}" for r in rows] or ["None"]

    def print_return(self):
        ids = self._selected_ids()
        if not ids:
            messagebox.showwarning("Returns", "Please select a return.")
            return
        try:
            record = self.current_return if self.current_return and self.current_return["id"] == ids[0] else InvoiceService.get_return(ids[0])
            invoice = InvoiceService.get_invoice(ids[1])
            path = ReturnPrinter(invoice, record).generate_pdf()
            ReturnPrinter.open_pdf(path)
        except Exception as exc:
            messagebox.showerror("Return Note", str(exc))

    def record_settlement(self):
        ids = self._selected_ids()
        if not ids or not self.current_return:
            messagebox.showwarning("Returns", "Please select a return.")
            return
        outstanding = clamp_currency_zero(self.current_return["outstanding_amount"])
        dialog = ctk.CTkToplevel(self.parent)
        dialog.title("Record Return Settlement")
        dialog.geometry("430x300")
        dialog.configure(fg_color=COLORS["app_bg"])
        dialog.transient(self.parent.winfo_toplevel())
        amount = self._entry(dialog, 180)
        method = tk.StringVar(value="cash")
        self._label(dialog, f"Outstanding: {format_currency(outstanding)}").pack(pady=(22, 8))
        amount.pack(pady=6)
        amount.insert(0, format_amount(outstanding))
        ttk.Combobox(dialog, textvariable=method, values=("cash", "card", "bank", "other"), state="readonly", width=18).pack(pady=6)

        def save():
            try:
                value = float(amount.get())
                if value <= 0 or clamp_currency_zero(outstanding - value) < 0:
                    raise ValueError("Settlement amount must be positive and cannot exceed the outstanding amount")
                InvoiceService.add_return_settlement(ids[0], {
                    "amount": value, "direction": self.current_return["difference_direction"],
                    "settlement_date": datetime.now().astimezone().isoformat(), "method": method.get(), "notes": None,
                })
                dialog.destroy()
                self.load_detail()
                self.search()
            except Exception as exc:
                messagebox.showerror("Settlement Failed", str(exc), parent=dialog)

        self._button(dialog, "Save Settlement", save, 170).pack(pady=14)
