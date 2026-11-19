"""Master Sanitary catalogue and per-branch stock management."""

import logging
import tkinter as tk
from tkinter import messagebox, ttk

import customtkinter as ctk

from desktop_client.session import api_client
from repositories.branch_repository import BranchRepository
from services.auth_service import AuthenticationService
from ui.theme import COLORS, FONTS, SIZES, SPACING
from utils.currency import format_currency


logger = logging.getLogger(__name__)


class MasterSanitaryWindow:
    def __init__(self, parent, current_user):
        self.parent = parent
        self.current_user = current_user
        self.branches = BranchRepository.get_all()
        if AuthenticationService.is_employee(current_user) and current_user.branch_id is not None:
            self.branches = [branch for branch in self.branches if branch.id == current_user.branch_id]
        self.products = []
        self.selected_id = None
        self._build()
        self.refresh()

    def _label(self, parent, text, row, column):
        label = ctk.CTkLabel(parent, text=text, font=FONTS["small"], text_color=COLORS["text"])
        label.grid(row=row, column=column, padx=8, pady=5, sticky=tk.W)
        return label

    def _entry(self, parent, row, column, width=180):
        entry = ctk.CTkEntry(parent, width=width, font=FONTS["small"], fg_color=COLORS["app_bg"],
                             border_color=COLORS["border"], text_color=COLORS["text"])
        entry.grid(row=row, column=column, padx=8, pady=5, sticky=tk.EW)
        return entry

    def _button(self, parent, text, command):
        return ctk.CTkButton(parent, text=text, command=command, font=FONTS["small_bold"],
                             fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"],
                             corner_radius=SIZES["corner_radius"])

    def _build(self):
        ctk.CTkLabel(self.parent, text="Master Sanitary Management", font=FONTS["section"],
                     fg_color=COLORS["surface"], text_color=COLORS["text"], height=48).pack(fill=tk.X)
        body = ctk.CTkFrame(self.parent, fg_color=COLORS["app_bg"], corner_radius=0)
        body.pack(fill=tk.BOTH, expand=True, padx=SPACING["page_x"], pady=SPACING["page_y"])

        form = ctk.CTkFrame(body, fg_color=COLORS["surface"], border_color=COLORS["border"], border_width=1)
        form.pack(fill=tk.X, pady=(0, 8))
        self._label(form, "Name", 0, 0)
        self.name_entry = self._entry(form, 0, 1, 210)
        self._label(form, "Color", 0, 2)
        self.color_entry = self._entry(form, 0, 3, 145)
        self._label(form, "Price (Rs.)", 0, 4)
        self.price_entry = self._entry(form, 0, 5, 130)
        self._button(form, "Save Product", self.save_product).grid(row=1, column=0, columnspan=2, padx=8, pady=8)
        self._button(form, "Clear", self.clear_form).grid(row=1, column=2, padx=8, pady=8)
        self._button(form, "Delete Product", self.delete_product).grid(row=1, column=3, padx=8, pady=8)
        self._button(form, "Save Price", self.save_price).grid(row=1, column=4, columnspan=2, padx=8, pady=8)

        stock = ctk.CTkFrame(body, fg_color=COLORS["surface"], border_color=COLORS["border"], border_width=1)
        stock.pack(fill=tk.X, pady=(0, 8))
        self._label(stock, "Branch", 0, 0)
        self.branch_var = tk.StringVar(value=self.branches[0].name if self.branches else "")
        self.branch_combo = ttk.Combobox(stock, textvariable=self.branch_var, state="readonly", width=27,
                                         values=[branch.name for branch in self.branches])
        self.branch_combo.grid(row=0, column=1, padx=8, pady=5)
        self.branch_combo.bind("<<ComboboxSelected>>", lambda _event: self.refresh())
        self._label(stock, "Quantity (pieces)", 0, 2)
        self.quantity_entry = self._entry(stock, 0, 3, 120)
        self._label(stock, "Reason", 0, 4)
        self.reason_entry = self._entry(stock, 0, 5, 200)
        self._label(stock, "DC Number", 1, 0)
        self.dc_entry = self._entry(stock, 1, 1, 180)
        self._button(stock, "Stock In", lambda: self.adjust_stock("stock-in")).grid(row=1, column=3, padx=8, pady=8)
        self._button(stock, "Stock Out", lambda: self.adjust_stock("stock-out")).grid(row=1, column=4, padx=8, pady=8)

        table = ctk.CTkFrame(body, fg_color=COLORS["surface"], border_color=COLORS["border"], border_width=1)
        table.pack(fill=tk.BOTH, expand=True)
        search = ctk.CTkFrame(table, fg_color="transparent")
        search.pack(fill=tk.X, padx=8, pady=(8, 0))
        ctk.CTkLabel(search, text="Search", font=FONTS["small"], text_color=COLORS["text"]).pack(side=tk.LEFT, padx=(0, 8))
        self.search_entry = ctk.CTkEntry(search, width=260, font=FONTS["small"], fg_color=COLORS["app_bg"],
                                        border_color=COLORS["border"], text_color=COLORS["text"])
        self.search_entry.pack(side=tk.LEFT)
        self.search_entry.bind("<KeyRelease>", lambda _event: self._populate_table())
        self.load_status = ctk.CTkLabel(table, text="", font=FONTS["small"], text_color=COLORS["text"])
        self.load_status.pack(fill=tk.X, padx=8)
        columns = ("sku", "name", "color", "price", "branch", "quantity")
        self.tree = ttk.Treeview(table, columns=columns, show="headings", height=12)
        for column, heading, width in (("sku", "SKU", 110), ("name", "Name", 260), ("color", "Color", 110),
                                       ("price", "Price", 110), ("branch", "Branch", 190), ("quantity", "Qty", 80)):
            anchor = tk.W if column in ("sku", "name", "color", "branch") else tk.E if column == "price" else tk.CENTER
            self.tree.heading(column, text=heading, anchor=anchor)
            self.tree.column(column, width=width, minwidth=70, anchor=anchor)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8, pady=8)
        scrollbar = ttk.Scrollbar(table, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.bind("<<TreeviewSelect>>", self._select)

    def _branch_id(self):
        branch = next((branch for branch in self.branches if branch.name == self.branch_var.get()), None)
        if not branch:
            raise ValueError("Please select a branch")
        return branch.id

    def refresh(self):
        try:
            catalog_path = "/catalog/master-sanitary"
            products = api_client.get(catalog_path)
            branch_id = self._branch_id()
            inventory_path = f"/inventory/master-sanitary/{branch_id}"
            inventory = api_client.get(inventory_path)
            self.products = products
            self.stock = {row["product_id"]: row for row in inventory}
            if self.selected_id is not None:
                price = self.stock.get(self.selected_id, {}).get("price")
                self.price_entry.delete(0, tk.END)
                if price is not None:
                    self.price_entry.insert(0, str(price))
            self._populate_table()
            self.load_status.configure(text=f"{len(products)} products loaded" if products else "No Master Sanitary products yet",
                                       text_color=COLORS["text"])
        except Exception as exc:
            path = locals().get("inventory_path", locals().get("catalog_path", "unknown route"))
            logger.exception("Master Sanitary refresh failed on GET %s", path)
            self.products = []
            self.stock = {}
            self._populate_table()
            error = f"Could not load Master Sanitary from GET {path}: {exc}"
            self.load_status.configure(text=error, text_color=COLORS["danger"])
            messagebox.showerror("Master Sanitary", error)

    def _populate_table(self):
        query = self.search_entry.get().strip().casefold()
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        branch = next((branch for branch in self.branches if branch.name == self.branch_var.get()), None)
        if not branch:
            return
        branch_id = branch.id
        for product in self.products:
            if query and query not in product["name"].casefold() and query not in product["color"].casefold():
                continue
            self.tree.insert("", tk.END, iid=f"{product['id']}:{branch_id}", values=(
                product["sku"], product["name"], product["color"],
                format_currency(self.stock[product["id"]]["price"]) if product["id"] in self.stock and self.stock[product["id"]].get("price") is not None else "No price set",
                self.branch_var.get(), self.stock.get(product["id"], {}).get("quantity", 0),
            ))

    def _select(self, _event=None):
        if not self.tree.selection():
            return
        product_id, _branch_id = map(int, self.tree.selection()[0].split(":"))
        product = next((p for p in self.products if p["id"] == product_id), None)
        if not product:
            return
        self.selected_id = product_id
        price = self.stock.get(product_id, {}).get("price")
        for entry, value in ((self.name_entry, product["name"]), (self.color_entry, product["color"]),
                             (self.price_entry, "" if price is None else str(price))):
            entry.delete(0, tk.END)
            entry.insert(0, value)

    def clear_form(self):
        self.selected_id = None
        for entry in (self.name_entry, self.color_entry, self.price_entry):
            entry.delete(0, tk.END)

    def save_product(self):
        try:
            payload = {"name": self.name_entry.get(), "color": self.color_entry.get()}
            if not payload["name"].strip() or not payload["color"].strip():
                raise ValueError("Name and color are required")
            if self.selected_id:
                api_client.put(f"/catalog/master-sanitary/{self.selected_id}", payload)
            else:
                api_client.post("/catalog/master-sanitary", payload)
            self.clear_form()
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Master Sanitary", str(exc))

    def save_price(self):
        try:
            if not self.selected_id:
                raise ValueError("Save or select a product first")
            price = self.price_entry.get().strip()
            if not price or float(price) < 0:
                raise ValueError("Enter a valid non-negative price")
            api_client.put(f"/inventory/master-sanitary/{self.selected_id}/price", {
                "branch_id": self._branch_id(), "price": price,
            })
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Master Sanitary Price", str(exc))

    def delete_product(self):
        if not self.selected_id:
            messagebox.showwarning("Master Sanitary", "Select a product first")
            return
        if not messagebox.askyesno("Delete Product", "Delete this product? Products with stock or sales history cannot be deleted."):
            return
        try:
            api_client.delete(f"/catalog/master-sanitary/{self.selected_id}")
            self.clear_form()
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Master Sanitary", str(exc))

    def adjust_stock(self, action):
        try:
            if not self.selected_id:
                raise ValueError("Select a product first")
            quantity = int(self.quantity_entry.get())
            if quantity <= 0:
                raise ValueError("Quantity must be a positive whole number")
            reason = self.reason_entry.get().strip()
            if action == "stock-out" and len(reason) < 5:
                raise ValueError("Please enter a reason for removing stock.")
            api_client.post(f"/inventory/master-sanitary/{self.selected_id}/{action}", {
                "branch_id": self._branch_id(), "quantity": quantity,
                "notes": reason or None, "dc_number": self.dc_entry.get().strip() or None,
            })
            self.quantity_entry.delete(0, tk.END)
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Master Sanitary Stock", str(exc))
