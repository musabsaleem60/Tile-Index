"""
Reports Window
View and print business reports.
"""

import os
import tkinter as tk
from datetime import date, datetime
from tkinter import messagebox, ttk

import customtkinter as ctk

from repositories.branch_repository import BranchRepository
from services.report_service import ReportService
from ui.theme import COLORS, FONTS, SIZES, SPACING
from utils.datetime_format import format_business_datetime
from utils.report_printer import ReportPrinter
from utils.searchable_combobox import SearchableCombobox


class ReportWindow:
    """Reports window"""

    def __init__(self, parent):
        self.parent = parent
        self.branches = BranchRepository.get_all()
        self.selected_branch_id = None
        self.current_report = None
        self.setup_ui()

    def setup_ui(self):
        header = ctk.CTkLabel(
            self.parent,
            text="Reports",
            font=FONTS["section"],
            fg_color=COLORS["surface"],
            text_color=COLORS["text"],
            height=48,
        )
        header.pack(fill=tk.X)

        main_frame = ctk.CTkFrame(self.parent, fg_color=COLORS["app_bg"], corner_radius=0)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=SPACING["page_x"], pady=SPACING["page_y"])

        left_frame = self.panel(main_frame, "Report Options")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 5))

        self.form_label(left_frame, "Select Branch:", bold=True).grid(row=1, column=0, sticky=tk.W, pady=5, padx=(12, 8))
        self.branch_var = tk.StringVar(value="All Branches")
        self.branch_combo = SearchableCombobox(
            left_frame,
            textvariable=self.branch_var,
            width=SIZES["compact_dropdown_width"],
            state="normal",
            font=FONTS["small"],
        )
        self.branch_combo.set_completion_list(["All Branches"] + [b.name for b in self.branches])
        self.branch_combo.grid(row=1, column=1, pady=5, padx=(0, 12), sticky=tk.W)
        self.branch_combo.bind("<<ComboboxSelected>>", self.on_branch_select)

        self.form_label(left_frame, "Report Type:", bold=True).grid(row=2, column=0, sticky=tk.W, pady=(12, 6), padx=(12, 8))
        self.report_type_var = tk.StringVar(value="Daily Sales")
        report_types = ["Daily Sales", "Branch Stock", "Complete Business Stock", "Monthly Sales"]
        for idx, report_type in enumerate(report_types):
            ctk.CTkRadioButton(
                left_frame,
                text=report_type,
                variable=self.report_type_var,
                value=report_type,
                font=FONTS["small"],
                text_color=COLORS["text"],
                fg_color=COLORS["primary"],
                hover_color=COLORS["primary_hover"],
                border_color=COLORS["border"],
                command=self.on_report_type_change,
            ).grid(row=3 + idx, column=0, columnspan=2, sticky=tk.W, pady=5, padx=12)

        self.date_frame = ctk.CTkFrame(left_frame, fg_color="transparent", corner_radius=0)
        self.date_frame.grid(row=7, column=0, columnspan=2, pady=10, padx=12, sticky=tk.EW)
        self.form_label(self.date_frame, "Date:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.date_entry = self.form_entry(self.date_frame, width=170)
        self.date_entry.grid(row=0, column=1, pady=5, padx=8, sticky=tk.W)
        self.date_entry.insert(0, date.today().strftime("%Y-%m-%d"))

        self.range_frame = ctk.CTkFrame(left_frame, fg_color="transparent", corner_radius=0)
        first_day = date.today().replace(day=1)
        self.form_label(self.range_frame, "From:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.date_from_entry = self.form_entry(self.range_frame, width=170)
        self.date_from_entry.grid(row=0, column=1, pady=5, padx=8, sticky=tk.W)
        self.date_from_entry.insert(0, first_day.strftime("%Y-%m-%d"))
        self.form_label(self.range_frame, "To:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.date_to_entry = self.form_entry(self.range_frame, width=170)
        self.date_to_entry.grid(row=1, column=1, pady=5, padx=8, sticky=tk.W)
        self.date_to_entry.insert(0, date.today().strftime("%Y-%m-%d"))

        self.branch_note_label = ctk.CTkLabel(
            left_frame,
            text="",
            font=FONTS["status"],
            text_color=COLORS["text_muted"],
            wraplength=230,
            height=SIZES["status_label_height"],
        )
        self.branch_note_label.grid(row=8, column=0, columnspan=2, pady=5, padx=12)

        self.action_button(left_frame, "Generate Report", self.generate_report, width=180).grid(row=9, column=0, columnspan=2, pady=15)

        right_frame = self.panel(main_frame, "Report")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        right_frame.grid_columnconfigure(0, weight=1)
        right_frame.grid_rowconfigure(2, weight=1)

        self.summary_label = ctk.CTkLabel(
            right_frame,
            text="Generate a report to view results.",
            font=FONTS["small_bold"],
            text_color=COLORS["text"],
            fg_color=COLORS["card"],
            corner_radius=SIZES["corner_radius"],
            height=38,
            anchor=tk.W,
        )
        self.summary_label.grid(row=1, column=0, columnspan=2, sticky=tk.EW, padx=12, pady=(0, 10))

        table_frame = ctk.CTkFrame(
            right_frame,
            fg_color=COLORS["surface"],
            corner_radius=SIZES["corner_radius"],
            border_width=1,
            border_color=COLORS["border"],
        )
        table_frame.grid(row=2, column=0, columnspan=2, sticky=tk.NSEW, padx=12, pady=(0, 10))
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        self.report_tree = ttk.Treeview(table_frame, columns=(), show="headings", height=22)
        yscrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.report_tree.yview)
        xscrollbar = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.report_tree.xview)
        self.report_tree.configure(yscrollcommand=yscrollbar.set, xscrollcommand=xscrollbar.set)
        self.report_tree.grid(row=0, column=0, sticky=tk.NSEW, padx=(1, 0), pady=(1, 0))
        yscrollbar.grid(row=0, column=1, sticky=tk.NS, pady=(1, 0), padx=(0, 1))
        xscrollbar.grid(row=1, column=0, sticky=tk.EW, padx=(1, 0), pady=(0, 1))

        self.action_button(right_frame, "Print Report", self.print_report, width=160).grid(row=3, column=0, columnspan=2, pady=(0, 12))

        left_frame.grid_columnconfigure(1, weight=1)
        self.on_report_type_change()

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

    def form_label(self, parent, text, bold=False):
        return ctk.CTkLabel(
            parent,
            text=text,
            font=FONTS["small_bold"] if bold else FONTS["small"],
            text_color=COLORS["text"],
            height=SIZES["small_label_height"],
            anchor=tk.W,
        )

    def form_entry(self, parent, width=200):
        return ctk.CTkEntry(
            parent,
            width=width,
            height=SIZES["input_height"],
            font=FONTS["small"],
            fg_color=COLORS["app_bg"],
            border_color=COLORS["border"],
            text_color=COLORS["text"],
        )

    def action_button(self, parent, text, command, width=160):
        return ctk.CTkButton(
            parent,
            text=text,
            command=command,
            width=width,
            height=34,
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            text_color=COLORS["text"],
            font=FONTS["small_bold"],
            corner_radius=SIZES["corner_radius"],
            cursor="hand2",
        )

    def on_branch_select(self, event=None):
        selected = self.branch_var.get()
        self.selected_branch_id = None
        if selected and selected != "All Branches":
            for branch in self.branches:
                if branch.name == selected:
                    self.selected_branch_id = branch.id
                    break

    def on_report_type_change(self):
        report_type = self.report_type_var.get()
        if report_type == "Daily Sales":
            self.date_frame.grid()
            self.range_frame.grid_remove()
            self.branch_note_label.configure(text="Select one branch for daily sales.")
        elif report_type == "Monthly Sales":
            self.date_frame.grid_remove()
            self.range_frame.grid(row=7, column=0, columnspan=2, pady=10, padx=12, sticky=tk.EW)
            self.branch_note_label.configure(text="Branch is optional for monthly sales.")
        else:
            self.date_frame.grid_remove()
            self.range_frame.grid_remove()
            if report_type == "Complete Business Stock":
                self.branch_note_label.configure(text="This report shows stock for all branches.")
            else:
                self.branch_note_label.configure(text="Select one branch for stock.")

    def generate_report(self):
        try:
            report_type = self.report_type_var.get()
            if report_type == "Daily Sales":
                report = self.build_daily_sales_report()
            elif report_type == "Branch Stock":
                report = self.build_branch_stock_report()
            elif report_type == "Complete Business Stock":
                report = self.build_complete_stock_report()
            elif report_type == "Monthly Sales":
                report = self.build_monthly_sales_report()
            else:
                raise ValueError("Unknown report type")

            self.current_report = report
            self.render_report(report)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def build_daily_sales_report(self):
        if not self.selected_branch_id:
            raise ValueError("Please select a branch for daily sales report")
        report_date = self.parse_date(self.date_entry.get().strip(), "Date")
        data = ReportService.get_daily_sales_report(self.selected_branch_id, report_date)
        branch = self.branch_name(data.get("branch_id"))
        rows = []
        for invoice in data.get("invoices", []):
            rows.append({
                "Invoice No": invoice.get("invoice_number", ""),
                "Customer": invoice.get("customer_name", ""),
                "Time": self.time_text(invoice.get("invoice_date")),
                "Total": self.money(invoice.get("grand_total")),
                "Paid": self.money(invoice.get("paid_amount")),
                "Balance": self.money(invoice.get("balance")),
            })
        return {
            "type": "Daily Sales",
            "title": "Daily Sales Report",
            "columns": ["Invoice No", "Customer", "Time", "Total", "Paid", "Balance"],
            "rows": rows,
            "summary": [
                f"Branch: {branch}",
                f"Date: {data.get('date')}",
                f"Invoices: {data.get('total_invoices', 0)}",
                f"Sales: {self.money(data.get('total_sales'))}",
                f"Paid: {self.money(data.get('total_paid'))}",
                f"Balance: {self.money(data.get('total_balance'))}",
            ],
        }

    def build_branch_stock_report(self):
        if not self.selected_branch_id:
            raise ValueError("Please select a branch for stock report")
        data = ReportService.get_branch_stock_report(self.selected_branch_id)
        rows = [self.stock_row(item) for item in data.get("items", [])]
        for item in data.get("sanitary_items", []):
            rows.append({
                "Product": f"{item.get('company_name', '')} - {item.get('product_category', '')}".strip(" -"),
                "Size": item.get("color", "-"),
                "Grade": item.get("sku", "-"),
                "Boxes": "-",
                "Loose": "-",
                "Total Pieces": item.get("quantity", 0),
                "Value": item.get("value_display") or self.money(item.get("stock_value")),
            })
        return {
            "type": "Branch Stock",
            "title": "Branch Stock Report",
            "columns": ["Product", "Size", "Grade", "Boxes", "Loose", "Total Pieces", "Value"],
            "rows": rows,
            "summary": [
                f"Branch: {data.get('branch_name', self.branch_name(self.selected_branch_id))}",
                f"Rows: {len(rows)}",
                f"Stock Value: {self.money(data.get('total_value'))}",
            ],
        }

    def build_complete_stock_report(self):
        data = ReportService.get_complete_business_stock_report()
        rows = []
        for branch in data.get("branches", []):
            for item in branch.get("items", []):
                row = self.stock_row(item)
                row["Branch"] = branch.get("branch_name", "")
                rows.append(row)
            for item in branch.get("sanitary_items", []):
                rows.append({
                    "Branch": branch.get("branch_name", ""),
                    "Product": f"{item.get('company_name', '')} - {item.get('product_category', '')}".strip(" -"),
                    "Size": item.get("color", "-"),
                    "Grade": item.get("sku", "-"),
                    "Boxes": "-",
                    "Loose": "-",
                    "Total Pieces": item.get("quantity", 0),
                    "Value": item.get("value_display") or self.money(item.get("stock_value")),
                })
        return {
            "type": "Complete Business Stock",
            "title": "Complete Business Stock Report",
            "columns": ["Branch", "Product", "Size", "Grade", "Boxes", "Loose", "Total Pieces", "Value"],
            "rows": rows,
            "summary": [
                f"Branches: {data.get('total_branches', 0)}",
                f"Rows: {len(rows)}",
                f"Stock Value: {self.money(data.get('total_value'))}",
            ],
        }

    def build_monthly_sales_report(self):
        date_from = self.parse_date(self.date_from_entry.get().strip(), "From")
        date_to = self.parse_date(self.date_to_entry.get().strip(), "To")
        if date_to < date_from:
            raise ValueError("Date To cannot be before Date From")
        data = ReportService.get_monthly_sales_report(date_from, date_to, self.selected_branch_id)
        rows = []
        for item in data.get("items", []):
            rows.append({
                "Month": item.get("month", ""),
                "Branch": item.get("branch_name", ""),
                "Invoice Count": item.get("invoice_count", 0),
                "Total Sales": self.money(item.get("total_sales")),
                "Total Paid": self.money(item.get("total_paid")),
                "Total Balance": self.money(item.get("total_balance")),
            })
        return {
            "type": "Monthly Sales",
            "title": "Monthly Sales Report",
            "columns": ["Month", "Branch", "Invoice Count", "Total Sales", "Total Paid", "Total Balance"],
            "rows": rows,
            "summary": [
                f"Date Range: {data.get('date_from')} to {data.get('date_to')}",
                f"Branch: {self.branch_name(self.selected_branch_id) if self.selected_branch_id else 'All Branches'}",
                f"Invoices: {data.get('total_invoices', 0)}",
                f"Sales: {self.money(data.get('total_sales'))}",
                f"Paid: {self.money(data.get('total_paid'))}",
                f"Balance: {self.money(data.get('total_balance'))}",
            ],
        }

    def render_report(self, report):
        columns = report["columns"]
        for item in self.report_tree.get_children():
            self.report_tree.delete(item)
        self.report_tree.configure(columns=columns)

        widths = {
            "Invoice No": 120,
            "Customer": 190,
            "Time": 100,
            "Total": 110,
            "Paid": 110,
            "Balance": 110,
            "Product": 240,
            "Size": 90,
            "Grade": 130,
            "Boxes": 80,
            "Loose": 80,
            "Total Pieces": 105,
            "Value": 130,
            "Branch": 160,
            "Month": 90,
            "Invoice Count": 105,
            "Total Sales": 120,
            "Total Paid": 120,
            "Total Balance": 120,
        }
        numeric_columns = {
            "Total", "Paid", "Balance", "Boxes", "Loose", "Total Pieces", "Value",
            "Invoice Count", "Total Sales", "Total Paid", "Total Balance",
        }
        for column in columns:
            self.report_tree.heading(column, text=column)
            self.report_tree.column(
                column,
                width=widths.get(column, 120),
                anchor=tk.E if column in numeric_columns else tk.W,
                stretch=True,
            )

        for row in report["rows"]:
            self.report_tree.insert("", tk.END, values=[row.get(column, "") for column in columns])

        self.summary_label.configure(text="   " + "   |   ".join(report["summary"]))

    def print_report(self):
        if not self.current_report:
            messagebox.showwarning("Warning", "No report to print")
            return
        try:
            pdf_path = ReportPrinter(self.current_report).generate_pdf()
            try:
                os.startfile(pdf_path)
            except Exception as e:
                messagebox.showwarning(
                    "Report PDF Created",
                    "The report PDF was created, but Windows could not open a PDF viewer.\n\n"
                    f"File path:\n{pdf_path}\n\nError: {str(e)}",
                )
        except Exception as e:
            messagebox.showerror("Print Error", f"Failed to generate report PDF: {str(e)}")

    @staticmethod
    def stock_row(item):
        return {
            "Product": item.get("product_name", ""),
            "Size": item.get("tile_size", ""),
            "Grade": item.get("grade", ""),
            "Boxes": item.get("boxes", 0),
            "Loose": item.get("loose_pieces", 0),
            "Total Pieces": item.get("total_pieces", 0),
            "Value": item.get("value_display") or ReportWindow.money(item.get("stock_value")),
        }

    def branch_name(self, branch_id):
        for branch in self.branches:
            if branch.id == branch_id:
                return branch.name
        return "N/A"

    @staticmethod
    def parse_date(value, label):
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except Exception:
            raise ValueError(f"Invalid {label} date format. Use YYYY-MM-DD")

    @staticmethod
    def money(value):
        try:
            return f"Rs. {float(value or 0):.2f}"
        except Exception:
            return "Rs. 0.00"

    @staticmethod
    def time_text(value):
        if not value:
            return ""
        try:
            return format_business_datetime(value, fmt="%H:%M")
        except Exception:
            return str(value)[11:16]
