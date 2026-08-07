"""
Invoice Printer Utility
Generates printable invoice format in Pakistani style
"""

import os
import re
import tkinter as tk
from tkinter import messagebox, ttk

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from repositories.branch_repository import BranchRepository
from repositories.product_repository import ProductRepository
from repositories.accessory_repository import AccessoryRepository
from repositories.sanitary_repository import SanitaryProductRepository
from services.invoice_service import InvoiceService
from utils.accessory_labels import accessory_display_label
from utils.datetime_format import format_business_datetime


class InvoicePrintWindow:
    """Window for displaying and printing invoices"""
    
    def __init__(self, parent, invoice_id=None, invoice_data=None):
        self.parent = parent
        self.set_window_title("Invoice - Tile Index")
        self.set_window_geometry("800x1000")
        
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
        self.sanitary_products = {p.id: p for p in SanitaryProductRepository.get_all()}
        
        self.setup_ui()

    def set_window_title(self, title):
        try:
            window = self.parent.winfo_toplevel()
            if hasattr(window, "title"):
                window.title(title)
        except Exception:
            pass

    def set_window_geometry(self, geometry):
        try:
            window = self.parent.winfo_toplevel()
            if hasattr(window, "geometry"):
                window.geometry(geometry)
        except Exception:
            pass
    
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
        
        tk.Button(btn_frame, text="Print Invoice", command=self.print_invoice,
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
        if getattr(self.invoice, 'status', 'active') == 'void':
            tk.Label(left_details, text="STATUS: VOID", 
                    font=("Arial", 14, "bold"), bg="white", fg="#c0392b", anchor=tk.W).pack(anchor=tk.W, pady=(5, 0))
            if getattr(self.invoice, 'void_reason', None):
                tk.Label(left_details, text=f"Void Reason: {self.invoice.void_reason}", 
                        font=("Arial", 10, "bold"), bg="white", fg="#c0392b", anchor=tk.W).pack(anchor=tk.W, pady=(3, 0))
        
        date_str = format_business_datetime(self.invoice.invoice_date, fmt="%d-%m-%Y %H:%M:%S")
        
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
                    product_name = accessory_display_label(accessory)
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
            elif item.sanitary_product_id:
                sanitary_product = self.sanitary_products.get(item.sanitary_product_id)
                if sanitary_product:
                    product_name = f"{sanitary_product.company_name} - {sanitary_product.product_category}"
                    size = sanitary_product.color
                    grade = sanitary_product.sku
                else:
                    product_name = "Unknown Sanitary Product"
                    size = "-"
                    grade = "-"

                qty_main = str(item.boxes)
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
    
    def print_invoice(self):
        """Generate a PDF invoice and open it with the default PDF viewer."""
        try:
            pdf_path = self.generate_invoice_pdf()
            try:
                os.startfile(pdf_path)
            except Exception as e:
                messagebox.showwarning(
                    "Invoice PDF Created",
                    "The invoice PDF was created, but Windows could not open a PDF viewer.\n\n"
                    f"File path:\n{pdf_path}\n\nError: {str(e)}"
                )
        except Exception as e:
            messagebox.showerror("Print Error", f"Failed to generate invoice PDF: {str(e)}")

    def generate_invoice_pdf(self):
        """Create a black-on-white PDF invoice and return the file path."""
        pdf_path = self.next_invoice_pdf_path()
        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=landscape(A4),
            rightMargin=10 * mm,
            leftMargin=10 * mm,
            topMargin=10 * mm,
            bottomMargin=10 * mm,
            title=f"Invoice {self.invoice.invoice_number}",
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "InvoiceTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=colors.black,
            alignment=1,
            spaceAfter=4,
        )
        subtitle_style = ParagraphStyle(
            "InvoiceSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=12,
            textColor=colors.black,
            alignment=1,
        )
        normal = ParagraphStyle(
            "InvoiceNormal",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=colors.black,
        )
        normal_bold = ParagraphStyle(
            "InvoiceNormalBold",
            parent=normal,
            fontName="Helvetica-Bold",
        )
        void_style = ParagraphStyle(
            "InvoiceVoid",
            parent=normal_bold,
            fontSize=13,
            leading=16,
            textColor=colors.black,
        )

        story = [
            Paragraph("TILE INDEX", title_style),
            Paragraph("Tiles Trading Company", subtitle_style),
            Paragraph("Pakistan", subtitle_style),
        ]
        if self.branch:
            story.append(Paragraph(self.escape_text(self.branch.name), subtitle_style))
        story.append(Spacer(1, 8))

        invoice_date = format_business_datetime(self.invoice.invoice_date, fmt="%d-%m-%Y %H:%M:%S")
        details_left = [
            Paragraph(f"<b>Invoice No:</b> {self.escape_text(self.invoice.invoice_number)}", normal),
            Paragraph(f"<b>Date:</b> {self.escape_text(invoice_date)}", normal),
        ]
        if getattr(self.invoice, "status", "active") == "void":
            details_left.insert(1, Paragraph("STATUS: VOID", void_style))
            if getattr(self.invoice, "void_reason", None):
                details_left.insert(2, Paragraph(f"<b>Void Reason:</b> {self.escape_text(self.invoice.void_reason)}", normal))

        details_right = [
            Paragraph("<b>Customer Details</b>", normal),
            Paragraph(f"<b>Name:</b> {self.escape_text(self.invoice.customer_name)}", normal),
        ]
        if self.invoice.customer_contact:
            details_right.append(Paragraph(f"<b>Contact:</b> {self.escape_text(self.invoice.customer_contact)}", normal))

        details_table = Table([[details_left, details_right]], colWidths=[130 * mm, 130 * mm])
        details_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.black),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.black),
            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.extend([details_table, Spacer(1, 8)])

        table_data = [[
            Paragraph("<b>S.No</b>", normal_bold),
            Paragraph("<b>Item</b>", normal_bold),
            Paragraph("<b>Size</b>", normal_bold),
            Paragraph("<b>Grade</b>", normal_bold),
            Paragraph("<b>Boxes</b>", normal_bold),
            Paragraph("<b>Pieces</b>", normal_bold),
            Paragraph("<b>Rate/m2</b>", normal_bold),
            Paragraph("<b>Rate/Box</b>", normal_bold),
            Paragraph("<b>Rate/Piece</b>", normal_bold),
            Paragraph("<b>Total</b>", normal_bold),
        ]]

        for idx, item in enumerate(self.invoice.items, 1):
            table_data.append([
                str(idx),
                Paragraph(self.escape_text(self.item_label(item)), normal),
                Paragraph(self.escape_text(self.item_size(item)), normal),
                Paragraph(self.escape_text(item.grade or "-"), normal),
                self.quantity_text(item.boxes),
                self.quantity_text(item.loose_pieces) if item.product_id else "-",
                self.money_text(item.rate_per_sqm) if item.product_id else "-",
                self.money_text(item.rate_per_box),
                self.money_text(item.rate_per_piece) if item.product_id else "-",
                self.money_text(item.line_total),
            ])

        items_table = Table(
            table_data,
            colWidths=[12 * mm, 60 * mm, 22 * mm, 24 * mm, 18 * mm, 18 * mm, 25 * mm, 25 * mm, 27 * mm, 28 * mm],
            repeatRows=1,
        )
        items_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.white),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.black),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("LEADING", (0, 0), (-1, -1), 9),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("ALIGN", (4, 1), (-1, -1), "RIGHT"),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.extend([items_table, Spacer(1, 10)])

        totals_rows = [
            ["Sub Total", self.money_text(self.invoice.subtotal)],
        ]
        if self.invoice.discount > 0:
            totals_rows.append(["Discount", self.money_text(self.invoice.discount)])
        totals_rows.extend([
            ["Grand Total", self.money_text(self.invoice.grand_total)],
            ["Paid Amount", self.money_text(self.invoice.paid_amount)],
            ["Balance", self.money_text(self.invoice.balance)],
        ])
        totals_table = Table(totals_rows, colWidths=[45 * mm, 35 * mm], hAlign="RIGHT")
        totals_table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.35, colors.black),
            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME", (0, 2 if self.invoice.discount > 0 else 1), (-1, 2 if self.invoice.discount > 0 else 1), "Helvetica-Bold"),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.extend([totals_table, Spacer(1, 12)])

        story.append(Paragraph("Thank you for your business!", subtitle_style))
        story.append(Paragraph("Tile Index - Quality Tiles, Trusted Service", subtitle_style))

        doc.build(story)
        return pdf_path

    def invoice_pdf_dir(self):
        base_dir = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        path = os.path.join(base_dir, "TileIndex", "invoices")
        os.makedirs(path, exist_ok=True)
        return path

    def next_invoice_pdf_path(self):
        invoice_number = self.safe_filename(self.invoice.invoice_number or "invoice")
        base = f"invoice_{invoice_number}.pdf"
        folder = self.invoice_pdf_dir()
        candidate = os.path.join(folder, base)
        if not os.path.exists(candidate):
            return candidate

        stem, ext = os.path.splitext(base)
        counter = 2
        while True:
            candidate = os.path.join(folder, f"{stem}_{counter}{ext}")
            if not os.path.exists(candidate):
                return candidate
            counter += 1

    @staticmethod
    def safe_filename(value):
        return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value)).strip("_") or "invoice"

    @staticmethod
    def escape_text(value):
        return (
            str(value or "")
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    @staticmethod
    def money_text(value):
        try:
            return f"Rs. {float(value or 0):.2f}"
        except (TypeError, ValueError):
            return "Rs. 0.00"

    @staticmethod
    def quantity_text(value):
        try:
            number = float(value or 0)
        except (TypeError, ValueError):
            return "0"
        if number.is_integer():
            return str(int(number))
        return str(number)

    def item_label(self, item):
        if item.product_id:
            product = self.products.get(item.product_id)
            return product.name if product else "Unknown Tile"
        if item.accessory_id:
            accessory = self.accessories.get(item.accessory_id)
            return accessory_display_label(accessory) if accessory else "Unknown Accessory"
        if item.sanitary_product_id:
            sanitary_product = self.sanitary_products.get(item.sanitary_product_id)
            if sanitary_product:
                return f"{sanitary_product.company_name} - {sanitary_product.product_category}"
            return "Unknown Sanitary Product"
        return "Unknown Item"

    def item_size(self, item):
        if item.product_id:
            return item.tile_size or "-"
        if item.accessory_id:
            accessory = self.accessories.get(item.accessory_id)
            return accessory.category if accessory else "-"
        if item.sanitary_product_id:
            sanitary_product = self.sanitary_products.get(item.sanitary_product_id)
            return sanitary_product.color if sanitary_product else "-"
        return "-"

