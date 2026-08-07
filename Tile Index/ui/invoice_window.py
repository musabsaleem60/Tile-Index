"""
Invoice & Billing Window
Create and manage invoices
"""

import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
from datetime import datetime
from repositories.branch_repository import BranchRepository
from repositories.product_repository import ProductRepository
from repositories.accessory_repository import AccessoryRepository
from repositories.sanitary_repository import SanitaryProductRepository
from services.invoice_service import InvoiceService
from services.inventory_service import InventoryService
from services.accessory_service import AccessoryService
from services.sanitary_service import SanitaryService
from utils.validators import validate_positive_number, validate_integer, validate_required
from utils.invoice_printer import InvoicePrintWindow
from utils.grade_constants import VALID_GRADES, GRADE_1
from utils.searchable_combobox import SearchableCombobox
from utils.accessory_labels import accessory_display_label
from ui.theme import COLORS, FONTS, SIZES, SPACING


class InvoiceWindow:
    """Invoice creation window"""
    
    def __init__(self, parent, current_user):
        self.parent = parent
        self.current_user = current_user
        
        self.branches = BranchRepository.get_all()
        self.products = ProductRepository.get_all()
        self.accessories = AccessoryService.get_all_accessories()
        self.sanitary_products = SanitaryProductRepository.get_all()
        self.selected_branch_id = None
        self.invoice_items = []  # List of item dicts
        
        # Filter branches for employees
        from services.auth_service import AuthenticationService
        if AuthenticationService.is_employee(self.current_user):
            # Employee can only see their assigned branch
            self.branches = [b for b in self.branches if b.id == self.current_user.branch_id]
            if self.branches:
                self.selected_branch_id = self.branches[0].id
        
        self.setup_ui()
        
        # Set branch if employee
        if AuthenticationService.is_employee(self.current_user) and self.branches:
            self.branch_var.set(self.branches[0].name)
    
    def setup_ui(self):
        """Setup the invoice UI"""
        # Header
        header = ctk.CTkLabel(
            self.parent,
            text="Invoice & Billing",
            font=FONTS["section"],
            fg_color=COLORS["surface"],
            text_color=COLORS["text"],
            height=48,
        )
        header.pack(fill=tk.X)
        
        # Main container
        main_frame = ctk.CTkFrame(self.parent, fg_color=COLORS["app_bg"], corner_radius=0)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=SPACING["page_x"], pady=SPACING["page_y"])
        
        # Left panel - Invoice Details
        left_frame = ctk.CTkScrollableFrame(
            main_frame,
            width=560,
            fg_color=COLORS["surface"],
            corner_radius=SIZES["corner_radius"],
            border_width=1,
            border_color=COLORS["border"],
        )
        left_frame.pack(side=tk.LEFT, fill=tk.Y, expand=False, padx=(0, 5))
        ctk.CTkLabel(
            left_frame,
            text="Invoice Details",
            font=FONTS["body_bold"],
            text_color=COLORS["text"],
            height=SIZES["section_label_height"],
        ).grid(row=0, column=0, columnspan=2, sticky=tk.EW, padx=12, pady=(10, 8))
        
        # Branch selection
        self.form_label(left_frame, "Branch:", bold=True).grid(row=1, column=0, sticky=tk.W, pady=5, padx=(12, 0))
        self.branch_var = tk.StringVar()
        self.branch_combo = SearchableCombobox(left_frame, textvariable=self.branch_var, width=SIZES["dropdown_width"], state="normal", font=FONTS["small"])
        self.branch_combo.set_completion_list([f"{b.name}" for b in self.branches])
        self.branch_combo.grid(row=1, column=1, pady=5, padx=(5, 12), sticky=tk.W)
        self.branch_combo.bind('<<ComboboxSelected>>', self.on_branch_select)
        
        # Disable branch selection for employees
        from services.auth_service import AuthenticationService
        if AuthenticationService.is_employee(self.current_user):
            self.branch_combo.config(state="disabled")
        
        # Customer details
        self.form_label(left_frame, "Customer Name:").grid(row=2, column=0, sticky=tk.W, pady=5, padx=(12, 0))
        self.customer_name_entry = self.form_entry(left_frame)
        self.customer_name_entry.grid(row=2, column=1, pady=5, padx=(5, 12), sticky=tk.EW)
        
        self.form_label(left_frame, "Contact (Optional):").grid(row=3, column=0, sticky=tk.W, pady=5, padx=(12, 0))
        self.customer_contact_entry = self.form_entry(left_frame)
        self.customer_contact_entry.grid(row=3, column=1, pady=5, padx=(5, 12), sticky=tk.EW)
        
        # Date
        self.form_label(left_frame, "Date:").grid(row=4, column=0, sticky=tk.W, pady=5, padx=(12, 0))
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.form_label(left_frame, date_str, muted=True).grid(row=4, column=1, sticky=tk.W, pady=5, padx=(5, 12))
        
        # Add Item section
        item_frame = self.create_subpanel(left_frame, "Add Item")
        item_frame.grid(row=5, column=0, columnspan=2, sticky=tk.EW, pady=10, padx=12)
        
        self.form_label(item_frame, "Item Type:").grid(row=1, column=0, sticky=tk.W, pady=3, padx=8)
        self.item_type_var = tk.StringVar(value="Tiles")
        item_type_combo = ttk.Combobox(item_frame, textvariable=self.item_type_var, width=SIZES["dropdown_width"], state="readonly", font=FONTS["small"])
        item_type_combo['values'] = ("Tiles", "Accessories", "Sanitary")
        item_type_combo.grid(row=1, column=1, pady=3, padx=8, sticky=tk.W)
        item_type_combo.bind('<<ComboboxSelected>>', self.on_item_type_change)
        
        self.product_label = self.form_label(item_frame, "Product:")
        self.product_label.grid(row=2, column=0, sticky=tk.W, pady=3, padx=8)
        self.product_var = tk.StringVar()
        self.product_combo = SearchableCombobox(item_frame, textvariable=self.product_var, width=SIZES["dropdown_width"], state="normal", font=FONTS["small"])
        self.product_combo.set_completion_list([f"{p.name} - {p.tile_size}" for p in self.products])
        self.product_combo.grid(row=2, column=1, pady=3, padx=8, sticky=tk.W)
        self.product_combo.bind('<<ComboboxSelected>>', self.on_product_select)
        
        self.grade_label = self.form_label(item_frame, "Grade:")
        self.grade_label.grid(row=3, column=0, sticky=tk.W, pady=3, padx=8)
        self.grade_var = tk.StringVar(value=GRADE_1)
        self.grade_combo = ttk.Combobox(item_frame, textvariable=self.grade_var, width=SIZES["dropdown_width"], state="readonly", font=FONTS["small"])
        self.grade_combo['values'] = VALID_GRADES
        self.grade_combo.grid(row=3, column=1, pady=3, padx=8, sticky=tk.W)
        self.grade_combo.bind('<<ComboboxSelected>>', self.on_grade_select)
        
        self.boxes_label = self.form_label(item_frame, "Boxes:")
        self.boxes_label.grid(row=4, column=0, sticky=tk.W, pady=3, padx=8)
        self.item_boxes_entry = self.form_entry(item_frame, width=160)
        self.item_boxes_entry.grid(row=4, column=1, pady=3, padx=8)
        self.item_boxes_entry.insert(0, "0")
        
        self.pieces_label = self.form_label(item_frame, "Loose Pieces:")
        self.pieces_label.grid(row=5, column=0, sticky=tk.W, pady=3, padx=8)
        self.item_pieces_entry = self.form_entry(item_frame, width=160)
        self.item_pieces_entry.grid(row=5, column=1, pady=3, padx=8)
        self.item_pieces_entry.insert(0, "0")
        
        # Stock info display
        self.stock_info_label = ctk.CTkLabel(
            item_frame,
            text="",
            font=FONTS["status"],
            text_color=COLORS["primary"],
            wraplength=300,
            height=SIZES["small_label_height"],
        )
        self.stock_info_label.grid(row=6, column=0, columnspan=2, pady=5)
        
        self.action_button(item_frame, "Add to Invoice", self.add_item, width=180).grid(row=7, column=0, columnspan=2, pady=10)
        
        # Totals section
        totals_frame = self.create_subpanel(left_frame, "Totals")
        totals_frame.grid(row=6, column=0, columnspan=2, sticky=tk.EW, pady=10, padx=12)
        
        self.form_label(totals_frame, "Sub Total:").grid(row=1, column=0, sticky=tk.W, pady=3, padx=8)
        self.subtotal_label = self.value_label(totals_frame, "Rs. 0.00", COLORS["primary"])
        self.subtotal_label.grid(row=1, column=1, sticky=tk.E, pady=3, padx=8)
        
        self.form_label(totals_frame, "Discount:").grid(row=2, column=0, sticky=tk.W, pady=3, padx=8)
        self.discount_entry = self.form_entry(totals_frame, width=160)
        self.discount_entry.grid(row=2, column=1, pady=3, padx=8)
        self.discount_entry.insert(0, "0")
        self.discount_entry.bind('<KeyRelease>', self.update_totals)
        
        self.form_label(totals_frame, "Grand Total:", bold=True).grid(row=3, column=0, sticky=tk.W, pady=5, padx=8)
        self.grand_total_label = self.value_label(totals_frame, "Rs. 0.00", COLORS["primary"], bold=True)
        self.grand_total_label.grid(row=3, column=1, sticky=tk.E, pady=5, padx=8)
        
        self.form_label(totals_frame, "Paid Amount:").grid(row=4, column=0, sticky=tk.W, pady=3, padx=8)
        self.paid_entry = self.form_entry(totals_frame, width=160)
        self.paid_entry.grid(row=4, column=1, pady=3, padx=8)
        self.paid_entry.insert(0, "0")
        self.paid_entry.bind('<KeyRelease>', self.update_totals)
        
        self.form_label(totals_frame, "Balance:").grid(row=5, column=0, sticky=tk.W, pady=3, padx=8)
        self.balance_label = self.value_label(totals_frame, "Rs. 0.00", COLORS["danger"])
        self.balance_label.grid(row=5, column=1, sticky=tk.E, pady=3, padx=8)
        
        # Action buttons
        btn_frame = ctk.CTkFrame(left_frame, fg_color="transparent", corner_radius=0)
        btn_frame.grid(row=7, column=0, columnspan=2, pady=10)
        
        self.action_button(btn_frame, "Generate Invoice", self.generate_invoice, width=140).pack(side=tk.LEFT, padx=5)
        self.action_button(btn_frame, "Clear All", self.clear_invoice, width=120, primary=False).pack(side=tk.LEFT, padx=5)
        self.action_button(btn_frame, "Print Invoice", self.print_invoice, width=120).pack(side=tk.LEFT, padx=5)
        
        # Right panel - Invoice Items Table
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
            text="Invoice Items",
            font=FONTS["body_bold"],
            text_color=COLORS["text"],
            height=SIZES["section_label_height"],
        ).pack(fill=tk.X, padx=12, pady=(10, 8))
        
        # Treeview for items
        columns = ('S.No', 'Product', 'Size', 'Grade', 'Boxes', 'Pieces', 'Rate/Box', 'Rate/Piece', 'Total')
        table_frame = ctk.CTkFrame(right_frame, fg_color=COLORS["surface"], corner_radius=SIZES["corner_radius"], border_width=1, border_color=COLORS["border"])
        table_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 8))
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        self.items_tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=20)

        column_widths = {
            'S.No': 55,
            'Product': 210,
            'Size': 75,
            'Grade': 90,
            'Boxes': 70,
            'Pieces': 70,
            'Rate/Box': 85,
            'Rate/Piece': 90,
            'Total': 95,
        }
        for col in columns:
            self.items_tree.heading(col, text=col)
            self.items_tree.column(col, width=column_widths[col], minwidth=column_widths[col], anchor=tk.CENTER, stretch=False)
        
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.items_tree.yview)
        xscrollbar = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.items_tree.xview)
        self.items_tree.configure(yscrollcommand=scrollbar.set, xscrollcommand=xscrollbar.set)
        
        self.items_tree.grid(row=0, column=0, sticky=tk.NSEW, padx=(1, 0), pady=(1, 0))
        scrollbar.grid(row=0, column=1, sticky=tk.NS, pady=(1, 0))
        xscrollbar.grid(row=1, column=0, sticky=tk.EW, padx=(1, 0), pady=(0, 1))
        
        # Delete item button
        self.action_button(right_frame, "Remove Selected Item", self.remove_item, width=180, primary=False).pack(pady=(0, 12))
        
        # Configure grid
        left_frame.grid_columnconfigure(1, weight=1)

    def create_subpanel(self, parent, title):
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

    def form_label(self, parent, text, bold=False, muted=False):
        return ctk.CTkLabel(
            parent,
            text=text,
            font=FONTS["small_bold"] if bold else FONTS["small"],
            text_color=COLORS["text_muted"] if muted else COLORS["text"],
            height=SIZES["small_label_height"],
            anchor=tk.W,
        )

    def value_label(self, parent, text, color, bold=False):
        return ctk.CTkLabel(
            parent,
            text=text,
            font=FONTS["body_bold"] if bold else FONTS["small_bold"],
            text_color=color,
            height=SIZES["small_label_height"],
            anchor=tk.E,
        )

    def form_entry(self, parent, width=240):
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
    
    def on_item_type_change(self, event):
        """Handle item type change"""
        item_type = self.item_type_var.get()
        self.product_var.set("")
        
        if item_type == "Tiles":
            self.product_label.configure(text="Product:")
            self.product_combo.set_completion_list([f"{p.name} - {p.tile_size}" for p in self.products])
            self.grade_label.grid()
            self.grade_combo.grid()
            self.boxes_label.configure(text="Boxes:")
            self.pieces_label.grid()
            self.item_pieces_entry.grid()
        elif item_type == "Accessories":
            self.product_label.configure(text="Accessory:")
            self.product_combo.set_completion_list([self.format_accessory(a) for a in self.accessories])
            self.grade_label.grid_remove()
            self.grade_combo.grid_remove()
            self.boxes_label.configure(text="Quantity:")
            self.pieces_label.grid_remove()
            self.item_pieces_entry.grid_remove()
        else:
            self.product_label.configure(text="Sanitary:")
            self.product_combo.set_completion_list([self.format_sanitary_product(p) for p in self.sanitary_products])
            self.grade_label.grid_remove()
            self.grade_combo.grid_remove()
            self.boxes_label.configure(text="Quantity:")
            self.pieces_label.grid_remove()
            self.item_pieces_entry.grid_remove()
            
        self.update_stock_info()
    
    def on_branch_select(self, event):
        """Handle branch selection"""
        selected = self.branch_var.get()
        for branch in self.branches:
            if branch.name == selected:
                self.selected_branch_id = branch.id
                break
        self.update_stock_info()
    
    def on_product_select(self, event):
        """Handle product selection"""
        self.update_stock_info()
    
    def on_grade_select(self, event):
        """Handle grade selection"""
        self.update_stock_info()
    
    def update_stock_info(self):
        """Update stock information display"""
        try:
            item_type = self.item_type_var.get()
            item_str = self.product_var.get()
            
            if not item_str or not self.selected_branch_id:
                self.stock_info_label.configure(text="")
                return
            
            if item_type == "Tiles":
                # Find product
                product = None
                for p in self.products:
                    if f"{p.name} - {p.tile_size}" == item_str:
                        product = p
                        break
                
                if not product:
                    self.stock_info_label.configure(text="")
                    return
                
                grade = self.grade_var.get()
                inv = InventoryService.get_inventory(self.selected_branch_id, product.id, grade)
                
                if inv:
                    self.stock_info_label.configure(
                        text=f"Available: {inv.boxes} boxes + {inv.loose_pieces} pieces\n"
                             f"Rate/Box: Rs. {inv.rate_per_box:.2f} | Rate/Piece: Rs. {inv.rate_per_piece:.2f}",
                        text_color=COLORS["primary"]
                    )
                else:
                    self.stock_info_label.configure(text="No stock available for this grade", text_color=COLORS["danger"])
            elif item_type == "Accessories":
                # Find accessory
                accessory = None
                for a in self.accessories:
                    if self.format_accessory(a) == item_str:
                        accessory = a
                        break
                
                if not accessory:
                    self.stock_info_label.configure(text="")
                    return
                
                acc_inv = AccessoryService.get_inventory(self.selected_branch_id, accessory.id)
                available = acc_inv.quantity if acc_inv else 0
                
                self.stock_info_label.configure(
                    text=f"Available: {available} items\n"
                         f"Unit Price: Rs. {accessory.unit_price:.2f}",
                    text_color=COLORS["primary"]
                )
            else:
                sanitary_product = None
                for product in self.sanitary_products:
                    if self.format_sanitary_product(product) == item_str:
                        sanitary_product = product
                        break

                if not sanitary_product:
                    self.stock_info_label.configure(text="")
                    return

                sanitary_inv = SanitaryService.get_inventory(self.selected_branch_id, sanitary_product.id)
                available = sanitary_inv.quantity if sanitary_inv else 0

                self.stock_info_label.configure(
                    text=f"Available: {available} items\n"
                         f"Sale Price: Rs. {sanitary_product.sale_price:.2f}",
                    text_color=COLORS["primary"]
                )
        except:
            self.stock_info_label.configure(text="")
    
    def add_item(self):
        """Add item to invoice"""
        try:
            if not self.selected_branch_id:
                raise ValueError("Please select a branch")
            
            item_type = self.item_type_var.get()
            item_str = self.product_var.get()
            if not item_str:
                raise ValueError(f"Please select a {self.item_type_var.get().lower()} item")
            
            if item_type == "Tiles":
                # Find product
                product = None
                for p in self.products:
                    if f"{p.name} - {p.tile_size}" == item_str:
                        product = p
                        break
                
                if not product:
                    raise ValueError("Product not found")
                
                grade = self.grade_var.get()
                boxes = validate_integer(self.item_boxes_entry.get() or "0", "Boxes")
                loose_pieces = validate_integer(self.item_pieces_entry.get() or "0", "Loose Pieces")
                
                if boxes == 0 and loose_pieces == 0:
                    raise ValueError("Please enter at least some quantity")
                
                # Check stock
                inv = InventoryService.get_inventory(self.selected_branch_id, product.id, grade)
                if not inv:
                    raise ValueError(f"No stock available for {product.name} - Grade {grade}")
                
                total_available_pieces = (inv.boxes * product.pieces_per_box) + inv.loose_pieces
                total_requested_pieces = (boxes * product.pieces_per_box) + loose_pieces
                
                if total_requested_pieces > total_available_pieces:
                    raise ValueError(f"Insufficient stock. Available: {inv.boxes} boxes + {inv.loose_pieces} pieces")
                
                # Calculate line total
                line_total = (boxes * inv.rate_per_box) + (loose_pieces * inv.rate_per_piece)
                
                # Add to items list
                item_data = {
                    'type': 'Tiles',
                    'product_id': product.id,
                    'product_name': product.name,
                    'tile_size': product.tile_size,
                    'grade': grade,
                    'boxes': boxes,
                    'loose_pieces': loose_pieces,
                    'rate_per_box': inv.rate_per_box,
                    'rate_per_piece': inv.rate_per_piece,
                    'line_total': line_total
                }
            elif item_type == "Accessories":
                # Accessory logic
                accessory = None
                for a in self.accessories:
                    if self.format_accessory(a) == item_str:
                        accessory = a
                        break
                
                if not accessory:
                    raise ValueError("Accessory not found")
                
                quantity = validate_integer(self.item_boxes_entry.get() or "0", "Quantity")
                if quantity <= 0:
                    raise ValueError("Please enter a valid quantity")
                
                # Check stock
                acc_inv = AccessoryService.get_inventory(self.selected_branch_id, accessory.id)
                available = acc_inv.quantity if acc_inv else 0
                if quantity > available:
                    raise ValueError(f"Insufficient stock for accessory {accessory_display_label(accessory)}. Available: {available}")
                
                # Calculate line total
                line_total = quantity * accessory.unit_price
                
                # Add to items list
                item_data = {
                    'type': 'Accessory',
                    'accessory_id': accessory.id,
                    'product_name': accessory_display_label(accessory),
                    'tile_size': accessory.category,
                    'grade': '-',
                    'boxes': quantity,
                    'loose_pieces': 0,
                    'rate_per_box': accessory.unit_price,
                    'rate_per_piece': 0,
                    'line_total': line_total
                }
            else:
                sanitary_product = None
                for product in self.sanitary_products:
                    if self.format_sanitary_product(product) == item_str:
                        sanitary_product = product
                        break

                if not sanitary_product:
                    raise ValueError("Sanitary product not found")

                quantity = validate_integer(self.item_boxes_entry.get() or "0", "Quantity")
                if quantity <= 0:
                    raise ValueError("Please enter a valid quantity")

                sanitary_inv = SanitaryService.get_inventory(self.selected_branch_id, sanitary_product.id)
                available = sanitary_inv.quantity if sanitary_inv else 0
                if quantity > available:
                    raise ValueError(
                        f"Insufficient stock for sanitary product {sanitary_product.product_category}. "
                        f"Available: {available}"
                    )

                line_total = quantity * sanitary_product.sale_price

                item_data = {
                    'type': 'Sanitary',
                    'sanitary_product_id': sanitary_product.id,
                    'product_name': f"{sanitary_product.company_name} - {sanitary_product.product_category}",
                    'tile_size': sanitary_product.color,
                    'grade': sanitary_product.sku,
                    'boxes': quantity,
                    'loose_pieces': 0,
                    'rate_per_box': sanitary_product.sale_price,
                    'rate_per_piece': 0,
                    'line_total': line_total
                }
            
            self.invoice_items.append(item_data)
            self.update_items_table()
            self.update_totals()
            
            # Clear item form
            self.item_boxes_entry.delete(0, tk.END)
            self.item_boxes_entry.insert(0, "0")
            self.item_pieces_entry.delete(0, tk.END)
            self.item_pieces_entry.insert(0, "0")
            
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def remove_item(self):
        """Remove selected item from invoice"""
        selection = self.items_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select an item to remove")
            return
        
        item = self.items_tree.item(selection[0])
        index = int(item['values'][0]) - 1
        
        if 0 <= index < len(self.invoice_items):
            self.invoice_items.pop(index)
            self.update_items_table()
            self.update_totals()
    
    def update_items_table(self):
        """Update the items table display"""
        # Clear table
        for item in self.items_tree.get_children():
            self.items_tree.delete(item)
        
        # Add items
        for idx, item in enumerate(self.invoice_items, 1):
            self.items_tree.insert('', tk.END, values=(
                idx,
                item['product_name'],
                item['tile_size'],
                item['grade'],
                item['boxes'],
                item['loose_pieces'],
                f"Rs. {item['rate_per_box']:.2f}",
                f"Rs. {item['rate_per_piece']:.2f}",
                f"Rs. {item['line_total']:.2f}"
            ))
    
    def update_totals(self, event=None):
        """Update invoice totals"""
        subtotal = sum(item['line_total'] for item in self.invoice_items)
        
        try:
            discount = float(self.discount_entry.get() or "0")
        except:
            discount = 0
        
        try:
            paid = float(self.paid_entry.get() or "0")
        except:
            paid = 0
        
        grand_total = subtotal - discount
        balance = grand_total - paid
        
        self.subtotal_label.configure(text=f"Rs. {subtotal:.2f}")
        self.grand_total_label.configure(text=f"Rs. {grand_total:.2f}")
        self.balance_label.configure(text=f"Rs. {balance:.2f}")
    
    def generate_invoice(self):
        """Generate and save invoice"""
        try:
            if not self.selected_branch_id:
                raise ValueError("Please select a branch")
            
            customer_name = validate_required(self.customer_name_entry.get(), "Customer Name")
            customer_contact = self.customer_contact_entry.get().strip() or None
            
            if len(self.invoice_items) == 0:
                raise ValueError("Please add at least one item to the invoice")
            
            discount = float(self.discount_entry.get() or "0")
            paid_amount = float(self.paid_entry.get() or "0")
            
            # Prepare items data
            items_data = []
            for item in self.invoice_items:
                if item.get('type') == 'Tiles':
                    items_data.append({
                        'product_id': item['product_id'],
                        'grade': item['grade'],
                        'boxes': item['boxes'],
                        'loose_pieces': item['loose_pieces']
                    })
                elif item.get('type') == 'Accessory':
                    items_data.append({
                        'accessory_id': item['accessory_id'],
                        'quantity': item['boxes']  # boxes field used for quantity in accessories
                    })
                else:
                    items_data.append({
                        'sanitary_product_id': item['sanitary_product_id'],
                        'quantity': item['boxes']
                    })
            
            # Check branch access for employees
            from services.auth_service import AuthenticationService
            if not AuthenticationService.can_access_branch(self.current_user, self.selected_branch_id):
                raise ValueError("You do not have access to this branch")
            
            # Create invoice
            invoice = InvoiceService.create_invoice(
                self.selected_branch_id,
                customer_name,
                customer_contact,
                items_data,
                discount,
                paid_amount,
                user_id=self.current_user.id
            )
            
            messagebox.showinfo("Success", f"Invoice generated successfully!\nInvoice Number: {invoice.invoice_number}")
            
            # Open invoice print window
            print_window = tk.Toplevel(self.parent)
            InvoicePrintWindow(print_window, invoice_id=invoice.id)
            
            self.clear_invoice()
            
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def clear_invoice(self):
        """Clear invoice form"""
        self.customer_name_entry.delete(0, tk.END)
        self.customer_contact_entry.delete(0, tk.END)
        self.item_type_var.set("Tiles")
        self.on_item_type_change(None)
        self.product_var.set("")
        self.discount_entry.delete(0, tk.END)
        self.discount_entry.insert(0, "0")
        self.paid_entry.delete(0, tk.END)
        self.paid_entry.insert(0, "0")
        self.invoice_items = []
        self.update_items_table()
        self.update_totals()
    
    def print_invoice(self):
        """Print invoice (opens print preview)"""
        if len(self.invoice_items) == 0:
            messagebox.showwarning("Warning", "No items in invoice to print.\nPlease generate an invoice first, then use the print option from the invoice view window.")
            return
        
        # Show message - invoice must be generated first
        messagebox.showinfo("Print Invoice", "Please generate the invoice first. After generation, the invoice will open in a print window automatically.\nYou can also search for existing invoices to print them.")

    @staticmethod
    def format_accessory(accessory):
        return f"{accessory.category} - {accessory_display_label(accessory)}"

    @staticmethod
    def format_sanitary_product(product):
        """Format sanitary product for dropdown display"""
        return (
            f"{product.company_name} - {product.product_category} - "
            f"{product.color} ({product.sku})"
        )

