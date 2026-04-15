"""
Reports Window
View various reports
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date
from repositories.branch_repository import BranchRepository
from services.report_service import ReportService
from utils.searchable_combobox import SearchableCombobox


class ReportWindow:
    """Reports window"""
    
    def __init__(self, parent):
        self.parent = parent
        
        self.branches = BranchRepository.get_all()
        self.selected_branch_id = None
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the reports UI"""
        # Header
        header = tk.Label(
            self.parent,
            text="Reports",
            font=("Arial", 18, "bold"),
            bg="#e67e22",
            fg="white",
            pady=10
        )
        header.pack(fill=tk.X)
        
        # Main container
        main_frame = tk.Frame(self.parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel - Report Selection
        left_frame = tk.LabelFrame(main_frame, text="Report Options", font=("Arial", 12, "bold"), padx=10, pady=10)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 5))
        
        # Branch selection
        tk.Label(left_frame, text="Select Branch:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.branch_var = tk.StringVar()
        self.branch_combo = SearchableCombobox(left_frame, textvariable=self.branch_var, width=25, state="normal", font=("Arial", 10))
        self.branch_combo.set_completion_list(["All Branches"] + [f"{b.name}" for b in self.branches])
        self.branch_combo.grid(row=0, column=1, pady=5, padx=5, sticky=tk.W)
        self.branch_combo.bind('<<ComboboxSelected>>', self.on_branch_select)
        
        # Report type selection
        tk.Label(left_frame, text="Report Type:", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky=tk.W, pady=10)
        self.report_type_var = tk.StringVar(value="Daily Sales")
        
        report_types = ["Daily Sales", "Branch Stock", "Complete Business Stock"]
        for idx, rtype in enumerate(report_types):
            tk.Radiobutton(
                left_frame,
                text=rtype,
                variable=self.report_type_var,
                value=rtype,
                font=("Arial", 10),
                command=self.on_report_type_change
            ).grid(row=2+idx, column=0, columnspan=2, sticky=tk.W, pady=3)
        
        # Date selection for daily sales
        self.date_frame = tk.Frame(left_frame)
        self.date_frame.grid(row=5, column=0, columnspan=2, pady=10, sticky=tk.EW)
        
        tk.Label(self.date_frame, text="Date:", font=("Arial", 10)).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.date_entry = tk.Entry(self.date_frame, width=20, font=("Arial", 10))
        self.date_entry.grid(row=0, column=1, pady=5, padx=5)
        self.date_entry.insert(0, date.today().strftime("%Y-%m-%d"))
        
        # Branch selection note for Complete Business Stock
        self.branch_note_label = tk.Label(left_frame, text="", font=("Arial", 9), fg="blue", wraplength=200)
        self.branch_note_label.grid(row=6, column=0, columnspan=2, pady=5)
        
        # Generate button
        tk.Button(left_frame, text="Generate Report", command=self.generate_report, bg="#3498db", fg="white", width=20, font=("Arial", 10, "bold")).grid(row=6, column=0, columnspan=2, pady=15)
        
        # Right panel - Report Display
        right_frame = tk.LabelFrame(main_frame, text="Report", font=("Arial", 12, "bold"), padx=10, pady=10)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # Text widget with scrollbar
        text_frame = tk.Frame(right_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        self.report_text = tk.Text(text_frame, wrap=tk.WORD, font=("Courier", 10), state=tk.DISABLED)
        scrollbar = tk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.report_text.yview)
        self.report_text.configure(yscrollcommand=scrollbar.set)
        
        self.report_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Print button
        tk.Button(right_frame, text="Print Report", command=self.print_report, bg="#27ae60", fg="white", width=20).pack(pady=5)
        
        # Configure grid
        left_frame.grid_columnconfigure(1, weight=1)
    
    def on_branch_select(self, event):
        """Handle branch selection"""
        selected = self.branch_var.get()
        if selected == "All Branches":
            self.selected_branch_id = None
        else:
            for branch in self.branches:
                if branch.name == selected:
                    self.selected_branch_id = branch.id
                    break
    
    def on_report_type_change(self):
        """Handle report type change"""
        report_type = self.report_type_var.get()
        
        # Show/hide date frame based on report type
        if report_type == "Daily Sales":
            self.date_frame.grid()
            self.branch_note_label.config(text="")
        else:
            self.date_frame.grid_remove()
            if report_type == "Complete Business Stock":
                self.branch_note_label.config(text="Note: This report shows stock for ALL branches")
            else:
                self.branch_note_label.config(text="")
    
    def generate_report(self):
        """Generate the selected report"""
        try:
            report_type = self.report_type_var.get()
            
            self.report_text.config(state=tk.NORMAL)
            self.report_text.delete(1.0, tk.END)
            
            if report_type == "Daily Sales":
                if not self.selected_branch_id:
                    raise ValueError("Please select a branch for daily sales report")
                
                date_str = self.date_entry.get()
                try:
                    report_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                except:
                    raise ValueError("Invalid date format. Use YYYY-MM-DD")
                
                report = ReportService.get_daily_sales_report(self.selected_branch_id, report_date)
                self.display_daily_sales_report(report)
                
            elif report_type == "Branch Stock":
                if not self.selected_branch_id:
                    raise ValueError("Please select a branch for stock report")
                
                report = ReportService.get_branch_stock_report(self.selected_branch_id)
                self.display_stock_report(report)
                
            elif report_type == "Complete Business Stock":
                report = ReportService.get_complete_business_stock_report()
                self.display_complete_stock_report(report)
            
            self.report_text.config(state=tk.DISABLED)
            
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.report_text.config(state=tk.DISABLED)
    
    def display_daily_sales_report(self, report):
        """Display daily sales report"""
        branch = None
        for b in self.branches:
            if b.id == report['branch_id']:
                branch = b
                break
        
        self.report_text.insert(tk.END, "=" * 70 + "\n")
        self.report_text.insert(tk.END, "DAILY SALES REPORT\n")
        self.report_text.insert(tk.END, "=" * 70 + "\n\n")
        self.report_text.insert(tk.END, f"Branch: {branch.name if branch else 'N/A'}\n")
        self.report_text.insert(tk.END, f"Date: {report['date']}\n")
        self.report_text.insert(tk.END, f"Total Invoices: {report['total_invoices']}\n\n")
        self.report_text.insert(tk.END, "-" * 70 + "\n")
        self.report_text.insert(tk.END, f"{'Invoice No':<15} {'Customer':<25} {'Total':<15} {'Paid':<15}\n")
        self.report_text.insert(tk.END, "-" * 70 + "\n")
        
        for inv in report['invoices']:
            self.report_text.insert(tk.END, f"{inv['invoice_number']:<15} {inv['customer_name']:<25} Rs. {inv['grand_total']:<12.2f} Rs. {inv['paid_amount']:<12.2f}\n")
        
        self.report_text.insert(tk.END, "-" * 70 + "\n")
        self.report_text.insert(tk.END, f"\nTotal Sales: Rs. {report['total_sales']:.2f}\n")
        self.report_text.insert(tk.END, f"Total Paid: Rs. {report['total_paid']:.2f}\n")
        self.report_text.insert(tk.END, f"Total Balance: Rs. {report['total_balance']:.2f}\n")
    
    def display_stock_report(self, report):
        """Display stock report"""
        self.report_text.insert(tk.END, "=" * 90 + "\n")
        self.report_text.insert(tk.END, "BRANCH STOCK REPORT\n")
        self.report_text.insert(tk.END, "=" * 90 + "\n\n")
        self.report_text.insert(tk.END, f"Branch: {report.get('branch_name', 'N/A')}\n\n")
        self.report_text.insert(tk.END, "-" * 90 + "\n")
        self.report_text.insert(tk.END, f"{'Product':<20} {'Size':<10} {'Grade':<6} {'Boxes':<8} {'Pieces':<8} {'Value (Rs.)':<15}\n")
        self.report_text.insert(tk.END, "-" * 90 + "\n")
        
        for item in report['items']:
            self.report_text.insert(tk.END, f"{item['product_name']:<20} {item['tile_size']:<10} {item['grade']:<6} "
                                           f"{item['boxes']:<8} {item['loose_pieces']:<8} {item['stock_value']:<15.2f}\n")
        
        self.report_text.insert(tk.END, "-" * 90 + "\n")
        self.report_text.insert(tk.END, f"\nTotal Stock Value: Rs. {report['total_value']:.2f}\n")
    
    def display_complete_stock_report(self, report):
        """Display complete business stock report (all branches)"""
        self.report_text.insert(tk.END, "=" * 100 + "\n")
        self.report_text.insert(tk.END, "COMPLETE BUSINESS STOCK REPORT\n")
        self.report_text.insert(tk.END, "=" * 100 + "\n\n")
        self.report_text.insert(tk.END, f"Report Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        self.report_text.insert(tk.END, f"Total Branches: {report['total_branches']}\n")
        self.report_text.insert(tk.END, f"Total Products: {report['total_products']}\n")
        self.report_text.insert(tk.END, f"Total Stock Value: Rs. {report['total_value']:.2f}\n\n")
        
        # Display by branch
        for branch_data in report['branches']:
            self.report_text.insert(tk.END, "\n" + "=" * 100 + "\n")
            self.report_text.insert(tk.END, f"BRANCH: {branch_data['branch_name']}\n")
            self.report_text.insert(tk.END, "=" * 100 + "\n\n")
            self.report_text.insert(tk.END, f"{'Product':<25} {'Size':<12} {'Grade':<20} {'Boxes':<10} {'Pieces':<10} {'Value (Rs.)':<15}\n")
            self.report_text.insert(tk.END, "-" * 100 + "\n")
            
            for item in branch_data['items']:
                self.report_text.insert(tk.END, f"{item['product_name']:<25} {item['tile_size']:<12} {item['grade']:<20} "
                                               f"{item['boxes']:<10} {item['loose_pieces']:<10} {item['stock_value']:<15.2f}\n")
            
            self.report_text.insert(tk.END, "-" * 100 + "\n")
            self.report_text.insert(tk.END, f"Branch Total Value: Rs. {branch_data['branch_total_value']:.2f}\n")
        
        self.report_text.insert(tk.END, "\n" + "=" * 100 + "\n")
        self.report_text.insert(tk.END, f"GRAND TOTAL STOCK VALUE: Rs. {report['total_value']:.2f}\n")
        self.report_text.insert(tk.END, "=" * 100 + "\n")
    
    def print_report(self):
        """Print report"""
        content = self.report_text.get(1.0, tk.END)
        if not content.strip():
            messagebox.showwarning("Warning", "No report to print")
            return
        
        # For now, show a message. In production, implement actual printing
        messagebox.showinfo("Print", "Print functionality will send report to printer.\nThis feature can be extended with actual printer integration.")

