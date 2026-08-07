"""
Invoice Search Window
Search and view existing invoices
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import customtkinter as ctk
from datetime import datetime, date
from repositories.branch_repository import BranchRepository
from services.invoice_service import InvoiceService
from utils.datetime_format import format_business_datetime
from utils.invoice_printer import InvoicePrintWindow
from utils.searchable_combobox import SearchableCombobox
from ui.theme import COLORS, FONTS, SIZES, SPACING


class InvoiceSearchWindow:
    """Invoice search and view window"""
    
    def __init__(self, parent, current_user=None):
        self.parent = parent
        self.current_user = current_user
        
        self.branches = BranchRepository.get_all()
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the search UI"""
        # Header
        header = ctk.CTkLabel(
            self.parent,
            text="Search & View Invoices",
            font=FONTS["section"],
            fg_color=COLORS["surface"],
            text_color=COLORS["text"],
            height=48,
        )
        header.pack(fill=tk.X)

        page = ctk.CTkFrame(self.parent, fg_color=COLORS["app_bg"], corner_radius=0)
        page.pack(fill=tk.BOTH, expand=True, padx=SPACING["page_x"], pady=SPACING["page_y"])

        # Search frame
        search_frame = self.panel(page, "Search Criteria")
        search_frame.pack(fill=tk.X, pady=(0, 12))
        for col in (1, 3):
            search_frame.grid_columnconfigure(col, weight=1)

        # Branch
        self.form_label(search_frame, "Branch:").grid(row=1, column=0, sticky=tk.W, pady=5, padx=8)
        self.branch_var = tk.StringVar()
        self.branch_combo = SearchableCombobox(search_frame, textvariable=self.branch_var, width=SIZES["compact_dropdown_width"], state="normal", font=FONTS["small"])
        self.branch_combo.set_completion_list(["All Branches"] + [f"{b.name}" for b in self.branches])
        self.branch_combo.grid(row=1, column=1, pady=5, padx=8, sticky=tk.W)

        # Invoice number
        self.form_label(search_frame, "Invoice Number:").grid(row=1, column=2, sticky=tk.W, pady=5, padx=8)
        self.invoice_number_entry = self.form_entry(search_frame, width=190)
        self.invoice_number_entry.grid(row=1, column=3, pady=5, padx=8, sticky=tk.W)

        # Customer name
        self.form_label(search_frame, "Customer Name:").grid(row=2, column=0, sticky=tk.W, pady=5, padx=8)
        self.customer_name_entry = self.form_entry(search_frame, width=240)
        self.customer_name_entry.grid(row=2, column=1, pady=5, padx=8, sticky=tk.W)

        # Date from
        self.form_label(search_frame, "Date From:").grid(row=2, column=2, sticky=tk.W, pady=5, padx=8)
        self.date_from_entry = self.form_entry(search_frame, width=190)
        self.date_from_entry.grid(row=2, column=3, pady=5, padx=8, sticky=tk.W)
        self.date_from_entry.insert(0, date.today().strftime("%Y-%m-%d"))

        # Date to
        self.form_label(search_frame, "Date To:").grid(row=3, column=0, sticky=tk.W, pady=5, padx=8)
        self.date_to_entry = self.form_entry(search_frame, width=190)
        self.date_to_entry.grid(row=3, column=1, pady=5, padx=8, sticky=tk.W)
        self.date_to_entry.insert(0, date.today().strftime("%Y-%m-%d"))

        # Search button
        self.action_button(search_frame, "Search", self.search_invoices, width=150).grid(row=3, column=2, columnspan=2, pady=8, padx=8, sticky=tk.W)

        # Results frame
        results_frame = self.panel(page, "Search Results")
        results_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 12))
        results_frame.grid_rowconfigure(1, weight=1)
        results_frame.grid_columnconfigure(0, weight=1)

        # Treeview for results
        columns = ('Invoice No', 'Status', 'Date', 'Customer', 'Branch', 'Total', 'Paid', 'Balance', 'invoice_id')
        self.results_tree = ttk.Treeview(results_frame, columns=columns, show='headings', height=15)

        column_widths = {
            'Invoice No': 120,
            'Status': 85,
            'Date': 115,
            'Customer': 180,
            'Branch': 170,
            'Total': 120,
            'Paid': 120,
            'Balance': 120,
        }
        visible_cols = ('Invoice No', 'Status', 'Date', 'Customer', 'Branch', 'Total', 'Paid', 'Balance')
        for col in visible_cols:
            self.results_tree.heading(col, text=col)
            self.results_tree.column(col, width=column_widths[col], minwidth=column_widths[col], anchor=tk.CENTER)

        # Hide invoice_id column
        self.results_tree.heading('invoice_id', text='')
        self.results_tree.column('invoice_id', width=0, stretch=False)

        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.results_tree.yview)
        xscrollbar = ttk.Scrollbar(results_frame, orient=tk.HORIZONTAL, command=self.results_tree.xview)
        self.results_tree.configure(yscrollcommand=scrollbar.set, xscrollcommand=xscrollbar.set)

        self.results_tree.grid(row=1, column=0, sticky=tk.NSEW, padx=(12, 0), pady=(0, 0))
        scrollbar.grid(row=1, column=1, sticky=tk.NS, padx=(0, 12), pady=(0, 0))
        xscrollbar.grid(row=2, column=0, sticky=tk.EW, padx=(12, 0), pady=(0, 12))

        self.results_tree.bind('<Double-1>', self.on_invoice_double_click)

        # Action buttons
        btn_frame = ctk.CTkFrame(page, fg_color="transparent", corner_radius=0)
        btn_frame.pack(pady=(0, 4))

        self.action_button(btn_frame, "View/Print Invoice", self.view_invoice, width=190).pack(side=tk.LEFT, padx=5)
        if getattr(self.current_user, 'role', '') == 'admin':
            self.action_button(btn_frame, "Void Invoice", self.void_invoice, width=170, danger=True).pack(side=tk.LEFT, padx=5)

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
        ).grid(row=0, column=0, columnspan=4, sticky=tk.EW, padx=12, pady=(10, 8))
        return panel

    def form_label(self, parent, text):
        return ctk.CTkLabel(
            parent,
            text=text,
            font=FONTS["small"],
            text_color=COLORS["text"],
            height=SIZES["small_label_height"],
            anchor=tk.W,
        )

    def form_entry(self, parent, width):
        return ctk.CTkEntry(
            parent,
            width=width,
            height=SIZES["input_height"],
            font=FONTS["small"],
            fg_color=COLORS["app_bg"],
            border_color=COLORS["border"],
            text_color=COLORS["text"],
        )

    def action_button(self, parent, text, command, width=150, danger=False):
        return ctk.CTkButton(
            parent,
            text=text,
            command=command,
            width=width,
            height=34,
            fg_color=COLORS["danger"] if danger else COLORS["primary"],
            hover_color=COLORS["danger_hover"] if danger else COLORS["primary_hover"],
            text_color=COLORS["text"],
            font=FONTS["small_bold"],
            corner_radius=SIZES["corner_radius"],
            cursor="hand2",
        )
    
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
                date_str = format_business_datetime(invoice.invoice_date, fmt="%Y-%m-%d")
                
                branch_name = branch_dict.get(invoice.branch_id, "N/A")
                status_text = "VOID" if getattr(invoice, 'status', 'active') == 'void' else "Active"
                
                item_id = self.results_tree.insert('', tk.END, values=(
                    invoice.invoice_number,
                    status_text,
                    date_str,
                    invoice.customer_name,
                    branch_name,
                    f"Rs. {invoice.grand_total:.2f}",
                    f"Rs. {invoice.paid_amount:.2f}",
                    f"Rs. {invoice.balance:.2f}",
                    str(invoice.id)  # Store invoice ID in hidden column
                ))
                if status_text == "VOID":
                    self.results_tree.item(item_id, tags=("void",))
            self.results_tree.tag_configure("void", foreground=COLORS["danger"])
            
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

    def void_invoice(self):
        """Void selected invoice."""
        selection = self.results_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select an invoice to void")
            return

        item_id = selection[0]
        invoice_id_str = self.results_tree.set(item_id, 'invoice_id')
        invoice_number = self.results_tree.set(item_id, 'Invoice No')
        status_text = self.results_tree.set(item_id, 'Status')
        if status_text == "VOID":
            messagebox.showinfo("Invoice Already Void", "This invoice is already marked VOID.")
            return

        reason = simpledialog.askstring(
            "Void Invoice",
            f"Enter reason for voiding invoice {invoice_number}.\nMinimum 10 characters:",
            parent=self.parent,
        )
        if reason is None:
            return
        reason = reason.strip()
        if len(reason) < 10:
            messagebox.showerror("Reason Required", "Void reason must be at least 10 characters.")
            return
        if not messagebox.askyesno(
            "Confirm Void",
            f"Void invoice {invoice_number}?\n\nThis will restore stock and exclude the invoice from sales totals. This cannot be undone.",
        ):
            return

        try:
            InvoiceService.void_invoice(int(invoice_id_str), reason)
            messagebox.showinfo("Invoice Voided", f"Invoice {invoice_number} has been marked VOID.")
            self.search_invoices()
        except Exception as e:
            messagebox.showerror("Void Failed", str(e))

