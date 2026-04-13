"""
Invoice & Billing Window
Create and manage invoices
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from repositories.branch_repository import BranchRepository
from repositories.product_repository import ProductRepository
from services.invoice_service import InvoiceService
from services.inventory_service import InventoryService
from utils.validators import validate_positive_number, validate_integer, validate_required
from utils.invoice_printer import InvoicePrintWindow
from utils.grade_constants import VALID_GRADES, GRADE_1


class InvoiceWindow:
    """Invoice creation window"""
    
    def __init__(self, parent, current_user):
        self.parent = parent
        self.current_user = current_user
        self.parent.title("Invoice & Billing - Tile Index")
        self.parent.geometry("1400x800")
        
        self.branches = BranchRepository.get_all()
        self.products = ProductRepository.get_all()
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
        header = tk.Label(
            self.parent,
            text="Invoice & Billing",
            font=("Arial", 18, "bold"),
            bg="#27ae60",
            fg="white",
            pady=10
        )
        header.pack(fill=tk.X)
        
        # Main container
        main_frame = tk.Frame(self.parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel - Invoice Details
        left_frame = tk.LabelFrame(main_frame, text="Invoice Details", font=("Arial", 12, "bold"), padx=10, pady=10)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 5))
        
        # Branch selection
        tk.Label(left_frame, text="Branch:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.branch_var = tk.StringVar()
        branch_combo = ttk.Combobox(left_frame, textvariable=self.branch_var, width=25, state="readonly", font=("Arial", 10))
        branch_combo['values'] = [f"{b.name}" for b in self.branches]
        branch_combo.grid(row=0, column=1, pady=5, padx=5, sticky=tk.W)
        branch_combo.bind('<<ComboboxSelected>>', self.on_branch_select)
        
        # Disable branch selection for employees
        from services.auth_service import AuthenticationService
        if AuthenticationService.is_employee(self.current_user):
            branch_combo.config(state="disabled")
        
        # Customer details
        tk.Label(left_frame, text="Customer Name:", font=("Arial", 10)).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.customer_name_entry = tk.Entry(left_frame, width=30, font=("Arial", 10))
        self.customer_name_entry.grid(row=1, column=1, pady=5, padx=5)
        
        tk.Label(left_frame, text="Contact (Optional):", font=("Arial", 10)).grid(row=2, column=0, sticky=tk.W, pady=5)
        self.customer_contact_entry = tk.Entry(left_frame, width=30, font=("Arial", 10))
        self.customer_contact_entry.grid(row=2, column=1, pady=5, padx=5)
        
        # Date
        tk.Label(left_frame, text="Date:", font=("Arial", 10)).grid(row=3, column=0, sticky=tk.W, pady=5)
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        tk.Label(left_frame, text=date_str, font=("Arial", 10), fg="gray").grid(row=3, column=1, sticky=tk.W, pady=5, padx=5)
        
        # Add Item section
        item_frame = tk.LabelFrame(left_frame, text="Add Item", font=("Arial", 10, "bold"), padx=5, pady=5)
        item_frame.grid(row=4, column=0, columnspan=2, sticky=tk.EW, pady=10)
        
        tk.Label(item_frame, text="Product:", font=("Arial", 9)).grid(row=0, column=0, sticky=tk.W, pady=3)
        self.product_var = tk.StringVar()
        product_combo = ttk.Combobox(item_frame, textvariable=self.product_var, width=22, state="readonly", font=("Arial", 9))
        product_combo['values'] = [f"{p.name} - {p.tile_size}" for p in self.products]
        product_combo.grid(row=0, column=1, pady=3, padx=5, sticky=tk.W)
        product_combo.bind('<<ComboboxSelected>>', self.on_product_select)
        
        tk.Label(item_frame, text="Grade:", font=("Arial", 9)).grid(row=1, column=0, sticky=tk.W, pady=3)
        self.grade_var = tk.StringVar(value=GRADE_1)
        grade_combo = ttk.Combobox(item_frame, textvariable=self.grade_var, width=22, state="readonly", font=("Arial", 9))
        grade_combo['values'] = VALID_GRADES
        grade_combo.grid(row=1, column=1, pady=3, padx=5, sticky=tk.W)
        grade_combo.bind('<<ComboboxSelected>>', self.on_grade_select)
        
        tk.Label(item_frame, text="Boxes:", font=("Arial", 9)).grid(row=2, column=0, sticky=tk.W, pady=3)
        self.item_boxes_entry = tk.Entry(item_frame, width=25, font=("Arial", 9))
        self.item_boxes_entry.grid(row=2, column=1, pady=3, padx=5)
        self.item_boxes_entry.insert(0, "0")
        
        tk.Label(item_frame, text="Loose Pieces:", font=("Arial", 9)).grid(row=3, column=0, sticky=tk.W, pady=3)
        self.item_pieces_entry = tk.Entry(item_frame, width=25, font=("Arial", 9))
        self.item_pieces_entry.grid(row=3, column=1, pady=3, padx=5)
        self.item_pieces_entry.insert(0, "0")
        
        # Stock info display
        self.stock_info_label = tk.Label(item_frame, text="", font=("Arial", 8), fg="blue", wraplength=200)
        self.stock_info_label.grid(row=4, column=0, columnspan=2, pady=5)
        
        tk.Button(item_frame, text="Add to Invoice", command=self.add_item, bg="#3498db", fg="white", width=20).grid(row=5, column=0, columnspan=2, pady=10)
        
        # Totals section
        totals_frame = tk.LabelFrame(left_frame, text="Totals", font=("Arial", 10, "bold"), padx=5, pady=5)
        totals_frame.grid(row=5, column=0, columnspan=2, sticky=tk.EW, pady=10)
        
        tk.Label(totals_frame, text="Sub Total:", font=("Arial", 10)).grid(row=0, column=0, sticky=tk.W, pady=3)
        self.subtotal_label = tk.Label(totals_frame, text="Rs. 0.00", font=("Arial", 10, "bold"), fg="green")
        self.subtotal_label.grid(row=0, column=1, sticky=tk.E, pady=3, padx=5)
        
        tk.Label(totals_frame, text="Discount:", font=("Arial", 10)).grid(row=1, column=0, sticky=tk.W, pady=3)
        self.discount_entry = tk.Entry(totals_frame, width=15, font=("Arial", 10))
        self.discount_entry.grid(row=1, column=1, pady=3, padx=5)
        self.discount_entry.insert(0, "0")
        self.discount_entry.bind('<KeyRelease>', self.update_totals)
        
        tk.Label(totals_frame, text="Grand Total:", font=("Arial", 11, "bold")).grid(row=2, column=0, sticky=tk.W, pady=5)
        self.grand_total_label = tk.Label(totals_frame, text="Rs. 0.00", font=("Arial", 12, "bold"), fg="darkgreen")
        self.grand_total_label.grid(row=2, column=1, sticky=tk.E, pady=5, padx=5)
        
        tk.Label(totals_frame, text="Paid Amount:", font=("Arial", 10)).grid(row=3, column=0, sticky=tk.W, pady=3)
        self.paid_entry = tk.Entry(totals_frame, width=15, font=("Arial", 10))
        self.paid_entry.grid(row=3, column=1, pady=3, padx=5)
        self.paid_entry.insert(0, "0")
        self.paid_entry.bind('<KeyRelease>', self.update_totals)
        
        tk.Label(totals_frame, text="Balance:", font=("Arial", 10)).grid(row=4, column=0, sticky=tk.W, pady=3)
        self.balance_label = tk.Label(totals_frame, text="Rs. 0.00", font=("Arial", 10, "bold"), fg="red")
        self.balance_label.grid(row=4, column=1, sticky=tk.E, pady=3, padx=5)
        
        # Action buttons
        btn_frame = tk.Frame(left_frame)
        btn_frame.grid(row=6, column=0, columnspan=2, pady=10)
        
        tk.Button(btn_frame, text="Generate Invoice", command=self.generate_invoice, bg="#27ae60", fg="white", width=15, font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Clear All", command=self.clear_invoice, bg="#e74c3c", fg="white", width=15).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Print Invoice", command=self.print_invoice, bg="#3498db", fg="white", width=15).pack(side=tk.LEFT, padx=5)
        
        # Right panel - Invoice Items Table
        right_frame = tk.LabelFrame(main_frame, text="Invoice Items", font=("Arial", 12, "bold"), padx=10, pady=10)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # Treeview for items
        columns = ('S.No', 'Product', 'Size', 'Grade', 'Boxes', 'Pieces', 'Rate/Box', 'Rate/Piece', 'Total')
        self.items_tree = ttk.Treeview(right_frame, columns=columns, show='headings', height=20)
        
        for col in columns:
            self.items_tree.heading(col, text=col)
            self.items_tree.column(col, width=100, anchor=tk.CENTER)
        
        self.items_tree.column('Product', width=150)
        self.items_tree.column('Total', width=120)
        
        scrollbar = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=self.items_tree.yview)
        self.items_tree.configure(yscrollcommand=scrollbar.set)
        
        self.items_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Delete item button
        tk.Button(right_frame, text="Remove Selected Item", command=self.remove_item, bg="#e74c3c", fg="white", width=20).pack(pady=5)
        
        # Configure grid
        left_frame.grid_columnconfigure(1, weight=1)
    
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
            product_str = self.product_var.get()
            if not product_str or not self.selected_branch_id:
                self.stock_info_label.config(text="")
                return
            
            # Find product
            product = None
            for p in self.products:
                if f"{p.name} - {p.tile_size}" == product_str:
                    product = p
                    break
            
            if not product:
                self.stock_info_label.config(text="")
                return
            
            grade = self.grade_var.get()
            inv = InventoryService.get_inventory(self.selected_branch_id, product.id, grade)
            
            if inv:
                total_pieces = (inv.boxes * product.pieces_per_box) + inv.loose_pieces
                self.stock_info_label.config(
                    text=f"Available: {inv.boxes} boxes + {inv.loose_pieces} pieces\n"
                         f"Rate/Box: Rs. {inv.rate_per_box:.2f} | Rate/Piece: Rs. {inv.rate_per_piece:.2f}"
                )
            else:
                self.stock_info_label.config(text="No stock available for this grade", fg="red")
        except:
            self.stock_info_label.config(text="")
    
    def add_item(self):
        """Add item to invoice"""
        try:
            if not self.selected_branch_id:
                raise ValueError("Please select a branch")
            
            product_str = self.product_var.get()
            if not product_str:
                raise ValueError("Please select a product")
            
            # Find product
            product = None
            for p in self.products:
                if f"{p.name} - {p.tile_size}" == product_str:
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
        
        self.subtotal_label.config(text=f"Rs. {subtotal:.2f}")
        self.grand_total_label.config(text=f"Rs. {grand_total:.2f}")
        self.balance_label.config(text=f"Rs. {balance:.2f}")
    
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
                items_data.append({
                    'product_id': item['product_id'],
                    'grade': item['grade'],
                    'boxes': item['boxes'],
                    'loose_pieces': item['loose_pieces']
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

