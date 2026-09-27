"""Admin-only activity timeline and product history."""

import json
import tkinter as tk
from datetime import date, datetime
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

from repositories.activity_log_repository import ActivityLogRepository
from repositories.branch_repository import BranchRepository
from repositories.user_repository import UserRepository
from services.auth_service import AuthenticationService
from ui.theme import COLORS, FONTS, SIZES, SPACING
from utils.activity_log_formatter import activity_category, activity_reference, activity_summary, format_activity_details, raw_activity_json
from utils.datetime_format import format_business_datetime
from utils.searchable_combobox import SearchableCombobox


VIEWS = {"Business Activity": "business", "Access": "access", "All": "all"}
CATEGORIES = ("All Categories", "Stock", "Sales", "Returns", "Pricing", "Catalogue", "Users", "Access")
DEFAULT_ACTIONS = {
    "Stock": ["Stock IN", "Stock OUT", "Accessory Stock IN", "Accessory Stock OUT", "Sanitary Stock IN", "Sanitary Stock OUT"],
    "Sales": ["Invoice Created", "Invoice Payment Recorded", "Invoice Remarks Updated", "Invoice Voided", "Cross-Branch Sale"],
    "Returns": ["Invoice Return Processed", "Return Settlement Recorded"],
    "Pricing": ["Rate Card Updated", "Tile Size Added", "Product Rate Override Added", "Product Rate Override Updated", "Product Rate Override Removed"],
    "Catalogue": ["Product Added", "Product Edited", "Product Deleted", "Accessory Added", "Accessory Edited", "Accessory Deleted", "Sanitary Product Added", "Sanitary Product Edited", "Sanitary Product Deleted"],
    "Users": ["User Created", "User Edited", "Password Changed"],
    "Access": ["Login", "Logout"],
}


