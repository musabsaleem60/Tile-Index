"""
Sanitary Management Window
Manage sanitary products and branch-wise stock
"""

import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
from repositories.branch_repository import BranchRepository
from services.auth_service import AuthenticationService
from models.sanitary import SanitaryProduct
from desktop_client.session import api_client, invalidate_cache
from utils.searchable_combobox import SearchableCombobox
from ui.theme import COLORS, FONTS, SIZES, SPACING


class SanitaryWindow:
    """Sanitary management window"""

    def __init__(self, parent, current_user):
        self.parent = parent
        self.current_user = current_user

        self.branches = BranchRepository.get_all()
        self.products = self.fetch_products()
        self.selected_branch_id = None
        self.selected_product_id = None
        self.editing_product_id = None

        if AuthenticationService.is_employee(self.current_user) and self.current_user.branch_id is not None:
            self.branches = [b for b in self.branches if b.id == self.current_user.branch_id]
            if self.branches:
                self.selected_branch_id = self.branches[0].id

        self.setup_ui()
        self.load_products()

        if AuthenticationService.is_employee(self.current_user) and self.current_user.branch_id is not None and self.branches:
            self.branch_var.set(self.branches[0].name)
            self.selected_branch_id = self.branches[0].id
            self.refresh_stock()

    def setup_ui(self):
        """Setup the sanitary UI"""
        header = ctk.CTkLabel(
            self.parent,
            text="Sanitary Management",
            font=FONTS["section"],
            fg_color=COLORS["surface"],
            text_color=COLORS["text"],
            height=48,
        )
        header.pack(fill=tk.X)

        main_frame = ctk.CTkFrame(self.parent, fg_color=COLORS["app_bg"], corner_radius=0)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=SPACING["page_x"], pady=SPACING["page_y"])

        left_frame = self.panel(main_frame, "Sanitary Product Management")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        self.form_label(left_frame, "Company:").grid(row=1, column=0, sticky=tk.W, pady=5, padx=(12, 8))
        self.company_var = tk.StringVar(value=SanitaryProduct.COMPANIES[0])
        self.company_combo = SearchableCombobox(left_frame, textvariable=self.company_var, width=SIZES["compact_dropdown_width"], state="normal", font=FONTS["small"])
        self.company_combo.set_completion_list(SanitaryProduct.COMPANIES)
        self.company_combo.configure(font=FONTS["small"])
        self.company_combo.grid(row=1, column=1, pady=5, padx=(0, 12), sticky=tk.W)
        self.company_combo.bind('<<ComboboxSelected>>', self.on_company_change)

        self.form_label(left_frame, "Product Name/Code:").grid(row=2, column=0, sticky=tk.W, pady=5, padx=(12, 8))
        self.category_var = tk.StringVar(value=SanitaryProduct.CATEGORIES[0])
        self.category_combo = SearchableCombobox(left_frame, textvariable=self.category_var, width=SIZES["compact_dropdown_width"], state="normal", font=FONTS["small"])
        self.category_combo.set_completion_list(SanitaryProduct.CATEGORIES)
        self.category_combo.configure(font=FONTS["small"])
        self.category_combo.grid(row=2, column=1, pady=5, padx=(0, 12), sticky=tk.W)

        self.form_label(left_frame, "Color:").grid(row=3, column=0, sticky=tk.W, pady=5, padx=(12, 8))
        self.color_var = tk.StringVar(value="White")
        self.color_combo = SearchableCombobox(left_frame, textvariable=self.color_var, width=SIZES["compact_dropdown_width"], state="normal", font=FONTS["small"])
        self.color_combo.set_completion_list(SanitaryProduct.DEFAULT_COLORS)
        self.color_combo.configure(font=FONTS["small"])
        self.color_combo.grid(row=3, column=1, pady=5, padx=(0, 12), sticky=tk.W)

        self.form_label(left_frame, "Sale Price (Rs.):").grid(row=4, column=0, sticky=tk.W, pady=5, padx=(12, 8))
        self.sale_entry = self.form_entry(left_frame)
        self.sale_entry.grid(row=4, column=1, pady=5, padx=(0, 12), sticky=tk.W)

        btn_frame = ctk.CTkFrame(left_frame, fg_color="transparent", corner_radius=0)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=10)

        self.add_update_btn = self.action_button(btn_frame, "Add Sanitary Product", self.add_or_update_product, width=180)
        self.add_update_btn.pack(side=tk.LEFT, padx=5)
        self.action_button(btn_frame, "Clear", self.clear_form, width=110, primary=False).pack(side=tk.LEFT, padx=5)

        filter_frame = self.subpanel(left_frame, "Filters")
        filter_frame.grid(row=6, column=0, columnspan=2, sticky=tk.EW, pady=(10, 0), padx=12)

        self.filter_company_var = tk.StringVar(value="All")
        self.filter_company_combo = SearchableCombobox(filter_frame, textvariable=self.filter_company_var, width=18, state="normal", font=FONTS["small"])
        self.filter_company_combo.set_completion_list(["All"] + SanitaryProduct.COMPANIES)
        self.filter_company_combo.configure(font=FONTS["small"])
        self.filter_company_combo.grid(row=1, column=0, padx=5, pady=(0, 8))
        self.filter_company_combo.bind('<<ComboboxSelected>>', self.on_filter_change)

        self.filter_category_var = tk.StringVar(value="All")
        self.filter_category_combo = SearchableCombobox(filter_frame, textvariable=self.filter_category_var, width=18, state="normal", font=FONTS["small"])
        self.filter_category_combo.set_completion_list(["All"] + SanitaryProduct.CATEGORIES)
        self.filter_category_combo.configure(font=FONTS["small"])
        self.filter_category_combo.grid(row=1, column=1, padx=5, pady=(0, 8))
        self.filter_category_combo.bind('<<ComboboxSelected>>', self.on_filter_change)

        self.filter_color_var = tk.StringVar(value="All")
        self.filter_color_combo = SearchableCombobox(filter_frame, textvariable=self.filter_color_var, width=14, state="normal", font=FONTS["small"])
        self.filter_color_combo.set_completion_list(["All"] + SanitaryProduct.ORIENT_COLORS)
        self.filter_color_combo.configure(font=FONTS["small"])
        self.filter_color_combo.grid(row=1, column=2, padx=5, pady=(0, 8))
        self.filter_color_combo.bind('<<ComboboxSelected>>', self.on_filter_change)

        self.form_label(left_frame, "Sanitary Products List:", bold=True).grid(row=7, column=0, columnspan=2, sticky=tk.W, pady=(10, 5), padx=12)

        tree_frame = ctk.CTkFrame(left_frame, fg_color=COLORS["surface"], corner_radius=SIZES["corner_radius"], border_width=1, border_color=COLORS["border"])
        tree_frame.grid(row=8, column=0, columnspan=2, sticky=tk.NSEW, pady=5, padx=12)
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        columns = ('S.No', 'Company', 'Category', 'Color', 'SKU', 'Sale')
        self.products_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=12)
        for col in columns:
            self.products_tree.heading(col, text=col)
            self.products_tree.column(col, width=95, anchor=tk.CENTER)
        self.products_tree.column('Category', width=135, anchor=tk.W)
        self.products_tree.column('SKU', width=140, anchor=tk.W)

        tree_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.products_tree.yview)
        self.products_tree.configure(yscrollcommand=tree_scroll.set)
        self.products_tree.grid(row=0, column=0, sticky=tk.NSEW, padx=(1, 0), pady=1)
        tree_scroll.grid(row=0, column=1, sticky=tk.NS, pady=1)
        self.products_tree.bind('<<TreeviewSelect>>', self.on_product_select)

        action_frame = ctk.CTkFrame(left_frame, fg_color="transparent", corner_radius=0)
        action_frame.grid(row=9, column=0, columnspan=2, pady=(5, 12))

        self.action_button(action_frame, "Edit", self.edit_selected, width=110).pack(side=tk.LEFT, padx=5)
        self.action_button(action_frame, "Delete", self.delete_selected, width=110, danger=True).pack(side=tk.LEFT, padx=5)

        right_frame = self.panel(main_frame, "Stock Management")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

        self.form_label(right_frame, "Select Branch:", bold=True).grid(row=1, column=0, sticky=tk.W, pady=5, padx=(12, 8))
        self.branch_var = tk.StringVar()
        self.branch_combo = SearchableCombobox(right_frame, textvariable=self.branch_var, width=SIZES["compact_dropdown_width"], state="normal", font=FONTS["small"])
        self.branch_combo.set_completion_list([b.name for b in self.branches])
        self.branch_combo.configure(font=FONTS["small"])
        self.branch_combo.grid(row=1, column=1, pady=5, padx=(0, 12), sticky=tk.W)
        self.branch_combo.bind('<<ComboboxSelected>>', self.on_branch_select)

        if AuthenticationService.is_employee(self.current_user) and self.current_user.branch_id is not None:
            self.branch_combo.config(state="disabled")

        self.form_label(right_frame, "Select Sanitary Product:", bold=True).grid(row=2, column=0, sticky=tk.W, pady=5, padx=(12, 8))
        self.stock_product_var = tk.StringVar()
        self.stock_product_combo = SearchableCombobox(right_frame, textvariable=self.stock_product_var, width=SIZES["dropdown_width"], state="normal", font=FONTS["small"])
        self.stock_product_combo.configure(font=FONTS["small"])
        self.stock_product_combo.grid(row=2, column=1, pady=5, padx=(0, 12), sticky=tk.W)
        self.stock_product_combo.bind('<<ComboboxSelected>>', self.on_stock_product_select)

        stock_in_frame = self.subpanel(right_frame, "Stock IN")
        stock_in_frame.grid(row=3, column=0, columnspan=2, sticky=tk.EW, pady=10, padx=12)
        self.form_label(stock_in_frame, "Quantity:").grid(row=1, column=0, sticky=tk.W, pady=3, padx=8)
        self.stock_in_qty_entry = self.form_entry(stock_in_frame, width=160)
        self.stock_in_qty_entry.grid(row=1, column=1, pady=3, padx=8, sticky=tk.W)
        self.action_button(stock_in_frame, "Add Stock", self.add_stock, width=160).grid(row=2, column=0, columnspan=2, pady=10)

        stock_out_frame = self.subpanel(right_frame, "Stock OUT")
        stock_out_frame.grid(row=4, column=0, columnspan=2, sticky=tk.EW, pady=10, padx=12)
        self.form_label(stock_out_frame, "Quantity:").grid(row=1, column=0, sticky=tk.W, pady=3, padx=8)
        self.stock_out_qty_entry = self.form_entry(stock_out_frame, width=160)
        self.stock_out_qty_entry.grid(row=1, column=1, pady=3, padx=8, sticky=tk.W)
        self.action_button(stock_out_frame, "Remove Stock", self.remove_stock, width=160, danger=True).grid(row=2, column=0, columnspan=2, pady=10)

        stock_display_frame = self.subpanel(right_frame, "Current Sanitary Stock")
        stock_display_frame.grid(row=5, column=0, columnspan=2, sticky=tk.NSEW, pady=10, padx=12)
        stock_display_frame.grid_rowconfigure(1, weight=1)
        stock_display_frame.grid_columnconfigure(0, weight=1)

        stock_columns = ('S.No', 'Company', 'Category', 'Color', 'SKU', 'Sale', 'Qty', 'Value')
        self.stock_tree = ttk.Treeview(stock_display_frame, columns=stock_columns, show='headings', height=10)
        for col in stock_columns:
            self.stock_tree.heading(col, text=col)
            self.stock_tree.column(col, width=80, anchor=tk.CENTER)
        self.stock_tree.column('Category', width=120, anchor=tk.W)
        self.stock_tree.column('SKU', width=120, anchor=tk.W)

        stock_scroll = ttk.Scrollbar(stock_display_frame, orient=tk.VERTICAL, command=self.stock_tree.yview)
        self.stock_tree.configure(yscrollcommand=stock_scroll.set)
        self.stock_tree.grid(row=1, column=0, sticky=tk.NSEW, padx=(8, 0), pady=(0, 8))
        stock_scroll.grid(row=1, column=1, sticky=tk.NS, padx=(0, 8), pady=(0, 8))

        self.action_button(right_frame, "Refresh Stock", self.refresh_stock, width=160).grid(row=6, column=0, columnspan=2, pady=(5, 12))

        left_frame.grid_rowconfigure(8, weight=1)
        left_frame.grid_columnconfigure(1, weight=1)
        right_frame.grid_columnconfigure(1, weight=1)
        right_frame.grid_rowconfigure(5, weight=1)

    def panel(self, parent, title):
        panel = ctk.CTkFrame(
            parent,
            fg_color=COLORS["surface"],
            corner_radius=SIZES["corner_radius"],
            border_width=1,
            border_color=COLORS["border"],
        )
        ctk.CTkLabel(
            panel,
            text=title,
            font=FONTS["body_bold"],
            text_color=COLORS["text"],
            height=SIZES["section_label_height"],
        ).grid(row=0, column=0, columnspan=2, sticky=tk.EW, padx=12, pady=(10, 8))
        return panel

    def subpanel(self, parent, title):
        panel = ctk.CTkFrame(
            parent,
            fg_color=COLORS["card"],
            corner_radius=SIZES["corner_radius"],
            border_width=1,
            border_color=COLORS["border"],
        )
        ctk.CTkLabel(
            panel,
            text=title,
            font=FONTS["small_bold"],
            text_color=COLORS["text"],
            height=SIZES["small_label_height"],
        ).grid(row=0, column=0, columnspan=3, sticky=tk.EW, padx=8, pady=(8, 4))
        return panel

    def form_label(self, parent, text, bold=False):
        return ctk.CTkLabel(
            parent,
            text=text,
            font=FONTS["small_bold"] if bold else FONTS["small"],
            text_color=COLORS["text"],
            height=SIZES["small_label_height"],
            anchor=tk.W,
        )

    def form_entry(self, parent, width=220):
        return ctk.CTkEntry(
            parent,
            width=width,
            height=SIZES["input_height"],
            font=FONTS["small"],
            fg_color=COLORS["app_bg"],
            border_color=COLORS["border"],
            text_color=COLORS["text"],
        )

    def action_button(self, parent, text, command, width=140, primary=True, danger=False):
        if danger:
            fg_color, hover_color = COLORS["danger"], COLORS["danger_hover"]
        elif primary:
            fg_color, hover_color = COLORS["primary"], COLORS["primary_hover"]
        else:
            fg_color, hover_color = COLORS["card"], COLORS["card_hover"]
        return ctk.CTkButton(
            parent,
            text=text,
            command=command,
            width=width,
            height=34,
            fg_color=fg_color,
            hover_color=hover_color,
            text_color=COLORS["text"],
            font=FONTS["small_bold"],
            border_width=0 if primary or danger else 1,
            border_color=COLORS["border"],
            corner_radius=SIZES["corner_radius"],
            cursor="hand2",
        )

    def load_products(self):
        """Load sanitary products into treeview and dropdown"""
        self.products = self.fetch_products(
            self.filter_company_var.get() if hasattr(self, 'filter_company_var') else 'All',
            self.filter_category_var.get() if hasattr(self, 'filter_category_var') else 'All',
            self.filter_color_var.get() if hasattr(self, 'filter_color_var') else 'All',
        )

        if hasattr(self, 'products_tree'):
            for item in self.products_tree.get_children():
                self.products_tree.delete(item)

            for idx, product in enumerate(self.products, 1):
                self.products_tree.insert('', tk.END, values=(
                    idx,
                    product.company_name,
                    product.product_category,
                    product.color,
                    product.sku,
                    f"Rs. {product.sale_price:.0f}"
                ))

        self.update_stock_dropdown()
        self.refresh_stock()

    def update_stock_dropdown(self):
        """Update stock product dropdown"""
        if hasattr(self, 'stock_product_combo'):
            all_products = self.fetch_products()
            values = [self.format_product(product) for product in all_products]
            self.stock_product_combo.set_completion_list(values)
            self._stock_products = all_products

    def on_company_change(self, event):
        """Update color choices for selected company"""
        colors = SanitaryProduct.ORIENT_COLORS if self.company_var.get() == 'ORIENT (Local)' else SanitaryProduct.DEFAULT_COLORS
        self.color_combo.set_completion_list(colors)
        if self.color_var.get() not in colors:
            self.color_var.set(colors[0])

    def on_product_select(self, event):
        """Handle product selection"""
        selection = self.products_tree.selection()
        if selection:
            item = self.products_tree.item(selection[0])
            values = item['values']
            for product in self.products:
                if product.sku == values[4]:
                    self.selected_product_id = product.id
                    break

    def on_branch_select(self, event):
        """Handle branch selection"""
        selected = self.branch_var.get()
        for branch in self.branches:
            if branch.name == selected:
                self.selected_branch_id = branch.id
                break
        self.refresh_stock()

    def on_stock_product_select(self, event):
        """Handle stock product selection"""
        idx = self.stock_product_combo.current()
        if idx >= 0 and hasattr(self, '_stock_products'):
            self.selected_product_id = self._stock_products[idx].id

    def on_filter_change(self, event):
        """Handle filter change"""
        self.load_products()

    def add_or_update_product(self):
        """Add or update a sanitary product"""
        try:
            company = self.company_var.get().strip()
            category = self.category_var.get().strip()
            color = self.color_var.get().strip()
            sale_price = float(self.sale_entry.get().strip() or "0")

            if self.editing_product_id:
                api_client.put(f"/catalog/sanitary/{self.editing_product_id}", {
                    "company_name": company,
                    "product_category": category,
                    "color": color,
                    "sale_price": sale_price,
                })
                messagebox.showinfo("Success", "Sanitary product updated successfully!")
                self.editing_product_id = None
                self.add_update_btn.configure(
                    text="Add Sanitary Product",
                    fg_color=COLORS["primary"],
                    hover_color=COLORS["primary_hover"],
                )
            else:
                api_client.post("/catalog/sanitary", {
                    "company_name": company,
                    "product_category": category,
                    "color": color,
                    "sale_price": sale_price,
                })
                messagebox.showinfo("Success", "Sanitary product added successfully!")
            invalidate_cache("sanitary")

            self.clear_form()
            self.load_products()

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def edit_selected(self):
        """Edit selected sanitary product"""
        selection = self.products_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a sanitary product to edit")
            return

        item = self.products_tree.item(selection[0])
        sku = item['values'][4]
        product = next((p for p in self.products if p.sku == sku), None)
        if not product:
            messagebox.showerror("Error", "Sanitary product not found")
            return

        self.company_var.set(product.company_name)
        self.on_company_change(None)
        self.category_var.set(product.product_category)
        self.color_var.set(product.color)
        self.sale_entry.delete(0, tk.END)
        self.sale_entry.insert(0, str(int(product.sale_price)))

        self.editing_product_id = product.id
        self.add_update_btn.configure(
            text="Update Sanitary Product",
            fg_color=COLORS["warning"],
            hover_color=COLORS["warning_hover"],
        )

    def delete_selected(self):
        """Delete selected sanitary product"""
        selection = self.products_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a sanitary product to delete")
            return

        item = self.products_tree.item(selection[0])
        sku = item['values'][4]
        product = next((p for p in self.products if p.sku == sku), None)
        if not product:
            messagebox.showerror("Error", "Sanitary product not found")
            return

        confirm = messagebox.askyesno(
            "Confirm Delete",
            f"Delete {product.product_category} ({product.company_name}, {product.color})?\n\n"
            f"This cannot be undone."
        )
        if confirm:
            try:
                api_client.delete(f"/catalog/sanitary/{product.id}")
                invalidate_cache("sanitary")
                messagebox.showinfo("Success", "Sanitary product deleted successfully!")
                self.clear_form()
                self.load_products()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete: {str(e)}")

    def clear_form(self):
        """Clear product form"""
        self.company_var.set(SanitaryProduct.COMPANIES[0])
        self.category_var.set(SanitaryProduct.CATEGORIES[0])
        self.color_var.set("White")
        self.sale_entry.delete(0, tk.END)
        self.editing_product_id = None
        self.add_update_btn.configure(
            text="Add Sanitary Product",
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
        )

    def add_stock(self):
        """Add stock for a sanitary product"""
        try:
            branch_id, product, quantity = self.get_stock_inputs(self.stock_in_qty_entry)
            if not AuthenticationService.can_access_branch(self.current_user, branch_id):
                raise ValueError("You do not have access to this branch")

            api_client.post(f"/inventory/sanitary/{product.id}/stock-in", {
                "branch_id": branch_id,
                "quantity": quantity,
                "notes": "Desktop sanitary stock in",
            })
            messagebox.showinfo("Success", f"Added {quantity} units to sanitary stock!")
            self.stock_in_qty_entry.delete(0, tk.END)
            self.refresh_stock()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def remove_stock(self):
        """Remove stock for a sanitary product"""
        try:
            branch_id, product, quantity = self.get_stock_inputs(self.stock_out_qty_entry)
            if not AuthenticationService.can_access_branch(self.current_user, branch_id):
                raise ValueError("You do not have access to this branch")

            inventory = self.fetch_inventory(branch_id)
            inv = next((row for row in inventory if row["sanitary_product_id"] == product.id), None)
            available = int(inv["quantity"]) if inv else 0
            if quantity > available:
                raise ValueError(f"Insufficient stock. Available: {available}, Requested: {quantity}")

            confirm = messagebox.askyesno(
                "Confirm Stock OUT",
                f"Remove {quantity} units of {product.product_category} ({product.company_name}, {product.color})?"
            )
            if not confirm:
                return

            api_client.post(f"/inventory/sanitary/{product.id}/stock-out", {
                "branch_id": branch_id,
                "quantity": quantity,
                "notes": "Desktop sanitary stock out",
            })
            messagebox.showinfo("Success", f"Removed {quantity} units from sanitary stock!")
            self.stock_out_qty_entry.delete(0, tk.END)
            self.refresh_stock()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def get_stock_inputs(self, quantity_entry):
        """Read and validate stock form inputs"""
        if not self.selected_branch_id:
            raise ValueError("Please select a branch")

        idx = self.stock_product_combo.current()
        if idx < 0 or not hasattr(self, '_stock_products'):
            raise ValueError("Please select a sanitary product from the dropdown")

        quantity = int(quantity_entry.get().strip() or "0")
        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        return self.selected_branch_id, self._stock_products[idx], quantity

    def refresh_stock(self):
        """Refresh stock display"""
        if not hasattr(self, 'stock_tree'):
            return

        for item in self.stock_tree.get_children():
            self.stock_tree.delete(item)

        if not self.selected_branch_id:
            return

        all_products = self.fetch_products(
            self.filter_company_var.get(),
            self.filter_category_var.get(),
            self.filter_color_var.get()
        )

        inventory_by_product = {
            row["sanitary_product_id"]: row for row in self.fetch_inventory(self.selected_branch_id)
        }

        for idx, product in enumerate(all_products, 1):
            inv = inventory_by_product.get(product.id)
            qty = int(inv["quantity"]) if inv else 0
            total_value = qty * product.sale_price

            self.stock_tree.insert('', tk.END, values=(
                idx,
                product.company_name,
                product.product_category,
                product.color,
                product.sku,
                f"Rs. {product.sale_price:.0f}",
                qty,
                f"Rs. {total_value:.0f}"
            ))

    @staticmethod
    def format_product(product):
        """Format product for combobox display"""
        return (
            f"{product.company_name} - {product.product_category} - "
            f"{product.color} ({product.sku}) Rs. {product.sale_price:.0f}"
        )

    @staticmethod
    def fetch_products(company="All", category="All", color="All"):
        from urllib.parse import urlencode

        params = {}
        if company and company != "All":
            params["company"] = company
        if category and category != "All":
            params["category"] = category
        if color and color != "All":
            params["color"] = color
        path = "/catalog/sanitary"
        if params:
            path += "?" + urlencode(params)
        return [SanitaryProduct.from_dict(row) for row in api_client.get(path)]

    @staticmethod
    def fetch_inventory(branch_id):
        return api_client.get(f"/inventory/sanitary/{branch_id}")
