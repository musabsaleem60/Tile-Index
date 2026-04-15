"""
Invoice Printer Utility
Generates printable invoice format in Pakistani style
"""

import tkinter as tk
from tkinter import ttk
from datetime import datetime
from repositories.branch_repository import BranchRepository
from repositories.product_repository import ProductRepository
from repositories.accessory_repository import AccessoryRepository
from services.invoice_service import InvoiceService


class InvoicePrintWindow:
    """Window for displaying and printing invoices"""
    
    def __init__(self, parent, invoice_id=None, invoice_data=None):
        self.parent = parent
        self.parent.title("Invoice - Tile Index")
        self.parent.geometry("800x1000")
        
        # Get invoice data
        if invoice_id:
            self.invoice = InvoiceService.get_invoice(invoice_id)
        elif invoice_data:
            self.invoice = invoice_data
        else:
            raise ValueError("Either invoice_id or invoice_data must be provided")
        
        if not self.invoice:
            raise ValueError("Invoice not found")
        
        # Get branch, products, and accessories
        self.branch = BranchRepository.get_by_id(self.invoice.branch_id)
        self.products = {p.id: p for p in ProductRepository.get_all()}
        self.accessories = {a.id: a for a in AccessoryRepository.get_all()}
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the invoice display UI"""
        # Create canvas with scrollbar for printing
        canvas_frame = tk.Frame(self.parent)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        canvas = tk.Canvas(canvas_frame, bg="white")
        scrollbar = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="white")
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Invoice content
        self.create_invoice_content(scrollable_frame)
        
        # Buttons
        btn_frame = tk.Frame(self.parent)
        btn_frame.pack(pady=10)
        
        tk.Button(btn_frame, text="Print", command=lambda: self.print_invoice(canvas), 
                 bg="#3498db", fg="white", width=15, font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Close", command=self.parent.destroy, 
                 bg="#95a5a6", fg="white", width=15).pack(side=tk.LEFT, padx=5)
    
    def create_invoice_content(self, parent):
        """Create invoice content in Pakistani format"""
        # Company Header
        header_frame = tk.Frame(parent, bg="white")
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        tk.Label(header_frame, text="TILE INDEX", font=("Arial", 24, "bold"), 
                bg="white", fg="#2c3e50").pack()
        tk.Label(header_frame, text="Tiles Trading Company", font=("Arial", 14), 
                bg="white", fg="#7f8c8d").pack()
        tk.Label(header_frame, text="Pakistan", font=("Arial", 12), 
                bg="white", fg="#7f8c8d").pack(pady=(5, 0))
        
        # Branch name
        if self.branch:
            tk.Label(header_frame, text=self.branch.name, font=("Arial", 12, "bold"), 
                    bg="white", fg="#34495e").pack(pady=(10, 0))
        
        # Separator line
        tk.Frame(parent, height=2, bg="#34495e").pack(fill=tk.X, pady=10)
        
        # Invoice details
        details_frame = tk.Frame(parent, bg="white")
        details_frame.pack(fill=tk.X, pady=10)
        
        # Left side - Invoice info
        left_details = tk.Frame(details_frame, bg="white")
        left_details.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        tk.Label(left_details, text=f"Invoice No: {self.invoice.invoice_number}", 
                font=("Arial", 11, "bold"), bg="white", anchor=tk.W).pack(anchor=tk.W)
        
        invoice_date = self.invoice.invoice_date
        if isinstance(invoice_date, str):
            date_str = invoice_date
        else:
            date_str = invoice_date.strftime("%d-%m-%Y %H:%M:%S")
        
        tk.Label(left_details, text=f"Date: {date_str}", 
                font=("Arial", 10), bg="white", anchor=tk.W).pack(anchor=tk.W, pady=(5, 0))
        
        # Right side - Customer info
        right_details = tk.Frame(details_frame, bg="white")
        right_details.pack(side=tk.RIGHT, fill=tk.X, expand=True)
        
        tk.Label(right_details, text="Customer Details", 
                font=("Arial", 11, "bold"), bg="white", anchor=tk.W).pack(anchor=tk.W)
        tk.Label(right_details, text=f"Name: {self.invoice.customer_name}", 
                font=("Arial", 10), bg="white", anchor=tk.W).pack(anchor=tk.W, pady=(5, 0))
        if self.invoice.customer_contact:
            tk.Label(right_details, text=f"Contact: {self.invoice.customer_contact}", 
                    font=("Arial", 10), bg="white", anchor=tk.W).pack(anchor=tk.W)
        
        # Separator
        tk.Frame(parent, height=1, bg="#bdc3c7").pack(fill=tk.X, pady=10)
        
        # Items table header
        table_frame = tk.Frame(parent, bg="white")
        table_frame.pack(fill=tk.X, pady=5)
        
        headers = ['S.No', 'Product Name', 'Size', 'Grade', 'Boxes', 'Pieces', 'Rate/m²', 'Rate/Box', 'Rate/Piece', 'Total']
        col_widths = [50, 150, 80, 60, 60, 60, 80, 80, 80, 100]
        
        for idx, (header, width) in enumerate(zip(headers, col_widths)):
            frame = tk.Frame(table_frame, bg="#34495e", relief=tk.RAISED, bd=1)
            frame.grid(row=0, column=idx, padx=1, pady=1, sticky=tk.NSEW)
            tk.Label(frame, text=header, font=("Arial", 9, "bold"), 
                    bg="#34495e", fg="white", padx=5, pady=5).pack()
            table_frame.grid_columnconfigure(idx, minsize=width)
        
        # Items rows
        for row_idx, item in enumerate(self.invoice.items, 1):
            if item.product_id:
                product = self.products.get(item.product_id)
                product_name = product.name if product else "N/A"
                size = item.tile_size
                grade = item.grade
                qty_main = str(item.boxes)
                qty_loose = str(item.loose_pieces)
                rate_sqm = f"Rs. {item.rate_per_sqm:.2f}"
                rate_main = f"Rs. {item.rate_per_box:.2f}"
                rate_loose = f"Rs. {item.rate_per_piece:.2f}"
            elif item.accessory_id:
                accessory = self.accessories.get(item.accessory_id)
                if accessory:
                    product_name = f"{accessory.name} ({accessory.company})"
                    size = accessory.category
                else:
                    product_name = "Unknown Accessory"
                    size = "-"
                
                grade = "-"
                qty_main = str(item.boxes)  # Reuse boxes for quantity
                qty_loose = "-"
                rate_sqm = "-"
                rate_main = f"Rs. {item.rate_per_box:.2f}"
                rate_loose = "-"
            else:
                product_name = "Unknown Item"
                size = "-"
                grade = "-"
                qty_main = "-"
                qty_loose = "-"
                rate_sqm = "-"
                rate_main = "-"
                rate_loose = "-"
                
            row_data = [
                str(row_idx),
                product_name,
                size,
                grade,
                qty_main,
                qty_loose,
                rate_sqm,
                rate_main,
                rate_loose,
                f"Rs. {item.line_total:.2f}"
            ]
            
            for col_idx, data in enumerate(row_data):
                bg_color = "#ecf0f1" if row_idx % 2 == 0 else "white"
                frame = tk.Frame(table_frame, bg=bg_color, relief=tk.RAISED, bd=1)
                frame.grid(row=row_idx, column=col_idx, padx=1, pady=1, sticky=tk.NSEW)
                tk.Label(frame, text=data, font=("Arial", 8), 
                        bg=bg_color, padx=5, pady=3, anchor=tk.W).pack(fill=tk.X)
        
        # Totals section
        totals_frame = tk.Frame(parent, bg="white")
        totals_frame.pack(fill=tk.X, pady=20)
        
        # Right align totals
        totals_right = tk.Frame(totals_frame, bg="white")
        totals_right.pack(side=tk.RIGHT, padx=20)
        
        tk.Label(totals_right, text=f"Sub Total:        Rs. {self.invoice.subtotal:.2f}", 
                font=("Arial", 11), bg="white", anchor=tk.E).pack(anchor=tk.E, pady=2)
        
        if self.invoice.discount > 0:
            tk.Label(totals_right, text=f"Discount:         Rs. {self.invoice.discount:.2f}", 
                    font=("Arial", 11), bg="white", anchor=tk.E).pack(anchor=tk.E, pady=2)
        
        tk.Label(totals_right, text=f"Grand Total:      Rs. {self.invoice.grand_total:.2f}", 
                font=("Arial", 12, "bold"), bg="white", anchor=tk.E, fg="#27ae60").pack(anchor=tk.E, pady=(5, 2))
        
        tk.Label(totals_right, text=f"Paid Amount:      Rs. {self.invoice.paid_amount:.2f}", 
                font=("Arial", 11), bg="white", anchor=tk.E).pack(anchor=tk.E, pady=2)
        
        if self.invoice.balance > 0:
            tk.Label(totals_right, text=f"Balance:          Rs. {self.invoice.balance:.2f}", 
                    font=("Arial", 11, "bold"), bg="white", anchor=tk.E, fg="#e74c3c").pack(anchor=tk.E, pady=2)
        elif self.invoice.balance == 0:
            tk.Label(totals_right, text="Balance:          Rs. 0.00 (Paid)", 
                    font=("Arial", 11, "bold"), bg="white", anchor=tk.E, fg="#27ae60").pack(anchor=tk.E, pady=2)
        
        # Footer
        tk.Frame(parent, height=2, bg="#34495e").pack(fill=tk.X, pady=20)
        tk.Label(parent, text="Thank you for your business!", 
                font=("Arial", 10, "italic"), bg="white", fg="#7f8c8d").pack(pady=10)
        tk.Label(parent, text="Tile Index - Quality Tiles, Trusted Service", 
                font=("Arial", 9), bg="white", fg="#95a5a6").pack()
    
    def print_invoice(self, canvas):
        """Print the invoice"""
        try:
            # Create a new window for printing
            canvas.postscript(file="invoice.ps", colormode='color')
            messagebox.showinfo("Print", "Invoice saved as invoice.ps\nYou can print this file or use system print dialog.")
        except Exception as e:
            messagebox.showerror("Print Error", f"Failed to generate print file: {str(e)}")