class ActivityLogWindow:
    def __init__(self, parent, current_user=None):
        self.parent = parent
        self.current_user = current_user
        if not AuthenticationService.is_admin(current_user):
            raise PermissionError("Admin access required")
        self.branches = []
        self.users = []
        self.actions = {category: list(actions) for category, actions in DEFAULT_ACTIONS.items()}
        self.products = []
        self.product_labels = {}
        self.rows_by_tree_id = {}
        self.setup_ui()
        self.parent.after(50, self.load_reference_data)
        self.parent.after(150, self.search_activities)

    @staticmethod
    def _product_label(row):
        codes = [row.get("item_code"), *(row.get("client_codes") or [])]
        code_text = ", ".join(dict.fromkeys(str(code) for code in codes if code))
        return f"{row['name']} - {row['tile_size']}" + (f" [{code_text}]" if code_text else "")

    def set_window_title(self, title):
        try:
            self.parent.winfo_toplevel().title(title)
        except Exception:
            pass

    def setup_ui(self):
        ctk.CTkLabel(self.parent, text="Activity Log / Audit Trail", font=FONTS["section"],
                     fg_color=COLORS["surface"], text_color=COLORS["text"], height=48).pack(fill=tk.X)
        root = ctk.CTkFrame(self.parent, fg_color=COLORS["app_bg"], corner_radius=0)
        root.pack(fill=tk.BOTH, expand=True, padx=SPACING["page_x"], pady=SPACING["page_y"])
        filters = self._panel(root)
        filters.pack(fill=tk.X, pady=(0, 8))
        for col in range(8):
            filters.grid_columnconfigure(col, weight=1)

        self.view_var = tk.StringVar(value="Business Activity")
        self.category_var = tk.StringVar(value="All Categories")
        self.action_var = tk.StringVar(value="All Actions")
        self.user_var = tk.StringVar(value="All Users")
        self.branch_var = tk.StringVar(value="All Branches")
        self.invoice_var = tk.StringVar()
        self.return_var = tk.StringVar()

        self._combo(filters, "View", self.view_var, list(VIEWS), 0, 18)
        category = self._combo(filters, "Category", self.category_var, CATEGORIES, 1, 16)
        category.bind("<<ComboboxSelected>>", self._refresh_actions)
        self._label(filters, "Action").grid(row=0, column=2, sticky="w", padx=6)
        self.action_combo = ttk.Combobox(filters, textvariable=self.action_var, state="readonly", width=22)
        self.action_combo.grid(row=1, column=2, sticky="ew", padx=6)
        self._refresh_actions()
        self.user_combo = self._combo(filters, "User", self.user_var, ["All Users"], 3, 17)
        self.branch_combo = self._combo(filters, "Branch", self.branch_var, ["All Branches"], 4, 20)

        self._label(filters, "Product / Item Code").grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.product_combo = SearchableCombobox(filters, width=35)
        self.product_combo.set_completion_list(list(self.product_labels))
        self.product_combo.grid(row=3, column=0, columnspan=2, sticky="ew", padx=(0, 6))
        self._entry(filters, "Invoice Number", self.invoice_var, 2)
        self._entry(filters, "Return Number", self.return_var, 3)
        self.date_from = self._date_entry(filters, "Date From", 4, date.today().replace(day=1).isoformat())
        self.date_to = self._date_entry(filters, "Date To", 5, date.today().isoformat())
        self._button(filters, "Search", self.search_activities).grid(row=3, column=6, padx=6)
        self._button(filters, "Product History", self.show_product_history, False).grid(row=3, column=7, padx=(6, 0))
        self.status_label = ctk.CTkLabel(filters, text="Loading filters...", font=FONTS["small"],
                                         text_color=COLORS["text_muted"], anchor="w")
        self.status_label.grid(row=4, column=0, columnspan=8, sticky="ew", padx=6, pady=(6, 4))

        content = self._panel(root)
        content.pack(fill=tk.BOTH, expand=True)
        content.grid_rowconfigure(0, weight=3)
        content.grid_rowconfigure(1, weight=2)
        content.grid_columnconfigure(0, weight=1)
        columns = ("Date", "User", "Branch", "Category", "Action", "Item / Document", "Summary")
        self.tree = ttk.Treeview(content, columns=columns, show="headings", height=14)
        for column, width in zip(columns, (145, 100, 145, 90, 155, 155, 390)):
            self.tree.heading(column, text=column)
            self.tree.column(column, width=width, minwidth=70, anchor=tk.W)
        scrollbar = ttk.Scrollbar(content, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(10, 0), pady=10)
        scrollbar.grid(row=0, column=1, sticky="ns", padx=(0, 10), pady=10)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.details = tk.Text(content, height=9, wrap=tk.WORD, state=tk.DISABLED, font=("Consolas", 9),
                               bg=COLORS["app_bg"], fg=COLORS["text"], relief=tk.FLAT, padx=10, pady=8)
        self.details.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=10, pady=(0, 8))
        self._button(content, "Export Log", self.export_log, False).grid(row=2, column=0, columnspan=2, pady=(0, 10))

    def _panel(self, parent):
        return ctk.CTkFrame(parent, fg_color=COLORS["surface"], corner_radius=SIZES["corner_radius"], border_width=1, border_color=COLORS["border"])

    def _label(self, parent, text):
        return ctk.CTkLabel(parent, text=text, font=FONTS["small"], text_color=COLORS["text"], anchor="w")

    def _combo(self, parent, label, variable, values, column, width):
        self._label(parent, label).grid(row=0, column=column, sticky="w", padx=6)
        widget = ttk.Combobox(parent, textvariable=variable, values=values, state="readonly", width=width)
        widget.grid(row=1, column=column, sticky="ew", padx=6)
        return widget

    def _entry(self, parent, label, variable, column):
        self._label(parent, label).grid(row=2, column=column, sticky="w", padx=6, pady=(8, 0))
        ctk.CTkEntry(parent, textvariable=variable, height=SIZES["input_height"]).grid(row=3, column=column, sticky="ew", padx=6)

    def _date_entry(self, parent, label, column, value):
        self._label(parent, label).grid(row=2, column=column, sticky="w", padx=6, pady=(8, 0))
        entry = ctk.CTkEntry(parent, height=SIZES["input_height"])
        entry.grid(row=3, column=column, sticky="ew", padx=6)
        entry.insert(0, value)
        return entry

    def _button(self, parent, text, command, primary=True):
        return ctk.CTkButton(parent, text=text, command=command, height=34, width=130,
                             fg_color=COLORS["primary"] if primary else COLORS["card"],
                             hover_color=COLORS["primary_hover"] if primary else COLORS["card_hover"],
                             border_width=0 if primary else 1, border_color=COLORS["border"])

    def _refresh_actions(self, _event=None):
        category = self.category_var.get()
        actions = sorted({action for values in self.actions.values() for action in values}) if category == "All Categories" else self.actions.get(category, [])
        self.action_combo.configure(values=["All Actions", *actions])
        self.action_var.set("All Actions")

    def load_reference_data(self):
        """Load filter metadata without allowing an API failure to erase the screen."""
        errors = []
        try:
            self.branches = BranchRepository.get_all()
            branch_values = ["All Branches"] + [branch.name for branch in self.branches]
            self.branch_combo.configure(values=branch_values)
        except Exception as exc:
            errors.append(f"branches: {exc}")
        try:
            self.users = UserRepository.get_all()
            user_values = ["All Users"] + [f"{user.username} ({user.role})" for user in self.users]
            self.user_combo.configure(values=user_values)
        except Exception as exc:
            errors.append(f"users: {exc}")
        try:
            loaded_actions = ActivityLogRepository.action_options()
            if loaded_actions:
                self.actions = loaded_actions
            self._refresh_actions()
        except Exception as exc:
            errors.append(f"action filters: {exc}")
        try:
            self.products = ActivityLogRepository.product_options()
            self.product_labels = {self._product_label(row): row["id"] for row in self.products}
            self.product_combo.set_completion_list(list(self.product_labels))
        except Exception as exc:
            errors.append(f"product search: {exc}")
            self._load_product_fallback(errors)
        if errors:
            message = "Some Activity Log filters could not load. The timeline is still available. " + "; ".join(errors)
            self._set_status(message, error=True)
            print(f"[activity-log] {message}")
        else:
            self._set_status("Business Activity excludes login and logout entries.")

    def _load_product_fallback(self, errors):
        try:
            from repositories.product_repository import ProductRepository
            products = ProductRepository.get_all()
            self.product_labels = {
                f"{product.name} - {product.tile_size}" + (f" [{product.item_code}]" if getattr(product, "item_code", None) else ""): product.id
                for product in products
            }
            self.product_combo.set_completion_list(list(self.product_labels))
        except Exception as exc:
            errors.append(f"product fallback: {exc}")

    def _set_status(self, message, error=False):
        self.status_label.configure(
            text=message,
            text_color=COLORS["danger"] if error else COLORS["text_muted"],
        )

    def _filters(self):
        for entry in (self.date_from, self.date_to):
            if entry.get().strip():
                datetime.strptime(entry.get().strip(), "%Y-%m-%d")
        return dict(
            user_id=next((u.id for u in self.users if self.user_var.get().startswith(f"{u.username} (")), None),
            branch_id=next((b.id for b in self.branches if b.name == self.branch_var.get()), None),
            action_type=None if self.action_var.get() == "All Actions" else self.action_var.get(),
            view=VIEWS[self.view_var.get()],
            event_category=None if self.category_var.get() == "All Categories" else self.category_var.get(),
            product_id=self.product_labels.get(self.product_combo.get()),
            invoice_number=self.invoice_var.get().strip() or None,
            return_number=self.return_var.get().strip() or None,
            date_from=self.date_from.get().strip() or None,
            date_to=self.date_to.get().strip() or None,
            limit=2000,
        )

    def search_activities(self):
        try:
            filters = self._filters()
            if filters["product_id"] and not filters["invoice_number"] and not filters["return_number"]:
                payload = ActivityLogRepository.product_history(
                    filters["product_id"], filters["date_from"], filters["date_to"]
                )
                display = self._filter_history_rows(payload["timeline"], filters)
                self._show_rows(display)
                return
            rows = ActivityLogRepository.search(**filters)
            display = [{"activity": row, "date": row.action_date, "user": row.username, "branch": row.branch_name or "N/A",
                        "category": activity_category(row), "action": row.action_type, "reference": activity_reference(row),
                        "summary": activity_summary(row)} for row in rows]
            self._show_rows(display)
        except ValueError:
            self._set_status("Invalid date. Use YYYY-MM-DD for both dates.", error=True)
            messagebox.showerror("Invalid Date", "Use YYYY-MM-DD for both dates.")
        except Exception as exc:
            self._set_status(f"Could not load Activity Log: {exc}", error=True)
            print(f"[activity-log] timeline load failed: {exc}")
            messagebox.showerror("Error", f"Failed to load activities: {exc}")

    def _filter_history_rows(self, rows, filters):
        category = filters["event_category"]
        action = filters["action_type"]
        user = next((u.username for u in self.users if u.id == filters["user_id"]), None)
        branch = next((b.name for b in self.branches if b.id == filters["branch_id"]), None)
        if filters["view"] == "access":
            return []
        return [row for row in rows if
                (not category or row["category"] == category) and
                (not action or row["action"] == action) and
                (not user or row["user"] == user) and
                (not branch or row["branch"] == branch)]

    def show_product_history(self):
        product_id = self.product_labels.get(self.product_combo.get())
        if not product_id:
            messagebox.showinfo("Select Product", "Select a product or item code first.")
            return
        try:
            payload = ActivityLogRepository.product_history(product_id, self.date_from.get().strip(), self.date_to.get().strip())
            self._show_rows(payload["timeline"])
        except Exception as exc:
            messagebox.showerror("Product History", f"Failed to load product history: {exc}")

    def _show_rows(self, rows):
        self.tree.delete(*self.tree.get_children())
        self.rows_by_tree_id.clear()
        for row in rows:
            item = self.tree.insert("", "end", values=(format_business_datetime(row["date"]), row["user"], row["branch"],
                                    row["category"], row["action"], row["reference"], row["summary"]))
            self.rows_by_tree_id[item] = row
        self.set_window_title(f"Activity Log - Tile Index ({len(rows)} entries)")

    def on_select(self, _event=None):
        selected = self.tree.selection()
        if not selected:
            return
        row = self.rows_by_tree_id[selected[0]]
        if "activity" in row:
            readable = format_activity_details(row["activity"]) or "No additional details"
            raw = raw_activity_json(row["activity"]) or "No raw audit data"
        else:
            readable = row.get("details") or row.get("summary") or ""
            raw = json.dumps(row.get("raw") or {}, indent=2, default=str)
        self.details.configure(state=tk.NORMAL)
        self.details.delete("1.0", tk.END)
        self.details.insert(tk.END, f"{readable}\n\nRaw audit data:\n{raw}")
        self.details.configure(state=tk.DISABLED)

    def export_log(self):
        filename = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if not filename:
            return
        with open(filename, "w", encoding="utf-8") as handle:
            handle.write("TILE INDEX - ACTIVITY TIMELINE\n\n")
            for item in self.tree.get_children():
                handle.write(" | ".join(str(value) for value in self.tree.item(item, "values")) + "\n")
        messagebox.showinfo("Export Complete", f"Activity log exported to:\n{filename}")
