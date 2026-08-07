"""
Inventory Management Window
Manage products and inventory stock
"""

import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
from repositories.branch_repository import BranchRepository
from repositories.product_repository import ProductRepository
from services.inventory_service import InventoryService
from services.auth_service import AuthenticationService
from models.product import Product
from utils.validators import validate_positive_number, validate_integer, validate_required, validate_grade
from utils.grade_constants import VALID_GRADES, GRADE_1
from utils.searchable_combobox import SearchableCombobox
from desktop_client.remote_state import is_api_authenticated
from ui.theme import COLORS, FONTS, SIZES, SPACING


class InventoryWindow:
    """Inventory management window"""
    
    def __init__(self, parent, current_user):
        self.parent = parent
        self.current_user = current_user
        
        self.branches = BranchRepository.get_all()
        self.products = ProductRepository.get_all()
        self.selected_branch_id = None
        self.selected_product_id = None
        self.editing_product_id = None  # Track if we're editing a product
        
        # Filter branches for employees
        from services.auth_service import AuthenticationService
        if AuthenticationService.is_employee(self.current_user):
            # Employee can only see their assigned branch
            self.branches = [b for b in self.branches if b.id == self.current_user.branch_id]
            if self.branches:
                self.selected_branch_id = self.branches[0].id
        
        self.setup_ui()
        self.load_products()
        
        # Set branch if employee
        if AuthenticationService.is_employee(self.current_user) and self.branches:
            self.branch_var.set(self.branches[0].name)
            self.selected_branch_id = self.branches[0].id
    
    def setup_ui(self):
        """Setup the inventory UI"""
        # Header
        header = ctk.CTkLabel(
            self.parent,
            text="Inventory Management",
            font=FONTS["section"],
            fg_color=COLORS["surface"],
            text_color=COLORS["text"],
            height=48,
        )
        header.pack(fill=tk.X)
        
        # Main container
        main_frame = ctk.CTkFrame(self.parent, fg_color=COLORS["app_bg"], corner_radius=0)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=SPACING["page_x"], pady=SPACING["page_y"])
        
        # Left panel - Product Management
        left_frame = ctk.CTkFrame(
            main_frame,
            fg_color=COLORS["surface"],
            corner_radius=SIZES["corner_radius"],
            border_width=1,
            border_color=COLORS["border"],
        )
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        ctk.CTkLabel(
            left_frame,
            text="Product Management",
            font=FONTS["body_bold"],
            text_color=COLORS["text"],
            height=SIZES["section_label_height"],
        ).grid(row=0, column=0, columnspan=2, sticky=tk.EW, padx=12, pady=(10, 8))
        
        # Product form
        self.form_label(left_frame, "Product Name:").grid(row=1, column=0, sticky=tk.W, pady=5, padx=(12, 0))
        self.product_name_entry = self.form_entry(left_frame)
        self.product_name_entry.grid(row=1, column=1, pady=5, padx=(5, 12), sticky=tk.EW)
        
        self.form_label(left_frame, "Tile Size:").grid(row=2, column=0, sticky=tk.W, pady=5, padx=(12, 0))
        self.tile_size_entry = self.form_entry(left_frame)
        self.tile_size_entry.grid(row=2, column=1, pady=5, padx=(5, 12), sticky=tk.EW)
        
        self.form_label(left_frame, "Area per Box (m²):").grid(row=3, column=0, sticky=tk.W, pady=5, padx=(12, 0))
        self.area_per_box_entry = self.form_entry(left_frame)
        self.area_per_box_entry.grid(row=3, column=1, pady=5, padx=(5, 12), sticky=tk.EW)
        
        self.form_label(left_frame, "Pieces per Box:").grid(row=4, column=0, sticky=tk.W, pady=5, padx=(12, 0))
        self.pieces_per_box_entry = self.form_entry(left_frame)
        self.pieces_per_box_entry.grid(row=4, column=1, pady=5, padx=(5, 12), sticky=tk.EW)
        
        # Product buttons
        product_btn_frame = ctk.CTkFrame(left_frame, fg_color="transparent", corner_radius=0)
        product_btn_frame.grid(row=5, column=0, columnspan=2, pady=10)
        
        self.add_update_btn = self.action_button(product_btn_frame, "Add Product", self.add_or_update_product, width=140)
        self.add_update_btn.pack(side=tk.LEFT, padx=5)
        self.action_button(product_btn_frame, "Clear", self.clear_product_form, width=140, primary=False).pack(side=tk.LEFT, padx=5)
        
        # Products list
        self.form_label(left_frame, "Products List:", bold=True).grid(row=6, column=0, columnspan=2, sticky=tk.W, pady=(10, 5), padx=(12, 0))
        
        products_frame = ctk.CTkFrame(left_frame, fg_color=COLORS["surface"], corner_radius=SIZES["corner_radius"], border_width=1, border_color=COLORS["border"])
        products_frame.grid(row=7, column=0, columnspan=2, sticky=tk.NSEW, pady=5, padx=12)
        
        products_scroll = ctk.CTkScrollbar(products_frame)
        products_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.products_listbox = tk.Listbox(
            products_frame,
            yscrollcommand=products_scroll.set,
            height=12,
            font=FONTS["small"],
            bg=COLORS["surface"],
            fg=COLORS["text"],
            selectbackground=COLORS["primary"],
            selectforeground=COLORS["text"],
            relief=tk.FLAT,
            highlightthickness=0,
            borderwidth=0,
            activestyle="none",
        )
        self.products_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0), pady=10)
        products_scroll.configure(command=self.products_listbox.yview)
        self.products_listbox.bind('<<ListboxSelect>>', self.on_product_select)
        
        # Edit and Delete buttons for products (Admin only)
        product_action_frame = ctk.CTkFrame(left_frame, fg_color="transparent", corner_radius=0)
        product_action_frame.grid(row=8, column=0, columnspan=2, pady=5)
        
        if AuthenticationService.can_manage_products(self.current_user):
            self.action_button(product_action_frame, "Edit Product", self.edit_selected_product, width=140, primary=False).pack(side=tk.LEFT, padx=5)
            self.action_button(product_action_frame, "Delete Product", self.delete_selected_product, width=140, primary=False).pack(side=tk.LEFT, padx=5)
        
        # Hide product management for employees
        if AuthenticationService.is_employee(self.current_user):
            # Hide product form fields
            for row in range(9):
                for widget in left_frame.grid_slaves(row=row):
                    widget.grid_remove()
            self.form_label(left_frame, "Product management is restricted to administrators.", bold=True).grid(row=0, column=0, columnspan=2, pady=50)
        
        # Right panel - Stock Management
        right_frame = ctk.CTkFrame(
            main_frame,
            fg_color=COLORS["surface"],
            corner_radius=SIZES["corner_radius"],
            border_width=1,
            border_color=COLORS["border"],
        )
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        ctk.CTkLabel(
            right_frame,
            text="Stock Management",
            font=FONTS["body_bold"],
            text_color=COLORS["text"],
            height=SIZES["section_label_height"],
        ).grid(row=0, column=0, columnspan=2, sticky=tk.EW, padx=12, pady=(10, 8))
        
        # Branch selection
        self.form_label(right_frame, "Select Branch:", bold=True).grid(row=1, column=0, sticky=tk.W, pady=5, padx=(12, 0))
        self.branch_var = tk.StringVar()
        self.branch_combo = SearchableCombobox(right_frame, textvariable=self.branch_var, width=SIZES["dropdown_width"], state="normal", font=FONTS["small"])
        self.branch_combo.set_completion_list([f"{b.name}" for b in self.branches])
        self.branch_combo.grid(row=1, column=1, pady=5, padx=(5, 12), sticky=tk.W)
        self.branch_combo.bind('<<ComboboxSelected>>', self.on_branch_select)
        
        # Disable branch selection for employees (they can only access their branch)
        if AuthenticationService.is_employee(self.current_user):
            self.branch_combo.config(state="disabled")
        
        # Product selection (for Stock IN/OUT)
        self.form_label(right_frame, "Select Product:", bold=True).grid(row=2, column=0, sticky=tk.W, pady=5, padx=(12, 0))
        self.stock_product_var = tk.StringVar()
        self.stock_product_combo = SearchableCombobox(right_frame, textvariable=self.stock_product_var, width=SIZES["dropdown_width"], state="normal", font=FONTS["small"])
        self.stock_product_combo.grid(row=2, column=1, pady=5, padx=(5, 12), sticky=tk.W)
        self.stock_product_combo.bind('<<ComboboxSelected>>', self.on_stock_product_select)
        
        # Grade selection
        self.form_label(right_frame, "Grade:").grid(row=3, column=0, sticky=tk.W, pady=5, padx=(12, 0))
        self.grade_var = tk.StringVar(value=GRADE_1)
        grade_combo = ttk.Combobox(right_frame, textvariable=self.grade_var, width=SIZES["dropdown_width"], state="readonly", font=FONTS["small"])
        grade_combo['values'] = VALID_GRADES
        grade_combo.grid(row=3, column=1, pady=5, padx=(5, 12), sticky=tk.W)
        grade_combo.bind('<<ComboboxSelected>>', lambda e: self.refresh_stock())
        
        # Stock IN form
        stock_in_frame = self.create_subpanel(right_frame, "Stock IN (Add Stock)")
        stock_in_frame.grid(row=4, column=0, columnspan=2, sticky=tk.EW, pady=10, padx=12)
        
        self.form_label(stock_in_frame, "Boxes:").grid(row=1, column=0, sticky=tk.W, pady=3, padx=8)
        self.stock_in_boxes_entry = self.form_entry(stock_in_frame, width=160)
        self.stock_in_boxes_entry.grid(row=1, column=1, pady=3, padx=8)
        
        self.form_label(stock_in_frame, "Loose Pieces:").grid(row=2, column=0, sticky=tk.W, pady=3, padx=8)
        self.stock_in_pieces_entry = self.form_entry(stock_in_frame, width=160)
        self.stock_in_pieces_entry.grid(row=2, column=1, pady=3, padx=8)
        
        self.form_label(stock_in_frame, "Rate per m² (Rs.):").grid(row=2, column=0, sticky=tk.W, pady=3)
        for widget in stock_in_frame.grid_slaves(row=2, column=0):
            try:
                if str(widget.cget("text")).startswith("Rate per"):
                    widget.grid_forget()
            except Exception:
                pass
        self.form_label(stock_in_frame, "Rate per m² (Rs.):").grid(row=3, column=0, sticky=tk.W, pady=3, padx=8)
        self.rate_sqm_entry = self.form_entry(stock_in_frame, width=160)
        self.rate_sqm_entry.grid(row=3, column=1, pady=3, padx=8)
        
        self.form_label(stock_in_frame, "Rate per Box (Rs.):").grid(row=4, column=0, sticky=tk.W, pady=3, padx=8)
        self.rate_box_entry = self.form_entry(stock_in_frame, width=160)
        self.rate_box_entry.grid(row=4, column=1, pady=3, padx=8)
        
        self.form_label(stock_in_frame, "Rate per Piece (Rs.):").grid(row=5, column=0, sticky=tk.W, pady=3, padx=8)
        self.rate_piece_entry = self.form_entry(stock_in_frame, width=160)
        self.rate_piece_entry.grid(row=5, column=1, pady=3, padx=8)
        
        self.action_button(stock_in_frame, "Add Stock", self.add_stock, width=180).grid(row=6, column=0, columnspan=2, pady=10)
        
        # Stock OUT form
        stock_out_frame = self.create_subpanel(right_frame, "Stock OUT (Remove Stock)")
        stock_out_frame.grid(row=5, column=0, columnspan=2, sticky=tk.EW, pady=10, padx=12)
        
        self.form_label(stock_out_frame, "Boxes:").grid(row=1, column=0, sticky=tk.W, pady=3, padx=8)
        self.stock_out_boxes_entry = self.form_entry(stock_out_frame, width=160)
        self.stock_out_boxes_entry.grid(row=1, column=1, pady=3, padx=8)
        
        self.form_label(stock_out_frame, "Loose Pieces:").grid(row=2, column=0, sticky=tk.W, pady=3, padx=8)
        self.stock_out_pieces_entry = self.form_entry(stock_out_frame, width=160)
        self.stock_out_pieces_entry.grid(row=2, column=1, pady=3, padx=8)
        
        self.form_label(stock_out_frame, "Reason/Comment:").grid(row=3, column=0, sticky=tk.W, pady=3, padx=8)
        self.stock_out_comment_entry = self.form_entry(stock_out_frame, width=160)
        self.stock_out_comment_entry.grid(row=3, column=1, pady=3, padx=8)
        self.stock_out_comment_entry.insert(0, "Customer return / Other reason")
        
        self.action_button(stock_out_frame, "Remove Stock", self.remove_stock, width=180, primary=False).grid(row=4, column=0, columnspan=2, pady=10)
        
        # Current Stock Display
        stock_display_frame = self.create_subpanel(right_frame, "Current Stock")
        stock_display_frame.grid(row=6, column=0, columnspan=2, sticky=tk.EW, pady=10, padx=12)
        
        self.stock_display_text = tk.Text(
            stock_display_frame,
            height=8,
            width=40,
            font=FONTS["small"],
            state=tk.DISABLED,
            bg=COLORS["surface"],
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=COLORS["border"],
            padx=8,
            pady=8,
        )
        self.stock_display_text.grid(row=1, column=0, columnspan=2, sticky=tk.NSEW, padx=8, pady=(4, 8))
        stock_display_frame.grid_rowconfigure(1, weight=1)
        stock_display_frame.grid_columnconfigure(0, weight=1)
        
        self.action_button(right_frame, "Refresh Stock", self.refresh_stock, width=180).grid(row=7, column=0, columnspan=2, pady=5)
        
        # Configure grid weights
        left_frame.grid_rowconfigure(7, weight=1)
        left_frame.grid_columnconfigure(1, weight=1)
        right_frame.grid_columnconfigure(1, weight=1)

    def create_subpanel(self, parent, title):
        """Create a compact themed section while keeping child layout unchanged."""
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
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_columnconfigure(1, weight=1)
        return panel

    def form_label(self, parent, text, bold=False):
        """Create a themed form label with enough height for the font."""
        return ctk.CTkLabel(
            parent,
            text=text,
            font=FONTS["small_bold"] if bold else FONTS["small"],
            text_color=COLORS["text"],
            height=SIZES["small_label_height"],
            anchor=tk.W,
        )

    def form_entry(self, parent, width=240):
        """Create a themed entry that keeps normal Entry get/delete/insert behavior."""
        return ctk.CTkEntry(
            parent,
            width=width,
            height=SIZES["input_height"],
            font=FONTS["small"],
            fg_color=COLORS["app_bg"],
            border_color=COLORS["border"],
            text_color=COLORS["text"],
        )

    def action_button(self, parent, text, command, width=150, primary=True):
        """Create a themed action button with the existing command callback."""
        return ctk.CTkButton(
            parent,
            text=text,
            command=command,
            width=width,
            height=34,
            fg_color=COLORS["primary"] if primary else COLORS["card"],
            hover_color=COLORS["primary_hover"] if primary else COLORS["card_hover"],
            text_color=COLORS["text"],
            font=FONTS["small_bold"],
            border_width=0 if primary else 1,
            border_color=COLORS["border"],
            corner_radius=SIZES["corner_radius"],
            cursor="hand2",
        )
    
    def load_products(self):
        """Load products into listbox and stock product dropdown"""
        self.products = ProductRepository.get_all()
        
        # Update listbox (for admin product management)
        if hasattr(self, 'products_listbox'):
            self.products_listbox.delete(0, tk.END)
            for product in self.products:
                self.products_listbox.insert(tk.END, f"{product.name} - {product.tile_size}")
        
        # Update stock product dropdown (for Stock IN/OUT)
        if hasattr(self, 'stock_product_combo'):
            product_values = [f"{p.name} - {p.tile_size}" for p in self.products]
            self.stock_product_combo.set_completion_list(product_values)
    
    def on_product_select(self, event):
        """Handle product selection"""
        selection = self.products_listbox.curselection()
        if selection:
            index = selection[0]
            self.selected_product_id = self.products[index].id
            self.refresh_stock()
    
    def on_branch_select(self, event):
        """Handle branch selection"""
        selected = self.branch_var.get()
        for branch in self.branches:
            if branch.name == selected:
                self.selected_branch_id = branch.id
                break
        self.refresh_stock()
    
    def on_stock_product_select(self, event):
        """Handle product selection in Stock Management section"""
        product_str = self.stock_product_var.get()
        if product_str:
            for product in self.products:
                if f"{product.name} - {product.tile_size}" == product_str:
                    self.selected_product_id = product.id
                    break
        self.refresh_stock()
    
    def add_or_update_product(self):
        """Add a new product or update existing one"""
        try:
            name = validate_required(self.product_name_entry.get(), "Product Name")
            tile_size = validate_required(self.tile_size_entry.get(), "Tile Size")
            area_per_box = validate_positive_number(self.area_per_box_entry.get(), "Area per Box")
            pieces_per_box = validate_integer(self.pieces_per_box_entry.get(), "Pieces per Box", min_value=1)
            
            if self.editing_product_id:
                # Update existing product
                product = ProductRepository.get_by_id(self.editing_product_id)
                if not product:
                    raise ValueError("Product not found")
                
                product.name = name
                product.tile_size = tile_size
                product.area_per_box = area_per_box
                product.pieces_per_box = pieces_per_box
                
                ProductRepository.update(product, user=self.current_user)
                messagebox.showinfo("Success", f"Product '{name}' updated successfully!")
                self.editing_product_id = None
                self.add_update_btn.configure(text="Add Product", fg_color=COLORS["primary"])
            else:
                # Create new product
                product = ProductRepository.create(
                    Product(
                        name=name,
                        tile_size=tile_size,
                        area_per_box=area_per_box,
                        pieces_per_box=pieces_per_box
                    ),
                    user=self.current_user
                )
                messagebox.showinfo("Success", f"Product '{name}' added successfully!")
            
            self.clear_product_form()
            self.load_products()
            
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def edit_selected_product(self):
        """Load selected product into form for editing"""
        selection = self.products_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a product to edit")
            return
        
        try:
            index = selection[0]
            product = self.products[index]
            
            # Load product data into form
            self.product_name_entry.delete(0, tk.END)
            self.product_name_entry.insert(0, product.name)
            
            self.tile_size_entry.delete(0, tk.END)
            self.tile_size_entry.insert(0, product.tile_size)
            
            self.area_per_box_entry.delete(0, tk.END)
            self.area_per_box_entry.insert(0, str(product.area_per_box))
            
            self.pieces_per_box_entry.delete(0, tk.END)
            self.pieces_per_box_entry.insert(0, str(product.pieces_per_box))
            
            # Set editing mode
            self.editing_product_id = product.id
            self.add_update_btn.configure(text="Update Product", fg_color=COLORS["primary"])
            
            # Select the product in the listbox
            self.selected_product_id = product.id
            self.refresh_stock()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load product: {str(e)}")
    
    def delete_selected_product(self):
        """Delete selected product"""
        selection = self.products_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a product to delete")
            return
        
        try:
            index = selection[0]
            product = self.products[index]
            
            if not is_api_authenticated():
                # Check if product is used in inventory
                from database.init_db import get_connection
                conn = get_connection()
                cursor = conn.cursor()
                
                # Check inventory
                cursor.execute("SELECT COUNT(*) FROM inventory WHERE product_id = ?", (product.id,))
                inv_count = cursor.fetchone()[0]
                
                # Check invoice items
                cursor.execute("SELECT COUNT(*) FROM invoice_items WHERE product_id = ?", (product.id,))
                invoice_count = cursor.fetchone()[0]
                
                conn.close()
                
                if inv_count > 0 or invoice_count > 0:
                    messagebox.showerror(
                        "Cannot Delete",
                        f"Cannot delete product '{product.name}' because it is used in:\n"
                        f"- {inv_count} inventory record(s)\n"
                        f"- {invoice_count} invoice(s)\n\n"
                        f"Please remove all inventory and invoices for this product first."
                    )
                    return
            
            # Confirm deletion
            confirm = messagebox.askyesno(
                "Confirm Delete",
                f"Are you sure you want to delete product '{product.name} - {product.tile_size}'?\n\n"
                f"This action cannot be undone."
            )
            
            if confirm:
                ProductRepository.delete(product.id, user=self.current_user)
                messagebox.showinfo("Success", f"Product '{product.name}' deleted successfully!")
                self.clear_product_form()
                self.editing_product_id = None
                self.add_update_btn.configure(text="Add Product", fg_color=COLORS["primary"])
                self.selected_product_id = None
                self.load_products()
                self.refresh_stock()
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete product: {str(e)}")
    
    def clear_product_form(self):
        """Clear product form"""
        self.product_name_entry.delete(0, tk.END)
        self.tile_size_entry.delete(0, tk.END)
        self.area_per_box_entry.delete(0, tk.END)
        self.pieces_per_box_entry.delete(0, tk.END)
        self.editing_product_id = None
        self.add_update_btn.configure(text="Add Product", fg_color=COLORS["primary"])
    
    def add_stock(self):
        """Add stock to inventory"""
        try:
            if not self.selected_branch_id:
                raise ValueError("Please select a branch")
            
            # Get product from stock product dropdown
            product_str = self.stock_product_var.get()
            if not product_str:
                raise ValueError("Please select a product from the dropdown")
            
            # Find product
            selected_product = None
            for product in self.products:
                if f"{product.name} - {product.tile_size}" == product_str:
                    selected_product = product
                    break
            
            if not selected_product:
                raise ValueError("Selected product not found")
            
            # Check branch access for employees
            if not AuthenticationService.can_access_branch(self.current_user, self.selected_branch_id):
                raise ValueError("You do not have access to this branch")
            
            grade = validate_grade(self.grade_var.get())
            boxes = validate_integer(self.stock_in_boxes_entry.get() or "0", "Boxes")
            loose_pieces = validate_integer(self.stock_in_pieces_entry.get() or "0", "Loose Pieces")
            rate_per_sqm = validate_positive_number(self.rate_sqm_entry.get() or "0", "Rate per m²")
            rate_per_box = validate_positive_number(self.rate_box_entry.get() or "0", "Rate per Box")
            rate_per_piece = validate_positive_number(self.rate_piece_entry.get() or "0", "Rate per Piece")
            
            if boxes == 0 and loose_pieces == 0:
                raise ValueError("Please enter at least some stock quantity")
            
            InventoryService.add_stock(
                self.selected_branch_id,
                selected_product.id,
                grade,
                boxes,
                loose_pieces,
                rate_per_sqm,
                rate_per_box,
                rate_per_piece,
                user_id=self.current_user.id
            )
            
            messagebox.showinfo("Success", f"Stock added successfully for {selected_product.name}!")
            self.stock_in_boxes_entry.delete(0, tk.END)
            self.stock_in_pieces_entry.delete(0, tk.END)
            self.selected_product_id = selected_product.id
            self.refresh_stock()
            
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def remove_stock(self):
        """Remove stock from inventory (Stock OUT)"""
        try:
            if not self.selected_branch_id:
                raise ValueError("Please select a branch")
            
            # Get product from stock product dropdown
            product_str = self.stock_product_var.get()
            if not product_str:
                raise ValueError("Please select a product from the dropdown")
            
            # Find product
            selected_product = None
            for product in self.products:
                if f"{product.name} - {product.tile_size}" == product_str:
                    selected_product = product
                    break
            
            if not selected_product:
                raise ValueError("Selected product not found")
            
            # Check branch access for employees
            if not AuthenticationService.can_access_branch(self.current_user, self.selected_branch_id):
                raise ValueError("You do not have access to this branch")
            
            grade = validate_grade(self.grade_var.get())
            boxes = validate_integer(self.stock_out_boxes_entry.get() or "0", "Boxes")
            loose_pieces = validate_integer(self.stock_out_pieces_entry.get() or "0", "Loose Pieces")
            comment = self.stock_out_comment_entry.get().strip() or "Stock OUT"
            
            if boxes == 0 and loose_pieces == 0:
                raise ValueError("Please enter at least some quantity to remove")
            
            # Check available stock
            inventory = InventoryService.get_inventory(self.selected_branch_id, selected_product.id, grade)
            if not inventory:
                raise ValueError(f"No stock available for {selected_product.name} - {grade}")
            
            # Get product to know pieces per box
            product = ProductRepository.get_by_id(selected_product.id)
            if not product:
                raise ValueError(f"Product not found")
            
            # Calculate total pieces available
            total_available_pieces = (inventory.boxes * product.pieces_per_box) + inventory.loose_pieces
            
            # Calculate total pieces requested
            total_requested_pieces = (boxes * product.pieces_per_box) + loose_pieces
            
            # Check if sufficient stock
            if total_requested_pieces > total_available_pieces:
                raise ValueError(f"Insufficient stock. Available: {inventory.boxes} boxes + {inventory.loose_pieces} pieces. Requested: {boxes} boxes + {loose_pieces} pieces")
            
            # Confirm removal
            confirm_msg = f"Remove {boxes} boxes + {loose_pieces} pieces of {selected_product.name} ({grade})?\n\nReason: {comment}"
            if not messagebox.askyesno("Confirm Stock OUT", confirm_msg):
                return
            
            # Deduct stock
            InventoryService.deduct_stock(
                self.selected_branch_id,
                selected_product.id,
                grade,
                boxes,
                loose_pieces,
                user_id=self.current_user.id,
                notes=comment
            )
            
            messagebox.showinfo("Success", f"Stock removed successfully for {selected_product.name}!\nReason: {comment}")
            self.stock_out_boxes_entry.delete(0, tk.END)
            self.stock_out_pieces_entry.delete(0, tk.END)
            self.stock_out_comment_entry.delete(0, tk.END)
            self.stock_out_comment_entry.insert(0, "Customer return / Other reason")
            self.selected_product_id = selected_product.id
            self.refresh_stock()
            
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def refresh_stock(self):
        """Refresh stock display"""
        self.stock_display_text.config(state=tk.NORMAL)
        self.stock_display_text.delete(1.0, tk.END)
        
        # Get product from dropdown or selected product
        product = None
        product_str = self.stock_product_var.get() if hasattr(self, 'stock_product_var') else None
        
        if product_str:
            for p in self.products:
                if f"{p.name} - {p.tile_size}" == product_str:
                    product = p
                    self.selected_product_id = p.id
                    break
        
        if not self.selected_branch_id:
            self.stock_display_text.insert(tk.END, "Please select a branch to view stock")
        elif not product:
            self.stock_display_text.insert(tk.END, "Please select a product from the dropdown to view stock")
        else:
            self.stock_display_text.insert(tk.END, f"Product: {product.name} ({product.tile_size})\n")
            self.stock_display_text.insert(tk.END, f"Area per Box: {product.area_per_box} m²\n")
            self.stock_display_text.insert(tk.END, f"Pieces per Box: {product.pieces_per_box}\n\n")
            
            for grade in VALID_GRADES:
                inv = InventoryService.get_inventory(self.selected_branch_id, product.id, grade)
                if inv:
                    total_pieces = (inv.boxes * product.pieces_per_box) + inv.loose_pieces
                    self.stock_display_text.insert(tk.END, f"{grade}:\n")
                    self.stock_display_text.insert(tk.END, f"  Boxes: {inv.boxes}\n")
                    self.stock_display_text.insert(tk.END, f"  Loose Pieces: {inv.loose_pieces}\n")
                    self.stock_display_text.insert(tk.END, f"  Total Pieces: {total_pieces}\n")
                    self.stock_display_text.insert(tk.END, f"  Rate per m²: Rs. {inv.rate_per_sqm:.2f}\n")
                    self.stock_display_text.insert(tk.END, f"  Rate per Box: Rs. {inv.rate_per_box:.2f}\n")
                    self.stock_display_text.insert(tk.END, f"  Rate per Piece: Rs. {inv.rate_per_piece:.2f}\n\n")
                else:
                    self.stock_display_text.insert(tk.END, f"{grade}: No stock\n\n")
        
        self.stock_display_text.config(state=tk.DISABLED)

