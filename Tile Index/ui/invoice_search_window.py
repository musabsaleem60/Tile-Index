"""
Invoice Search Window
Search and view existing invoices
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date
from repositories.branch_repository import BranchRepository
from services.invoice_service import InvoiceService
from utils.invoice_printer import InvoicePrintWindow
from utils.searchable_combobox import SearchableCombobox


class InvoiceSearchWindow:
    """Invoice search and view window"""
    
    def __init__(self, parent):
        self.parent = parent
        
        self.branches = BranchRepository.get_all()
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the search UI"""
        # Header
        header = tk.Label(
            self.parent,
            text="Search & View Invoices",
            font=("Arial", 18, "bold"),
            bg="#3498db",
            fg="white",
            pady=10
        )
        header.pack(fill=tk.X)
        
        # Search frame
        search_frame = tk.LabelFrame(self.parent, text="Search Criteria", font=("Arial", 12, "bold"), padx=10, pady=10)
        search_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Branch
        tk.Label(search_frame, text="Branch:", font=("Arial", 10)).grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        self.branch_var = tk.StringVar()
        self.branch_combo = SearchableCombobox(search_frame, textvariable=self.branch_var, width=25, state="normal", font=("Arial", 10))
        self.branch_combo.set_completion_list(["All Branches"] + [f"{b.name}" for b in self.branches])
        self.branch_combo.grid(row=0, column=1, pady=5, padx=5, sticky=tk.W)
        
        # Invoice number
        tk.Label(search_frame, text="Invoice Number:", font=("Arial", 10)).grid(row=0, column=2, sticky=tk.W, pady=5, padx=5)
        self.invoice_number_entry = tk.Entry(search_frame, width=20, font=("Arial", 10))
        self.invoice_number_entry.grid(row=0, column=3, pady=5, padx=5)
        
        # Customer name
        tk.Label(search_frame, text="Customer Name:", font=("Arial", 10)).grid(row=1, column=0, sticky=tk.W, pady=5, padx=5)
        self.customer_name_entry = tk.Entry(search_frame, width=25, font=("Arial", 10))
        self.customer_name_entry.grid(row=1, column=1, pady=5, padx=5)
        
        # Date from
        tk.Label(search_frame, text="Date From:", font=("Arial", 10)).grid(row=1, column=2, sticky=tk.W, pady=5, padx=5)
        self.date_from_entry = tk.Entry(search_frame, width=20, font=("Arial", 10))
        self.date_from_entry.grid(row=1, column=3, pady=5, padx=5)
        self.date_from_entry.insert(0, date.today().strftime("%Y-%m-%d"))
        
        # Date to
        tk.Label(search_frame, text="Date To:", font=("Arial", 10)).grid(row=2, column=0, sticky=tk.W, pady=5, padx=5)
        self.date_to_entry = tk.Entry(search_frame, width=20, font=("Arial", 10))
        self.date_to_entry.grid(row=2, column=1, pady=5, padx=5)
        self.date_to_entry.insert(0, date.today().strftime("%Y-%m-%d"))
        
        # Search button
        tk.Button(search_frame, text="Search", command=self.search_invoices, bg="#27ae60", fg="white", width=15, font=("Arial", 10, "bold")).grid(row=2, column=2, columnspan=2, pady=10, padx=5)
        
        # Results frame
        results_frame = tk.LabelFrame(self.parent, text="Search Results", font=("Arial", 12, "bold"), padx=10, pady=10)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Treeview for results
        columns = ('Invoice No', 'Date', 'Customer', 'Branch', 'Total', 'Paid', 'Balance', 'invoice_id')
        self.results_tree = ttk.Treeview(results_frame, columns=columns, show='headings', height=15)
        
        visible_cols = ('Invoice No', 'Date', 'Customer', 'Branch', 'Total', 'Paid', 'Balance')
        for col in visible_cols:
            self.results_tree.heading(col, text=col)
            self.results_tree.column(col, width=120, anchor=tk.CENTER)
        
        # Hide invoice_id column
        self.results_tree.heading('invoice_id', text='')
        self.results_tree.column('invoice_id', width=0, stretch=False)
        
        self.results_tree.column('Customer', width=150)
        self.results_tree.column('Branch', width=150)
        
        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=scrollbar.set)
        
        self.results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.results_tree.bind('<Double-1>', self.on_invoice_double_click)
        
        # Action buttons
        btn_frame = tk.Frame(self.parent)
        btn_frame.pack(pady=10)
        
        tk.Button(btn_frame, text="View/Print Invoice", command=self.view_invoice, bg="#3498db", fg="white", width=20).pack(side=tk.LEFT, padx=5)
    
    def search_invoices(self):
        """Search for invoices"""
        try:
            # Get search criteria
            branch_id = None
            branch_str = self.branch_var.get()
            if branch_str and branch_str != "All Branches":
                for branch in self.branches:
                    if branch.name == branch_str:
                        branch_id = branch.id
                        break
            
            invoice_number = self.invoice_number_entry.get().strip() or None
            customer_name = self.customer_name_entry.get().strip() or None
            date_from = self.date_from_entry.get().strip() or None
            date_to = self.date_to_entry.get().strip() or None
            
            # Search
            invoices = InvoiceService.search_invoices(
                branch_id=branch_id,
                invoice_number=invoice_number,
                customer_name=customer_name,
                date_from=date_from,
                date_to=date_to
            )
            
            # Clear existing results
            for item in self.results_tree.get_children():
                self.results_tree.delete(item)
            
            # Display results
            branch_dict = {b.id: b.name for b in self.branches}
            
            for invoice in invoices:
                invoice_date = invoice.invoice_date
                if isinstance(invoice_date, str):
                    date_str = invoice_date[:10] if len(invoice_date) >= 10 else invoice_date
                else:
                    date_str = invoice_date.strftime("%Y-%m-%d")
                
                branch_name = branch_dict.get(invoice.branch_id, "N/A")
                
                item_id = self.results_tree.insert('', tk.END, values=(
                    invoice.invoice_number,
                    date_str,
                    invoice.customer_name,
                    branch_name,
                    f"Rs. {invoice.grand_total:.2f}",
                    f"Rs. {invoice.paid_amount:.2f}",
                    f"Rs. {invoice.balance:.2f}",
                    str(invoice.id)  # Store invoice ID in hidden column
                ))
            
            if len(invoices) == 0:
                messagebox.showinfo("Search Results", "No invoices found matching the criteria.")
            
        except Exception as e:
            messagebox.showerror("Error", f"Search failed: {str(e)}")
    
    def on_invoice_double_click(self, event):
        """Handle double click on invoice"""
        self.view_invoice()
    
    def view_invoice(self):
        """View selected invoice"""
        selection = self.results_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select an invoice to view")
            return
        
        item_id = selection[0]
        invoice_id_str = self.results_tree.set(item_id, 'invoice_id')
        
        if not invoice_id_str:
            messagebox.showerror("Error", "Could not retrieve invoice ID")
            return
        
        try:
            invoice_id = int(invoice_id_str)
            # Open invoice print window
            print_window = tk.Toplevel(self.parent)
            InvoicePrintWindow(print_window, invoice_id=invoice_id)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open invoice: {str(e)}")

