import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime

import customtkinter as ctk

from desktop_client.session import api_client
from services.invoice_service import InvoiceService
from repositories.product_repository import ProductRepository
from ui.theme import COLORS, FONTS, SIZES
from utils.return_printer import ReturnPrinter


class InvoiceReturnDialog:
    """Create a partial return with optional replacement items."""

    def __init__(self, parent, invoice, on_complete=None):
        self.invoice = invoice
        self.on_complete = on_complete
        self.history = InvoiceService.get_returns(invoice.id)
        self.return_inputs = {}
        self.exchange_rows = []
        self.catalog_rows = []
        self.branch_rows = []

        self.window = ctk.CTkToplevel(parent)
        self.window.title(f"Return / Exchange - {invoice.invoice_number}")
        self.window.geometry("1120x760")
        self.window.minsize(980, 680)
        self.window.transient(parent.winfo_toplevel())
        self._build()

    def _build(self):
        page = ctk.CTkScrollableFrame(self.window, fg_color=COLORS["app_bg"])
        page.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        ctk.CTkLabel(page, text=f"Return / Exchange - {self.invoice.invoice_number}", font=FONTS["section"], text_color=COLORS["text"]).pack(anchor=tk.W, pady=(0, 10))

        returned = self._panel(page, "Items Being Returned")
        returned.pack(fill=tk.X, pady=(0, 10))
        headers = ("Item", "Sold", "Returned", "Remaining", "Return Boxes", "Return Loose/Qty")
        for col, text in enumerate(headers):
            ctk.CTkLabel(returned, text=text, font=FONTS["small_bold"], text_color=COLORS["text"]).grid(row=1, column=col, padx=5, pady=5, sticky=tk.W)
        remaining = self.history.get("remaining_by_item", {})
        for row_index, item in enumerate(self.invoice.items, start=2):
            state = remaining.get(str(item.id), remaining.get(item.id, {}))
            sold = int(state.get("sold_quantity", item.quantity or (item.boxes + item.loose_pieces)))
            prior = int(state.get("returned_quantity", 0))
            left = int(state.get("remaining_quantity", sold - prior))
            label = item.description or f"Item {item.id}"
            values = (label, sold, prior, left)
            for col, value in enumerate(values):
                ctk.CTkLabel(returned, text=str(value), font=FONTS["small"], text_color=COLORS["text"]).grid(row=row_index, column=col, padx=5, pady=4, sticky=tk.W)
            boxes = ctk.CTkEntry(returned, width=90, font=FONTS["small"])
            loose = ctk.CTkEntry(returned, width=110, font=FONTS["small"])
            boxes.insert(0, "0")
            loose.insert(0, "0")
            boxes.grid(row=row_index, column=4, padx=5, pady=4)
            loose.grid(row=row_index, column=5, padx=5, pady=4)
            boxes.bind("<KeyRelease>", lambda _e: self._update_totals())
            loose.bind("<KeyRelease>", lambda _e: self._update_totals())
            if item.item_type != "tile":
                boxes.configure(state="disabled")
            self.return_inputs[item.id] = (item, boxes, loose)

        exchange = self._panel(page, "Optional Exchange Items")
        exchange.pack(fill=tk.X, pady=(0, 10))
        self.exchange_type = tk.StringVar(value="tile")
        type_combo = ttk.Combobox(exchange, textvariable=self.exchange_type, values=("tile", "accessory", "sanitary"), state="readonly", width=14)
        type_combo.grid(row=1, column=0, padx=6, pady=6)
        type_combo.bind("<<ComboboxSelected>>", lambda _e: self._load_exchange_catalog())
        self.exchange_product = tk.StringVar()
        self.product_combo = ttk.Combobox(exchange, textvariable=self.exchange_product, state="readonly", width=46)
        self.product_combo.grid(row=1, column=1, padx=6, pady=6)
        self.product_combo.bind("<<ComboboxSelected>>", lambda _e: self._select_exchange_product())
        self.exchange_branch = tk.StringVar()
        self.branch_combo = ttk.Combobox(exchange, textvariable=self.exchange_branch, state="readonly", width=24)
        self.branch_combo.grid(row=1, column=2, padx=6, pady=6)
        self.exchange_boxes = self._entry(exchange, "0", 80, 1, 3)
        self.exchange_loose = self._entry(exchange, "0", 80, 1, 4)
        ctk.CTkButton(exchange, text="Add Exchange Item", command=self._add_exchange, width=150).grid(row=1, column=5, padx=6, pady=6)
        ctk.CTkLabel(exchange, text="Product", font=FONTS["small"], text_color=COLORS["text_muted"]).grid(row=2, column=1)
        ctk.CTkLabel(exchange, text="Source Branch", font=FONTS["small"], text_color=COLORS["text_muted"]).grid(row=2, column=2)
        ctk.CTkLabel(exchange, text="Boxes", font=FONTS["small"], text_color=COLORS["text_muted"]).grid(row=2, column=3)
        ctk.CTkLabel(exchange, text="Loose / Qty", font=FONTS["small"], text_color=COLORS["text_muted"]).grid(row=2, column=4)
        self.exchange_tree = ttk.Treeview(exchange, columns=("item", "branch", "qty", "value"), show="headings", height=4)
        for col, width in (("item", 430), ("branch", 220), ("qty", 140), ("value", 130)):
            self.exchange_tree.heading(col, text=col.title())
            self.exchange_tree.column(col, width=width)
        self.exchange_tree.grid(row=3, column=0, columnspan=6, padx=6, pady=6, sticky=tk.EW)
        ctk.CTkButton(exchange, text="Remove Selected", command=self._remove_exchange, width=140, fg_color=COLORS["surface_alt"]).grid(row=4, column=5, padx=6, pady=(0, 6))

        settlement = self._panel(page, "Settlement and Reason")
        settlement.pack(fill=tk.X, pady=(0, 10))
        self.reason = ctk.CTkEntry(settlement, width=420, placeholder_text="Reason (minimum 5 characters)")
        self.reason.grid(row=1, column=0, columnspan=2, padx=8, pady=6, sticky=tk.W)
        self.settlement_amount = self._entry(settlement, "0", 130, 2, 0)
        self.settlement_method = tk.StringVar(value="cash")
        ttk.Combobox(settlement, textvariable=self.settlement_method, values=("cash", "card", "bank", "other"), state="readonly", width=16).grid(row=2, column=1, padx=8, pady=6)
        ctk.CTkLabel(settlement, text="Settlement amount", font=FONTS["small"], text_color=COLORS["text_muted"]).grid(row=3, column=0)
        ctk.CTkLabel(settlement, text="Method", font=FONTS["small"], text_color=COLORS["text_muted"]).grid(row=3, column=1)
        self.totals_label = ctk.CTkLabel(settlement, text="", font=FONTS["body_bold"], text_color=COLORS["primary"], justify=tk.LEFT)
        self.totals_label.grid(row=1, column=2, rowspan=3, padx=18, pady=6, sticky=tk.W)

        self.history_label = ctk.CTkLabel(page, text=self._history_text(), font=FONTS["small"], text_color=COLORS["text_muted"], justify=tk.LEFT)
        self.history_label.pack(anchor=tk.W, pady=4)
        buttons = ctk.CTkFrame(page, fg_color="transparent")
        buttons.pack(fill=tk.X, pady=8)
        ctk.CTkButton(buttons, text="Process Return / Exchange", command=self._submit, width=220).pack(side=tk.RIGHT, padx=5)
        ctk.CTkButton(buttons, text="Cancel", command=self.window.destroy, width=100, fg_color=COLORS["surface_alt"]).pack(side=tk.RIGHT, padx=5)
        self._load_exchange_catalog()
        self._update_totals()

    def _panel(self, parent, title):
        frame = ctk.CTkFrame(parent, fg_color=COLORS["surface"], border_width=1, border_color=COLORS["border"], corner_radius=SIZES["corner_radius"])
        ctk.CTkLabel(frame, text=title, font=FONTS["body_bold"], text_color=COLORS["text"]).grid(row=0, column=0, columnspan=6, padx=10, pady=(8, 4), sticky=tk.W)
        return frame

    def _entry(self, parent, default, width, row, column):
        entry = ctk.CTkEntry(parent, width=width, font=FONTS["small"])
        entry.insert(0, default)
        entry.grid(row=row, column=column, padx=6, pady=6)
        return entry

    def _load_exchange_catalog(self):
        try:
            kind = self.exchange_type.get()
            plural = {"tile": "tiles", "accessory": "accessories", "sanitary": "sanitary"}[kind]
            data = api_client.get(f"/stock/overview?item_type={plural}&include_zero=false")
            self.catalog_rows = data.get("rows", [])
            labels = []
            for row in self.catalog_rows:
                label = row.get("product", "")
                if kind == "tile":
                    label += f" - {row.get('size')} - {row.get('grade')}"
                labels.append(label)
                row["_label"] = label
            self.product_combo["values"] = labels
            self.exchange_product.set(labels[0] if labels else "")
            self._select_exchange_product()
        except Exception as exc:
            messagebox.showerror("Exchange Items", f"Could not load stock: {exc}", parent=self.window)

    def _select_exchange_product(self):
        row = next((r for r in self.catalog_rows if r.get("_label") == self.exchange_product.get()), None)
        self.branch_rows = [b for b in (row or {}).get("branches", []) if b.get("total_pieces", b.get("quantity", 0)) > 0]
        names = [b["branch_name"] for b in self.branch_rows]
        self.branch_combo["values"] = names
        self.exchange_branch.set(names[0] if names else "")

    def _add_exchange(self):
        row = next((r for r in self.catalog_rows if r.get("_label") == self.exchange_product.get()), None)
        branch = next((b for b in self.branch_rows if b.get("branch_name") == self.exchange_branch.get()), None)
        if not row or not branch:
            messagebox.showerror("Exchange Item", "Select an item and source branch.", parent=self.window)
            return
        try:
            boxes = int(self.exchange_boxes.get() or 0)
            loose = int(self.exchange_loose.get() or 0)
        except ValueError:
            messagebox.showerror("Exchange Item", "Quantities must be whole numbers.", parent=self.window)
            return
        kind = self.exchange_type.get()
        quantity = loose if kind != "tile" else 0
        if boxes < 0 or loose < 0 or (boxes == 0 and loose == 0):
            messagebox.showerror("Exchange Item", "Enter a positive exchange quantity.", parent=self.window)
            return
        payload = {"item_type": kind, "source_branch_id": branch["branch_id"], "boxes": boxes if kind == "tile" else quantity, "loose_pieces": loose if kind == "tile" else 0, "quantity": quantity}
        if kind == "tile":
            payload.update(product_id=row["product_id"], grade=row["grade"])
            value = boxes * float(row.get("rate_per_box") or 0) + loose * float(row.get("rate_per_piece") or 0)
            qty_text = f"{boxes} boxes + {loose} loose"
        elif kind == "accessory":
            payload["accessory_id"] = row["accessory_id"]
            value = quantity * float(row.get("unit_price") or 0)
            qty_text = f"{quantity} units"
        else:
            payload["sanitary_product_id"] = row["sanitary_product_id"]
            value = quantity * float(row.get("unit_price") or 0)
            qty_text = f"{quantity} units"
        self.exchange_rows.append(payload)
        item_id = self.exchange_tree.insert("", tk.END, values=(row["_label"], branch["branch_name"], qty_text, f"Rs. {value:.2f}"))
        self.exchange_tree.set(item_id, "item", row["_label"])
        self._update_totals()

    def _remove_exchange(self):
        selection = self.exchange_tree.selection()
        if not selection:
            return
        index = self.exchange_tree.index(selection[0])
        self.exchange_tree.delete(selection[0])
        self.exchange_rows.pop(index)
        self._update_totals()

    def _calculate_totals(self):
        factor = (float(self.invoice.grand_total) / float(self.invoice.subtotal)) if self.invoice.subtotal else 1.0
        returned = 0.0
        for item, boxes_entry, loose_entry in self.return_inputs.values():
            try:
                boxes = int(boxes_entry.get() or 0)
                loose = int(loose_entry.get() or 0)
            except ValueError:
                continue
            if item.item_type == "tile":
                product = ProductRepository.get_by_id(item.product_id)
                requested = boxes * int(product.pieces_per_box) + loose
            else:
                requested = loose
            returned += float(item.line_total) * requested / max(int(item.quantity), 1) * factor
        exchanged = 0.0
        for item_id in self.exchange_tree.get_children():
            try:
                exchanged += float(self.exchange_tree.set(item_id, "value").replace("Rs. ", ""))
            except ValueError:
                pass
        return round(returned, 2), round(exchanged, 2), round(returned - exchanged, 2)

    def _update_totals(self):
        returned, exchanged, difference = self._calculate_totals()
        direction = "Refund due" if difference > 0 else "Additional payment due" if difference < 0 else "Even exchange"
        self.totals_label.configure(text=f"Returned: Rs. {returned:.2f}\nExchange: Rs. {exchanged:.2f}\n{direction}: Rs. {abs(difference):.2f}")

    def _history_text(self):
        rows = self.history.get("returns", [])
        if not rows:
            return "No previous returns for this invoice."
        return "Previous returns: " + ", ".join(f"{r['return_number']} (Rs. {float(r['returned_value']):.2f})" for r in rows)

    def _submit(self):
        reason = self.reason.get().strip()
        if len(reason) < 5:
            messagebox.showerror("Reason Required", "Return reason must be at least 5 characters.", parent=self.window)
            return
        return_items = []
        try:
            for item, boxes_entry, loose_entry in self.return_inputs.values():
                boxes = int(boxes_entry.get() or 0) if item.item_type == "tile" else 0
                loose = int(loose_entry.get() or 0)
                if boxes or loose:
                    return_items.append({"invoice_item_id": item.id, "boxes": boxes, "loose_pieces": loose if item.item_type == "tile" else 0, "quantity": loose if item.item_type != "tile" else 0})
            amount = float(self.settlement_amount.get() or 0)
        except ValueError:
            messagebox.showerror("Invalid Quantity", "Return quantities and settlement must be numeric.", parent=self.window)
            return
        if not return_items:
            messagebox.showerror("Return Items", "Select at least one quantity to return.", parent=self.window)
            return
        payload = {
            "return_date": datetime.now().astimezone().isoformat(),
            "reason": reason,
            "return_items": return_items,
            "exchange_items": self.exchange_rows,
            "settlement": None,
        }
        if amount > 0:
            # The backend verifies the direction against the final calculated difference.
            _returned, _exchanged, difference = self._calculate_totals()
            direction = "refund_to_customer" if difference > 0 else "payment_from_customer"
            payload["settlement"] = {"amount": amount, "direction": direction, "settlement_date": datetime.now().astimezone().isoformat(), "method": self.settlement_method.get(), "notes": None}
        if not messagebox.askyesno("Confirm Return", "Process this return/exchange? Stock and settlement records will be written together.", parent=self.window):
            return
        try:
            result = InvoiceService.create_return(self.invoice.id, payload)
            messagebox.showinfo("Return Completed", f"{result['return_number']} completed.\nDifference: Rs. {float(result['difference_amount']):.2f}", parent=self.window)
            if messagebox.askyesno("Return Note", "Generate and open the return note PDF?", parent=self.window):
                try:
                    path = ReturnPrinter(self.invoice, result).generate_pdf()
                    ReturnPrinter.open_pdf(path)
                except Exception as print_exc:
                    messagebox.showwarning("Return Note Saved", f"The return completed, but the PDF could not be opened.\n{print_exc}", parent=self.window)
            self.window.destroy()
            if self.on_complete:
                self.on_complete(result)
        except Exception as exc:
            messagebox.showerror("Return Failed", str(exc), parent=self.window)
