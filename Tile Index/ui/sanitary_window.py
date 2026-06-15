"""
Sanitary Management Window
Manage sanitary products and branch-wise stock
"""

import tkinter as tk
from tkinter import ttk, messagebox
from repositories.branch_repository import BranchRepository
from repositories.sanitary_repository import SanitaryProductRepository, SanitaryInventoryRepository
from services.auth_service import AuthenticationService
from services.sanitary_service import SanitaryService
from models.sanitary import SanitaryProduct
from utils.searchable_combobox import SearchableCombobox


class SanitaryWindow:
    """Sanitary management window"""

    def __init__(self, parent, current_user):
        self.parent = parent
        self.current_user = current_user

        self.branches = BranchRepository.get_all()
        self.products = SanitaryProductRepository.get_all()
        self.selected_branch_id = None
        self.selected_product_id = None
        self.editing_product_id = None

        if AuthenticationService.is_employee(self.current_user):
            self.branches = [b for b in self.branches if b.id == self.current_user.branch_id]
            if self.branches:
                self.selected_branch_id = self.branches[0].id

        self.setup_ui()
        self.load_products()

        if AuthenticationService.is_employee(self.current_user) and self.branches:
            self.branch_var.set(self.branches[0].name)
            self.selected_branch_id = self.branches[0].id
            self.refresh_stock()

    def setup_ui(self):
        """Setup the sanitary UI"""
        header = tk.Label(
            self.parent,
            text="Sanitary Management",
            font=("Arial", 18, "bold"),
            bg="#1abc9c",
            fg="white",
            pady=10
        )
        header.pack(fill=tk.X)

        main_frame = tk.Frame(self.parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        left_frame = tk.LabelFrame(main_frame, text="Sanitary Product Management", font=("Arial", 12, "bold"), padx=10, pady=10)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        tk.Label(left_frame, text="Company:", font=("Arial", 10)).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.company_var = tk.StringVar(value=SanitaryProduct.COMPANIES[0])
        self.company_combo = SearchableCombobox(left_frame, textvariable=self.company_var, width=27, state="normal", font=("Arial", 10))
        self.company_combo.set_completion_list(SanitaryProduct.COMPANIES)
        self.company_combo.grid(row=0, column=1, pady=5, padx=5)
        self.company_combo.bind('<<ComboboxSelected>>', self.on_company_change)

        tk.Label(left_frame, text="Product Category:", font=("Arial", 10)).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.category_var = tk.StringVar(value=SanitaryProduct.CATEGORIES[0])
        self.category_combo = SearchableCombobox(left_frame, textvariable=self.category_var, width=27, state="normal", font=("Arial", 10))
        self.category_combo.set_completion_list(SanitaryProduct.CATEGORIES)
        self.category_combo.grid(row=1, column=1, pady=5, padx=5)

        tk.Label(left_frame, text="Color:", font=("Arial", 10)).grid(row=2, column=0, sticky=tk.W, pady=5)
        self.color_var = tk.StringVar(value="White")
        self.color_combo = SearchableCombobox(left_frame, textvariable=self.color_var, width=27, state="normal", font=("Arial", 10))
        self.color_combo.set_completion_list(SanitaryProduct.DEFAULT_COLORS)
        self.color_combo.grid(row=2, column=1, pady=5, padx=5)

        tk.Label(left_frame, text="SKU/Article Code:", font=("Arial", 10)).grid(row=3, column=0, sticky=tk.W, pady=5)
        self.sku_entry = tk.Entry(left_frame, width=30, font=("Arial", 10))
        self.sku_entry.grid(row=3, column=1, pady=5, padx=5)

        tk.Label(left_frame, text="Purchase Price (Rs.):", font=("Arial", 10)).grid(row=4, column=0, sticky=tk.W, pady=5)
        self.purchase_entry = tk.Entry(left_frame, width=30, font=("Arial", 10))
        self.purchase_entry.grid(row=4, column=1, pady=5, padx=5)

        tk.Label(left_frame, text="Sale Price (Rs.):", font=("Arial", 10)).grid(row=5, column=0, sticky=tk.W, pady=5)
        self.sale_entry = tk.Entry(left_frame, width=30, font=("Arial", 10))
        self.sale_entry.grid(row=5, column=1, pady=5, padx=5)

        btn_frame = tk.Frame(left_frame)
        btn_frame.grid(row=6, column=0, columnspan=2, pady=10)

        self.add_update_btn = tk.Button(btn_frame, text="Add Sanitary Product", command=self.add_or_update_product, bg="#3498db", fg="white", width=18)
        self.add_update_btn.pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Clear", command=self.clear_form, bg="#95a5a6", fg="white", width=12).pack(side=tk.LEFT, padx=5)

        filter_frame = tk.LabelFrame(left_frame, text="Filters", font=("Arial", 10, "bold"), padx=5, pady=5)
        filter_frame.grid(row=7, column=0, columnspan=2, sticky=tk.EW, pady=(10, 0))

        self.filter_company_var = tk.StringVar(value="All")
        self.filter_company_combo = SearchableCombobox(filter_frame, textvariable=self.filter_company_var, width=20, state="normal", font=("Arial", 9))
        self.filter_company_combo.set_completion_list(["All"] + SanitaryProduct.COMPANIES)
        self.filter_company_combo.grid(row=0, column=0, padx=3, pady=3)
        self.filter_company_combo.bind('<<ComboboxSelected>>', self.on_filter_change)

        self.filter_category_var = tk.StringVar(value="All")
        self.filter_category_combo = SearchableCombobox(filter_frame, textvariable=self.filter_category_var, width=20, state="normal", font=("Arial", 9))
        self.filter_category_combo.set_completion_list(["All"] + SanitaryProduct.CATEGORIES)
        self.filter_category_combo.grid(row=0, column=1, padx=3, pady=3)
        self.filter_category_combo.bind('<<ComboboxSelected>>', self.on_filter_change)

        self.filter_color_var = tk.StringVar(value="All")
        self.filter_color_combo = SearchableCombobox(filter_frame, textvariable=self.filter_color_var, width=16, state="normal", font=("Arial", 9))
        self.filter_color_combo.set_completion_list(["All"] + SanitaryProduct.ORIENT_COLORS)
        self.filter_color_combo.grid(row=0, column=2, padx=3, pady=3)
        self.filter_color_combo.bind('<<ComboboxSelected>>', self.on_filter_change)

        tk.Label(left_frame, text="Sanitary Products List:", font=("Arial", 10, "bold")).grid(row=8, column=0, columnspan=2, sticky=tk.W, pady=(10, 5))

        tree_frame = tk.Frame(left_frame)
        tree_frame.grid(row=9, column=0, columnspan=2, sticky=tk.NSEW, pady=5)

        columns = ('S.No', 'Company', 'Category', 'Color', 'SKU', 'Purchase', 'Sale')
        self.products_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=12)
        for col in columns:
            self.products_tree.heading(col, text=col)
            self.products_tree.column(col, width=95, anchor=tk.CENTER)
        self.products_tree.column('Category', width=135, anchor=tk.W)
        self.products_tree.column('SKU', width=140, anchor=tk.W)

        tree_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.products_tree.yview)
        self.products_tree.configure(yscrollcommand=tree_scroll.set)
        self.products_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.products_tree.bind('<<TreeviewSelect>>', self.on_product_select)

        action_frame = tk.Frame(left_frame)
        action_frame.grid(row=10, column=0, columnspan=2, pady=5)

        if AuthenticationService.can_manage_products(self.current_user):
            tk.Button(action_frame, text="Edit", command=self.edit_selected, bg="#f39c12", fg="white", width=12).pack(side=tk.LEFT, padx=5)
            tk.Button(action_frame, text="Delete", command=self.delete_selected, bg="#e74c3c", fg="white", width=12).pack(side=tk.LEFT, padx=5)

        if AuthenticationService.is_employee(self.current_user):
            for row in range(7):
                for widget in left_frame.grid_slaves(row=row):
                    widget.grid_remove()
            tk.Label(left_frame, text="Sanitary product management is restricted to administrators.",
                    font=("Arial", 10), fg="red").grid(row=0, column=0, columnspan=2, pady=20)

        right_frame = tk.LabelFrame(main_frame, text="Stock Management", font=("Arial", 12, "bold"), padx=10, pady=10)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

        tk.Label(right_frame, text="Select Branch:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.branch_var = tk.StringVar()
        self.branch_combo = SearchableCombobox(right_frame, textvariable=self.branch_var, width=27, state="normal", font=("Arial", 10))
        self.branch_combo.set_completion_list([b.name for b in self.branches])
        self.branch_combo.grid(row=0, column=1, pady=5, padx=5, sticky=tk.W)
        self.branch_combo.bind('<<ComboboxSelected>>', self.on_branch_select)

        if AuthenticationService.is_employee(self.current_user):
            self.branch_combo.config(state="disabled")

        tk.Label(right_frame, text="Select Sanitary Product:", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.stock_product_var = tk.StringVar()
        self.stock_product_combo = SearchableCombobox(right_frame, textvariable=self.stock_product_var, width=55, state="normal", font=("Arial", 10))
        self.stock_product_combo.grid(row=1, column=1, pady=5, padx=5, sticky=tk.W)
        self.stock_product_combo.bind('<<ComboboxSelected>>', self.on_stock_product_select)

        stock_in_frame = tk.LabelFrame(right_frame, text="Stock IN (Purchase Entry)", font=("Arial", 10, "bold"), padx=5, pady=5)
        stock_in_frame.grid(row=2, column=0, columnspan=2, sticky=tk.EW, pady=10)
        tk.Label(stock_in_frame, text="Quantity:", font=("Arial", 9)).grid(row=0, column=0, sticky=tk.W, pady=3)
        self.stock_in_qty_entry = tk.Entry(stock_in_frame, width=20, font=("Arial", 9))
        self.stock_in_qty_entry.grid(row=0, column=1, pady=3, padx=5)
        tk.Button(stock_in_frame, text="Add Stock", command=self.add_stock, bg="#27ae60", fg="white", width=20).grid(row=1, column=0, columnspan=2, pady=10)

        stock_out_frame = tk.LabelFrame(right_frame, text="Stock OUT (Sales/Adjustment Entry)", font=("Arial", 10, "bold"), padx=5, pady=5)
        stock_out_frame.grid(row=3, column=0, columnspan=2, sticky=tk.EW, pady=10)
        tk.Label(stock_out_frame, text="Quantity:", font=("Arial", 9)).grid(row=0, column=0, sticky=tk.W, pady=3)
        self.stock_out_qty_entry = tk.Entry(stock_out_frame, width=20, font=("Arial", 9))
        self.stock_out_qty_entry.grid(row=0, column=1, pady=3, padx=5)
        tk.Button(stock_out_frame, text="Remove Stock", command=self.remove_stock, bg="#e74c3c", fg="white", width=20).grid(row=1, column=0, columnspan=2, pady=10)

        stock_display_frame = tk.LabelFrame(right_frame, text="Current Sanitary Stock", font=("Arial", 10, "bold"), padx=5, pady=5)
        stock_display_frame.grid(row=4, column=0, columnspan=2, sticky=tk.NSEW, pady=10)

        stock_columns = ('S.No', 'Company', 'Category', 'Color', 'SKU', 'Sale', 'Qty', 'Value')
        self.stock_tree = ttk.Treeview(stock_display_frame, columns=stock_columns, show='headings', height=10)
        for col in stock_columns:
            self.stock_tree.heading(col, text=col)
            self.stock_tree.column(col, width=80, anchor=tk.CENTER)
        self.stock_tree.column('Category', width=120, anchor=tk.W)
        self.stock_tree.column('SKU', width=120, anchor=tk.W)

        stock_scroll = ttk.Scrollbar(stock_display_frame, orient=tk.VERTICAL, command=self.stock_tree.yview)
        self.stock_tree.configure(yscrollcommand=stock_scroll.set)
        self.stock_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        stock_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        tk.Button(right_frame, text="Refresh Stock", command=self.refresh_stock, bg="#3498db", fg="white", width=20).grid(row=5, column=0, columnspan=2, pady=5)

        left_frame.grid_rowconfigure(9, weight=1)
        left_frame.grid_columnconfigure(1, weight=1)
        right_frame.grid_columnconfigure(1, weight=1)
        right_frame.grid_rowconfigure(4, weight=1)

    def load_products(self):
        """Load sanitary products into treeview and dropdown"""
        self.products = SanitaryProductRepository.get_all(
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
                    f"Rs. {product.purchase_price:.0f}",
                    f"Rs. {product.sale_price:.0f}"
                ))

        self.update_stock_dropdown()
        self.refresh_stock()

    def update_stock_dropdown(self):
        """Update stock product dropdown"""
        if hasattr(self, 'stock_product_combo'):
            all_products = SanitaryProductRepository.get_all()
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
            sku = self.sku_entry.get().strip()
            purchase_price = float(self.purchase_entry.get().strip() or "0")
            sale_price = float(self.sale_entry.get().strip() or "0")

            if self.editing_product_id:
                SanitaryService.update_product(
                    self.editing_product_id, company, category, color,
                    purchase_price, sale_price, sku
                )
                messagebox.showinfo("Success", "Sanitary product updated successfully!")
                self.editing_product_id = None
                self.add_update_btn.config(text="Add Sanitary Product", bg="#3498db")
            else:
                SanitaryService.add_product(company, category, color, purchase_price, sale_price, sku)
                messagebox.showinfo("Success", "Sanitary product added successfully!")

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
        self.sku_entry.delete(0, tk.END)
        self.sku_entry.insert(0, product.sku)
        self.purchase_entry.delete(0, tk.END)
        self.purchase_entry.insert(0, str(int(product.purchase_price)))
        self.sale_entry.delete(0, tk.END)
        self.sale_entry.insert(0, str(int(product.sale_price)))

        self.editing_product_id = product.id
        self.add_update_btn.config(text="Update Sanitary Product", bg="#f39c12")

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
                SanitaryService.delete_product(product.id)
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
        self.sku_entry.delete(0, tk.END)
        self.purchase_entry.delete(0, tk.END)
        self.sale_entry.delete(0, tk.END)
        self.editing_product_id = None
        self.add_update_btn.config(text="Add Sanitary Product", bg="#3498db")

    def add_stock(self):
        """Add stock for a sanitary product"""
        try:
            branch_id, product, quantity = self.get_stock_inputs(self.stock_in_qty_entry)
            if not AuthenticationService.can_access_branch(self.current_user, branch_id):
                raise ValueError("You do not have access to this branch")

            SanitaryService.add_stock(branch_id, product.id, quantity, user_id=self.current_user.id)
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

            inv = SanitaryService.get_inventory(branch_id, product.id)
            available = inv.quantity if inv else 0
            if quantity > available:
                raise ValueError(f"Insufficient stock. Available: {available}, Requested: {quantity}")

            confirm = messagebox.askyesno(
                "Confirm Stock OUT",
                f"Remove {quantity} units of {product.product_category} ({product.company_name}, {product.color})?"
            )
            if not confirm:
                return

            SanitaryService.deduct_stock(branch_id, product.id, quantity, user_id=self.current_user.id)
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

        all_products = SanitaryProductRepository.get_all(
            self.filter_company_var.get(),
            self.filter_category_var.get(),
            self.filter_color_var.get()
        )

        for idx, product in enumerate(all_products, 1):
            inv = SanitaryInventoryRepository.get_by_branch_product(self.selected_branch_id, product.id)
            qty = inv.quantity if inv else 0
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
