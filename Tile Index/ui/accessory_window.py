"""
Accessory Management Window
Manage grouts, bonds, and their inventory stock
"""

import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
from repositories.branch_repository import BranchRepository
from repositories.accessory_repository import AccessoryRepository, AccessoryInventoryRepository
from services.accessory_service import AccessoryService
from services.auth_service import AuthenticationService
from models.accessory import Accessory
from utils.searchable_combobox import SearchableCombobox
from utils.accessory_labels import accessory_display_label
from ui.theme import COLORS, FONTS, SIZES, SPACING


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
        header = ctk.CTkLabel(
            self.parent,
            text="Accessories Management",
            font=FONTS["section"],
            fg_color=COLORS["surface"],
            text_color=COLORS["text"],
            height=48,
        )
        header.pack(fill=tk.X)

        main_frame = ctk.CTkFrame(self.parent, fg_color=COLORS["app_bg"], corner_radius=0)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=SPACING["page_x"], pady=SPACING["page_y"])

        left_frame = self.panel(main_frame, "Accessory Management")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        self.form_label(left_frame, "Category:").grid(row=1, column=0, sticky=tk.W, pady=5, padx=(12, 8))
        self.category_var = tk.StringVar(value=Accessory.CATEGORY_GROUT)
        category_combo = ttk.Combobox(left_frame, textvariable=self.category_var, width=SIZES["compact_dropdown_width"], state="readonly", font=FONTS["small"])
        category_combo['values'] = Accessory.VALID_CATEGORIES
        category_combo.grid(row=1, column=1, pady=5, padx=(0, 12), sticky=tk.W)
        category_combo.bind('<<ComboboxSelected>>', self.on_category_filter)

        self.form_label(left_frame, "Company/Details:").grid(row=2, column=0, sticky=tk.W, pady=5, padx=(12, 8))
        self.company_entry = self.form_entry(left_frame, width=280)
        self.company_entry.grid(row=2, column=1, pady=5, padx=(0, 12), sticky=tk.W)

        self.form_label(left_frame, "Unit Price (Rs.):").grid(row=3, column=0, sticky=tk.W, pady=5, padx=(12, 8))
        self.unit_price_entry = self.form_entry(left_frame, width=180)
        self.unit_price_entry.grid(row=3, column=1, pady=5, padx=(0, 12), sticky=tk.W)

        btn_frame = ctk.CTkFrame(left_frame, fg_color="transparent", corner_radius=0)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=10)

        self.add_update_btn = self.action_button(btn_frame, "Add Accessory", self.add_or_update_accessory, width=145)
        self.add_update_btn.pack(side=tk.LEFT, padx=5)
        self.action_button(btn_frame, "Clear", self.clear_form, width=120, primary=False).pack(side=tk.LEFT, padx=5)

        self.form_label(left_frame, "Filter:", bold=True).grid(row=5, column=0, sticky=tk.W, pady=(10, 0), padx=(12, 8))
        self.filter_var = tk.StringVar(value="All")
        self.filter_combo = SearchableCombobox(left_frame, textvariable=self.filter_var, width=SIZES["compact_dropdown_width"], state="normal", font=FONTS["small"])
        self.filter_combo.set_completion_list(['All', 'Grout', 'Bond', 'Floor Waste', 'Spacer'])
        self.filter_combo.grid(row=5, column=1, pady=(10, 0), padx=(0, 12), sticky=tk.W)
        self.filter_combo.bind('<<ComboboxSelected>>', self.on_filter_change)

        self.form_label(left_frame, "Accessories List:", bold=True).grid(row=6, column=0, columnspan=2, sticky=tk.W, pady=(10, 5), padx=12)

        tree_frame = ctk.CTkFrame(left_frame, fg_color=COLORS["surface"], corner_radius=SIZES["corner_radius"], border_width=1, border_color=COLORS["border"])
        tree_frame.grid(row=7, column=0, columnspan=2, sticky=tk.NSEW, pady=5, padx=12)
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        columns = ('S.No', 'Category', 'Company', 'Price')
        self.accessories_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=12)

        self.accessories_tree.heading('S.No', text='S.No')
        self.accessories_tree.heading('Category', text='Category')
        self.accessories_tree.heading('Company', text='Accessory')
        self.accessories_tree.heading('Price', text='Price (Rs.)')

        self.accessories_tree.column('S.No', width=50, anchor=tk.CENTER)
        self.accessories_tree.column('Category', width=80, anchor=tk.CENTER)
        self.accessories_tree.column('Company', width=280, anchor=tk.W)
        self.accessories_tree.column('Price', width=100, anchor=tk.CENTER)

        tree_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.accessories_tree.yview)
        self.accessories_tree.configure(yscrollcommand=tree_scroll.set)

        self.accessories_tree.grid(row=0, column=0, sticky=tk.NSEW, padx=(1, 0), pady=1)
        tree_scroll.grid(row=0, column=1, sticky=tk.NS, pady=1)

        self.accessories_tree.bind('<<TreeviewSelect>>', self.on_accessory_select)

        action_frame = ctk.CTkFrame(left_frame, fg_color="transparent", corner_radius=0)
        action_frame.grid(row=8, column=0, columnspan=2, pady=(5, 12))

        if AuthenticationService.can_manage_products(self.current_user):
            self.action_button(action_frame, "Edit", self.edit_selected, width=110).pack(side=tk.LEFT, padx=5)
            self.action_button(action_frame, "Delete", self.delete_selected, width=110, danger=True).pack(side=tk.LEFT, padx=5)

        if AuthenticationService.is_employee(self.current_user):
            for row in range(1, 5):
                for widget in left_frame.grid_slaves(row=row):
                    widget.grid_remove()
            ctk.CTkLabel(
                left_frame,
                text="Accessory management is restricted to administrators.",
                font=FONTS["small_bold"],
                text_color=COLORS["danger"],
                height=SIZES["small_label_height"],
            ).grid(row=1, column=0, columnspan=2, pady=20)

        right_frame = self.panel(main_frame, "Stock Management")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

        self.form_label(right_frame, "Select Branch:", bold=True).grid(row=1, column=0, sticky=tk.W, pady=5, padx=(12, 8))
        self.branch_var = tk.StringVar()
        self.branch_combo = SearchableCombobox(right_frame, textvariable=self.branch_var, width=SIZES["compact_dropdown_width"], state="normal", font=FONTS["small"])
        self.branch_combo.set_completion_list([f"{b.name}" for b in self.branches])
        self.branch_combo.grid(row=1, column=1, pady=5, padx=(0, 12), sticky=tk.W)
        self.branch_combo.bind('<<ComboboxSelected>>', self.on_branch_select)

        if AuthenticationService.is_employee(self.current_user):
            self.branch_combo.config(state="disabled")

        self.form_label(right_frame, "Select Accessory:", bold=True).grid(row=2, column=0, sticky=tk.W, pady=5, padx=(12, 8))
        self.stock_accessory_var = tk.StringVar()
        self.stock_accessory_combo = SearchableCombobox(right_frame, textvariable=self.stock_accessory_var, width=SIZES["dropdown_width"], state="normal", font=FONTS["small"])
        self.stock_accessory_combo.grid(row=2, column=1, pady=5, padx=(0, 12), sticky=tk.W)
        self.stock_accessory_combo.bind('<<ComboboxSelected>>', self.on_stock_accessory_select)
        self.update_stock_dropdown()

        stock_in_frame = self.subpanel(right_frame, "Stock IN (Add Stock)")
        stock_in_frame.grid(row=3, column=0, columnspan=2, sticky=tk.EW, pady=10, padx=12)

        self.form_label(stock_in_frame, "Quantity:").grid(row=1, column=0, sticky=tk.W, pady=3, padx=8)
        self.stock_in_qty_entry = self.form_entry(stock_in_frame, width=160)
        self.stock_in_qty_entry.grid(row=1, column=1, pady=3, padx=8, sticky=tk.W)

        self.action_button(stock_in_frame, "Add Stock", self.add_stock, width=160).grid(row=2, column=0, columnspan=2, pady=10)

        stock_out_frame = self.subpanel(right_frame, "Stock OUT (Remove Stock)")
        stock_out_frame.grid(row=4, column=0, columnspan=2, sticky=tk.EW, pady=10, padx=12)

        self.form_label(stock_out_frame, "Quantity:").grid(row=1, column=0, sticky=tk.W, pady=3, padx=8)
        self.stock_out_qty_entry = self.form_entry(stock_out_frame, width=160)
        self.stock_out_qty_entry.grid(row=1, column=1, pady=3, padx=8, sticky=tk.W)

        self.action_button(stock_out_frame, "Remove Stock", self.remove_stock, width=160, danger=True).grid(row=2, column=0, columnspan=2, pady=10)

        stock_display_frame = self.subpanel(right_frame, "Current Stock")
        stock_display_frame.grid(row=5, column=0, columnspan=2, sticky=tk.NSEW, pady=10, padx=12)
        stock_display_frame.grid_rowconfigure(1, weight=1)
        stock_display_frame.grid_columnconfigure(0, weight=1)

        stock_columns = ('S.No', 'Category', 'Company', 'Price', 'Quantity', 'Total Value')
        self.stock_tree = ttk.Treeview(stock_display_frame, columns=stock_columns, show='headings', height=10)

        self.stock_tree.heading('S.No', text='S.No')
        self.stock_tree.heading('Category', text='Category')
        self.stock_tree.heading('Company', text='Accessory')
        self.stock_tree.heading('Price', text='Price (Rs.)')
        self.stock_tree.heading('Quantity', text='Qty')
        self.stock_tree.heading('Total Value', text='Total Value')

        self.stock_tree.column('S.No', width=50, anchor=tk.CENTER)
        self.stock_tree.column('Category', width=70, anchor=tk.CENTER)
        self.stock_tree.column('Company', width=280, anchor=tk.W)
        self.stock_tree.column('Price', width=80, anchor=tk.CENTER)
        self.stock_tree.column('Quantity', width=60, anchor=tk.CENTER)
        self.stock_tree.column('Total Value', width=100, anchor=tk.CENTER)

        stock_scroll = ttk.Scrollbar(stock_display_frame, orient=tk.VERTICAL, command=self.stock_tree.yview)
        self.stock_tree.configure(yscrollcommand=stock_scroll.set)

        self.stock_tree.grid(row=1, column=0, sticky=tk.NSEW, padx=(8, 0), pady=(0, 8))
        stock_scroll.grid(row=1, column=1, sticky=tk.NS, padx=(0, 8), pady=(0, 8))

        self.action_button(right_frame, "Refresh Stock", self.refresh_stock, width=160).grid(row=6, column=0, columnspan=2, pady=(5, 12))

        left_frame.grid_rowconfigure(7, weight=1)
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
        ).grid(row=0, column=0, columnspan=2, sticky=tk.EW, padx=8, pady=(8, 4))
        panel.grid_columnconfigure(1, weight=1)
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
            fg_color = COLORS["danger"]
            hover_color = COLORS["danger_hover"]
        elif primary:
            fg_color = COLORS["primary"]
            hover_color = COLORS["primary_hover"]
        else:
            fg_color = COLORS["card"]
            hover_color = COLORS["card_hover"]
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
                    accessory_display_label(acc),
                    f"Rs. {acc.unit_price:.0f}"
                ), iid=str(acc.id))
        
        self.update_stock_dropdown()
    
    def update_stock_dropdown(self):
        """Update the stock accessory dropdown"""
        if hasattr(self, 'stock_accessory_combo'):
            all_accessories = AccessoryRepository.get_all()
            values = [f"{a.category} - {accessory_display_label(a)} (Rs. {a.unit_price:.0f})" for a in all_accessories]
            self.stock_accessory_combo.set_completion_list(values)
            self._stock_accessories = all_accessories
    
    def on_accessory_select(self, event):
        """Handle accessory selection"""
        selection = self.accessories_tree.selection()
        if selection:
            self.selected_accessory_id = int(selection[0])
    
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
                self.add_update_btn.configure(text="Add Accessory", fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"])
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
                if a.id == int(selection[0]):
                    acc = a
                    break
            
            if not acc:
                raise ValueError("Accessory not found")
            
            # Fill form
            self.category_var.set(acc.category)
            self.company_entry.delete(0, tk.END)
            self.company_entry.insert(0, acc.company or "")
            self.unit_price_entry.delete(0, tk.END)
            self.unit_price_entry.insert(0, str(int(acc.unit_price)))
            
            self.editing_accessory_id = acc.id
            self.add_update_btn.configure(text="Update Accessory", fg_color=COLORS["warning"], hover_color=COLORS["warning_hover"])
            
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
                if a.id == int(selection[0]):
                    acc = a
                    break
            
            if not acc:
                raise ValueError("Accessory not found")
            
            label = accessory_display_label(acc)
            confirm = messagebox.askyesno(
                "Confirm Delete",
                f"Are you sure you want to delete {acc.category} - {label} (Rs. {acc.unit_price:.0f})?\n\n"
                f"This action cannot be undone."
            )
            
            if confirm:
                AccessoryService.delete_accessory(acc.id)
                messagebox.showinfo("Success", f"{acc.category} - {label} deleted successfully!")
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
        self.add_update_btn.configure(text="Add Accessory", fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"])
    
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
            label = accessory_display_label(accessory)
            messagebox.showinfo("Success", f"Added {quantity} units of {accessory.category} - {label} to stock!")
            
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
            
            label = accessory_display_label(accessory)
            confirm = messagebox.askyesno(
                "Confirm Stock OUT",
                f"Remove {quantity} units of {accessory.category} - {label}?"
            )
            
            if not confirm:
                return
            
            AccessoryService.deduct_stock(self.selected_branch_id, accessory.id, quantity)
            messagebox.showinfo("Success", f"Removed {quantity} units of {accessory.category} - {label} from stock!")
            
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
                accessory_display_label(acc),
                f"Rs. {acc.unit_price:.0f}",
                qty,
                f"Rs. {total_value:.0f}"
            ))
