"""
Accessory Management Window
Manage grouts, bonds, and their inventory stock
"""

import tkinter as tk
from tkinter import ttk, messagebox
from repositories.branch_repository import BranchRepository
from repositories.accessory_repository import AccessoryRepository, AccessoryInventoryRepository
from services.accessory_service import AccessoryService
from services.auth_service import AuthenticationService
from models.accessory import Accessory
from utils.searchable_combobox import SearchableCombobox


class AccessoryWindow:
    """Accessory management window for grouts and bonds"""
    
    def __init__(self, parent, current_user):
        self.parent = parent
        self.current_user = current_user
        
        self.branches = BranchRepository.get_all()
        self.accessories = AccessoryRepository.get_all()
        self.selected_branch_id = None
        self.selected_accessory_id = None
        self.editing_accessory_id = None
        
        # Filter branches for employees
        if AuthenticationService.is_employee(self.current_user):
            self.branches = [b for b in self.branches if b.id == self.current_user.branch_id]
            if self.branches:
                self.selected_branch_id = self.branches[0].id
        
        self.setup_ui()
        self.load_accessories()
        
        # Set branch if employee
        if AuthenticationService.is_employee(self.current_user) and self.branches:
            self.branch_var.set(self.branches[0].name)
            self.selected_branch_id = self.branches[0].id
    
    def setup_ui(self):
        """Setup the accessory UI"""
        # Header
        header = tk.Label(
            self.parent,
            text="🛠️ Accessories Management",
            font=("Arial", 18, "bold"),
            bg="#8e44ad",
            fg="white",
            pady=10
        )
        header.pack(fill=tk.X)
        
        # Main container
        main_frame = tk.Frame(self.parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel - Accessory Management
        left_frame = tk.LabelFrame(main_frame, text="Accessory Management", font=("Arial", 12, "bold"), padx=10, pady=10)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Accessory form
        tk.Label(left_frame, text="Category:", font=("Arial", 10)).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.category_var = tk.StringVar(value=Accessory.CATEGORY_GROUT)
        category_combo = ttk.Combobox(left_frame, textvariable=self.category_var, width=27, state="readonly", font=("Arial", 10))
        category_combo['values'] = Accessory.VALID_CATEGORIES
        category_combo.grid(row=0, column=1, pady=5, padx=5)
        category_combo.bind('<<ComboboxSelected>>', self.on_category_filter)
        
        tk.Label(left_frame, text="Company/Details:", font=("Arial", 10)).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.company_entry = tk.Entry(left_frame, width=30, font=("Arial", 10))
        self.company_entry.grid(row=1, column=1, pady=5, padx=5)
        
        tk.Label(left_frame, text="Unit Price (Rs.):", font=("Arial", 10)).grid(row=2, column=0, sticky=tk.W, pady=5)
        self.unit_price_entry = tk.Entry(left_frame, width=30, font=("Arial", 10))
        self.unit_price_entry.grid(row=2, column=1, pady=5, padx=5)
        
        # Buttons
        btn_frame = tk.Frame(left_frame)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=10)
        
        self.add_update_btn = tk.Button(btn_frame, text="Add Accessory", command=self.add_or_update_accessory, bg="#3498db", fg="white", width=15)
        self.add_update_btn.pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Clear", command=self.clear_form, bg="#95a5a6", fg="white", width=15).pack(side=tk.LEFT, padx=5)
        
        # Filter label
        tk.Label(left_frame, text="Filter:", font=("Arial", 10, "bold")).grid(row=4, column=0, sticky=tk.W, pady=(10, 0))
        self.filter_var = tk.StringVar(value="All")
        self.filter_combo = SearchableCombobox(left_frame, textvariable=self.filter_var, width=27, state="normal", font=("Arial", 10))
        self.filter_combo.set_completion_list(['All', 'Grout', 'Bond', 'Floor Waste', 'Spacer'])
        self.filter_combo.grid(row=4, column=1, pady=(10, 0), padx=5)
        self.filter_combo.bind('<<ComboboxSelected>>', self.on_filter_change)
        
        # Accessories list
        tk.Label(left_frame, text="Accessories List:", font=("Arial", 10, "bold")).grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=(10, 5))
        
        # Treeview for accessories list
        tree_frame = tk.Frame(left_frame)
        tree_frame.grid(row=6, column=0, columnspan=2, sticky=tk.NSEW, pady=5)
        
        columns = ('S.No', 'Category', 'Company', 'Price')
        self.accessories_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=12)
        
        self.accessories_tree.heading('S.No', text='S.No')
        self.accessories_tree.heading('Category', text='Category')
        self.accessories_tree.heading('Company', text='Company/Details')
        self.accessories_tree.heading('Price', text='Price (Rs.)')
        
        self.accessories_tree.column('S.No', width=50, anchor=tk.CENTER)
        self.accessories_tree.column('Category', width=80, anchor=tk.CENTER)
        self.accessories_tree.column('Company', width=120, anchor=tk.W)
        self.accessories_tree.column('Price', width=100, anchor=tk.CENTER)
        
        tree_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.accessories_tree.yview)
        self.accessories_tree.configure(yscrollcommand=tree_scroll.set)
        
        self.accessories_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.accessories_tree.bind('<<TreeviewSelect>>', self.on_accessory_select)
        
        # Edit and Delete buttons (Admin only)
        action_frame = tk.Frame(left_frame)
        action_frame.grid(row=7, column=0, columnspan=2, pady=5)
        
        if AuthenticationService.can_manage_products(self.current_user):
            tk.Button(action_frame, text="Edit", command=self.edit_selected, bg="#f39c12", fg="white", width=12).pack(side=tk.LEFT, padx=5)
            tk.Button(action_frame, text="Delete", command=self.delete_selected, bg="#e74c3c", fg="white", width=12).pack(side=tk.LEFT, padx=5)
        
        # Hide form for employees
        if AuthenticationService.is_employee(self.current_user):
            for row in range(4):
                for widget in left_frame.grid_slaves(row=row):
                    widget.grid_remove()
            tk.Label(left_frame, text="Accessory management is restricted to administrators.",
                    font=("Arial", 10), fg="red").grid(row=0, column=0, columnspan=2, pady=20)
        
        # Right panel - Stock Management
        right_frame = tk.LabelFrame(main_frame, text="Stock Management", font=("Arial", 12, "bold"), padx=10, pady=10)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # Branch selection
        tk.Label(right_frame, text="Select Branch:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.branch_var = tk.StringVar()
        self.branch_combo = SearchableCombobox(right_frame, textvariable=self.branch_var, width=27, state="normal", font=("Arial", 10))
        self.branch_combo.set_completion_list([f"{b.name}" for b in self.branches])
        self.branch_combo.grid(row=0, column=1, pady=5, padx=5, sticky=tk.W)
        self.branch_combo.bind('<<ComboboxSelected>>', self.on_branch_select)
        
        if AuthenticationService.is_employee(self.current_user):
            self.branch_combo.config(state="disabled")
        
        # Accessory selection for stock
        tk.Label(right_frame, text="Select Accessory:", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.stock_accessory_var = tk.StringVar()
        self.stock_accessory_combo = SearchableCombobox(right_frame, textvariable=self.stock_accessory_var, width=45, state="normal", font=("Arial", 10))
        self.stock_accessory_combo.grid(row=1, column=1, pady=5, padx=5, sticky=tk.W)
        self.stock_accessory_combo.bind('<<ComboboxSelected>>', self.on_stock_accessory_select)
        self.update_stock_dropdown()
        
        # Stock IN
        stock_in_frame = tk.LabelFrame(right_frame, text="Stock IN (Add Stock)", font=("Arial", 10, "bold"), padx=5, pady=5)
        stock_in_frame.grid(row=2, column=0, columnspan=2, sticky=tk.EW, pady=10)
        
        tk.Label(stock_in_frame, text="Quantity:", font=("Arial", 9)).grid(row=0, column=0, sticky=tk.W, pady=3)
        self.stock_in_qty_entry = tk.Entry(stock_in_frame, width=20, font=("Arial", 9))
        self.stock_in_qty_entry.grid(row=0, column=1, pady=3, padx=5)
        
        tk.Button(stock_in_frame, text="Add Stock", command=self.add_stock, bg="#27ae60", fg="white", width=20).grid(row=1, column=0, columnspan=2, pady=10)
        
        # Stock OUT
        stock_out_frame = tk.LabelFrame(right_frame, text="Stock OUT (Remove Stock)", font=("Arial", 10, "bold"), padx=5, pady=5)
        stock_out_frame.grid(row=3, column=0, columnspan=2, sticky=tk.EW, pady=10)
        
        tk.Label(stock_out_frame, text="Quantity:", font=("Arial", 9)).grid(row=0, column=0, sticky=tk.W, pady=3)
        self.stock_out_qty_entry = tk.Entry(stock_out_frame, width=20, font=("Arial", 9))
        self.stock_out_qty_entry.grid(row=0, column=1, pady=3, padx=5)
        
        tk.Button(stock_out_frame, text="Remove Stock", command=self.remove_stock, bg="#e74c3c", fg="white", width=20).grid(row=1, column=0, columnspan=2, pady=10)
        
        # Current Stock Display
        stock_display_frame = tk.LabelFrame(right_frame, text="Current Stock", font=("Arial", 10, "bold"), padx=5, pady=5)
        stock_display_frame.grid(row=4, column=0, columnspan=2, sticky=tk.NSEW, pady=10)
        
        # Stock treeview
        stock_columns = ('S.No', 'Category', 'Company', 'Price', 'Quantity', 'Total Value')
        self.stock_tree = ttk.Treeview(stock_display_frame, columns=stock_columns, show='headings', height=10)
        
        self.stock_tree.heading('S.No', text='S.No')
        self.stock_tree.heading('Category', text='Category')
        self.stock_tree.heading('Company', text='Company/Details')
        self.stock_tree.heading('Price', text='Price (Rs.)')
        self.stock_tree.heading('Quantity', text='Qty')
        self.stock_tree.heading('Total Value', text='Total Value')
        
        self.stock_tree.column('S.No', width=50, anchor=tk.CENTER)
        self.stock_tree.column('Category', width=70, anchor=tk.CENTER)
        self.stock_tree.column('Company', width=100, anchor=tk.W)
        self.stock_tree.column('Price', width=80, anchor=tk.CENTER)
        self.stock_tree.column('Quantity', width=60, anchor=tk.CENTER)
        self.stock_tree.column('Total Value', width=100, anchor=tk.CENTER)
        
        stock_scroll = ttk.Scrollbar(stock_display_frame, orient=tk.VERTICAL, command=self.stock_tree.yview)
        self.stock_tree.configure(yscrollcommand=stock_scroll.set)
        
        self.stock_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        stock_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        tk.Button(right_frame, text="Refresh Stock", command=self.refresh_stock, bg="#3498db", fg="white", width=20).grid(row=5, column=0, columnspan=2, pady=5)
        
        # Configure grid weights
        left_frame.grid_rowconfigure(6, weight=1)
        left_frame.grid_columnconfigure(1, weight=1)
        right_frame.grid_columnconfigure(1, weight=1)
        right_frame.grid_rowconfigure(4, weight=1)
    
    def load_accessories(self):
        """Load accessories into treeview and dropdown"""
        filter_val = self.filter_var.get() if hasattr(self, 'filter_var') else 'All'
        
        if filter_val == 'All':
            self.accessories = AccessoryRepository.get_all()
        else:
            self.accessories = AccessoryRepository.get_by_category(filter_val)
        
        # Update treeview
        if hasattr(self, 'accessories_tree'):
            for item in self.accessories_tree.get_children():
                self.accessories_tree.delete(item)
            
            for idx, acc in enumerate(self.accessories, 1):
                self.accessories_tree.insert('', tk.END, values=(
                    idx,
                    acc.category,
                    acc.company,
                    f"Rs. {acc.unit_price:.0f}"
                ))
        
        self.update_stock_dropdown()
    
    def update_stock_dropdown(self):
        """Update the stock accessory dropdown"""
        if hasattr(self, 'stock_accessory_combo'):
            all_accessories = AccessoryRepository.get_all()
            values = [f"{a.category} - {a.company} (Rs. {a.unit_price:.0f})" for a in all_accessories]
            self.stock_accessory_combo.set_completion_list(values)
            self._stock_accessories = all_accessories
    
    def on_accessory_select(self, event):
        """Handle accessory selection"""
        selection = self.accessories_tree.selection()
        if selection:
            item = self.accessories_tree.item(selection[0])
            values = item['values']
            # Find matching accessory
            for acc in self.accessories:
                if acc.category == values[1] and acc.company == values[2]:
                    self.selected_accessory_id = acc.id
                    break
    
    def on_branch_select(self, event):
        """Handle branch selection"""
        selected = self.branch_var.get()
        for branch in self.branches:
            if branch.name == selected:
                self.selected_branch_id = branch.id
                break
        self.refresh_stock()
    
    def on_stock_accessory_select(self, event):
        """Handle stock accessory selection"""
        idx = self.stock_accessory_combo.current()
        if idx >= 0 and hasattr(self, '_stock_accessories'):
            self.selected_accessory_id = self._stock_accessories[idx].id
    
    def on_category_filter(self, event):
        """Handle category filter in form"""
        pass  # Category selection in form doesn't filter
    
    def on_filter_change(self, event):
        """Handle filter change"""
        self.load_accessories()
    
    def add_or_update_accessory(self):
        """Add or update an accessory"""
        try:
            category = self.category_var.get()
            company = self.company_entry.get().strip()
            price_str = self.unit_price_entry.get().strip()
            
            if not company:
                raise ValueError("Please enter a company name")
            if not price_str:
                raise ValueError("Please enter a unit price")
            
            try:
                unit_price = float(price_str)
            except ValueError:
                raise ValueError("Unit price must be a number")
            
            if unit_price < 0:
                raise ValueError("Unit price cannot be negative")
            
            if self.editing_accessory_id:
                AccessoryService.update_accessory(
                    self.editing_accessory_id,
                    name=category,
                    category=category,
                    company=company,
                    unit_price=unit_price
                )
                messagebox.showinfo("Success", f"{category} by {company} updated successfully!")
                self.editing_accessory_id = None
                self.add_update_btn.config(text="Add Accessory", bg="#3498db")
            else:
                AccessoryService.add_accessory(
                    name=category,
                    category=category,
                    company=company,
                    unit_price=unit_price
                )
                messagebox.showinfo("Success", f"{category} by {company} added successfully!")
            
            self.clear_form()
            self.load_accessories()
            
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def edit_selected(self):
        """Edit selected accessory"""
        selection = self.accessories_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select an accessory to edit")
            return
        
        try:
            item = self.accessories_tree.item(selection[0])
            values = item['values']
            
            # Find the accessory
            acc = None
            for a in self.accessories:
                if a.category == values[1] and a.company == values[2]:
                    acc = a
                    break
            
            if not acc:
                raise ValueError("Accessory not found")
            
            # Fill form
            self.category_var.set(acc.category)
            self.company_entry.delete(0, tk.END)
            self.company_entry.insert(0, acc.company)
            self.unit_price_entry.delete(0, tk.END)
            self.unit_price_entry.insert(0, str(int(acc.unit_price)))
            
            self.editing_accessory_id = acc.id
            self.add_update_btn.config(text="Update Accessory", bg="#f39c12")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load accessory: {str(e)}")
    
    def delete_selected(self):
        """Delete selected accessory"""
        selection = self.accessories_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select an accessory to delete")
            return
        
        try:
            item = self.accessories_tree.item(selection[0])
            values = item['values']
            
            acc = None
            for a in self.accessories:
                if a.category == values[1] and a.company == values[2]:
                    acc = a
                    break
            
            if not acc:
                raise ValueError("Accessory not found")
            
            confirm = messagebox.askyesno(
                "Confirm Delete",
                f"Are you sure you want to delete {acc.category} by {acc.company} (Rs. {acc.unit_price:.0f})?\n\n"
                f"This action cannot be undone."
            )
            
            if confirm:
                AccessoryService.delete_accessory(acc.id)
                messagebox.showinfo("Success", f"{acc.category} by {acc.company} deleted successfully!")
                self.clear_form()
                self.load_accessories()
                self.refresh_stock()
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete: {str(e)}")
    
    def clear_form(self):
        """Clear the form"""
        self.category_var.set(Accessory.CATEGORY_GROUT)
        self.company_entry.delete(0, tk.END)
        self.unit_price_entry.delete(0, tk.END)
        self.editing_accessory_id = None
        self.add_update_btn.config(text="Add Accessory", bg="#3498db")
    
    def add_stock(self):
        """Add stock for an accessory"""
        try:
            if not self.selected_branch_id:
                raise ValueError("Please select a branch")
            
            acc_str = self.stock_accessory_var.get()
            if not acc_str:
                raise ValueError("Please select an accessory")
            
            idx = self.stock_accessory_combo.current()
            if idx < 0 or not hasattr(self, '_stock_accessories'):
                raise ValueError("Please select an accessory from the dropdown")
            
            accessory = self._stock_accessories[idx]
            
            qty_str = self.stock_in_qty_entry.get().strip()
            if not qty_str:
                raise ValueError("Please enter a quantity")
            
            try:
                quantity = int(qty_str)
            except ValueError:
                raise ValueError("Quantity must be a whole number")
            
            if quantity <= 0:
                raise ValueError("Quantity must be positive")
            
            if not AuthenticationService.can_access_branch(self.current_user, self.selected_branch_id):
                raise ValueError("You do not have access to this branch")
            
            AccessoryService.add_stock(self.selected_branch_id, accessory.id, quantity)
            messagebox.showinfo("Success", f"Added {quantity} units of {accessory.category} ({accessory.company}) to stock!")
            
            self.stock_in_qty_entry.delete(0, tk.END)
            self.refresh_stock()
            
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def remove_stock(self):
        """Remove stock for an accessory"""
        try:
            if not self.selected_branch_id:
                raise ValueError("Please select a branch")
            
            acc_str = self.stock_accessory_var.get()
            if not acc_str:
                raise ValueError("Please select an accessory")
            
            idx = self.stock_accessory_combo.current()
            if idx < 0 or not hasattr(self, '_stock_accessories'):
                raise ValueError("Please select an accessory from the dropdown")
            
            accessory = self._stock_accessories[idx]
            
            qty_str = self.stock_out_qty_entry.get().strip()
            if not qty_str:
                raise ValueError("Please enter a quantity")
            
            try:
                quantity = int(qty_str)
            except ValueError:
                raise ValueError("Quantity must be a whole number")
            
            if quantity <= 0:
                raise ValueError("Quantity must be positive")
            
            if not AuthenticationService.can_access_branch(self.current_user, self.selected_branch_id):
                raise ValueError("You do not have access to this branch")
            
            # Check stock
            inv = AccessoryService.get_inventory(self.selected_branch_id, accessory.id)
            current_qty = inv.quantity if inv else 0
            
            if quantity > current_qty:
                raise ValueError(f"Insufficient stock. Available: {current_qty}, Requested: {quantity}")
            
            confirm = messagebox.askyesno(
                "Confirm Stock OUT",
                f"Remove {quantity} units of {accessory.category} ({accessory.company})?"
            )
            
            if not confirm:
                return
            
            AccessoryService.deduct_stock(self.selected_branch_id, accessory.id, quantity)
            messagebox.showinfo("Success", f"Removed {quantity} units of {accessory.category} ({accessory.company}) from stock!")
            
            self.stock_out_qty_entry.delete(0, tk.END)
            self.refresh_stock()
            
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def refresh_stock(self):
        """Refresh stock display"""
        # Clear stock tree
        for item in self.stock_tree.get_children():
            self.stock_tree.delete(item)
        
        if not self.selected_branch_id:
            return
        
        # Get all accessory inventory for this branch
        all_accessories = AccessoryRepository.get_all()
        
        for idx, acc in enumerate(all_accessories, 1):
            inv = AccessoryInventoryRepository.get_by_branch_accessory(self.selected_branch_id, acc.id)
            qty = inv.quantity if inv else 0
            total_value = qty * acc.unit_price
            
            self.stock_tree.insert('', tk.END, values=(
                idx,
                acc.category,
                acc.company,
                f"Rs. {acc.unit_price:.0f}",
                qty,
                f"Rs. {total_value:.0f}"
            ))
