import os
import re
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from repositories.branch_repository import BranchRepository


class ReturnPrinter:
    def __init__(self, invoice, return_record):
        self.invoice = invoice
        self.record = return_record

    def generate_pdf(self):
        root = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "TileIndex", "returns")
        os.makedirs(root, exist_ok=True)
        number = re.sub(r"[^A-Za-z0-9_-]", "_", self.record["return_number"])
        base = os.path.join(root, f"return_{number}.pdf")
        path = base
        counter = 2
        while os.path.exists(path):
            path = os.path.join(root, f"return_{number}_{counter}.pdf")
            counter += 1

        doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=12 * mm, bottomMargin=12 * mm)
        styles = getSampleStyleSheet()
        title = ParagraphStyle("ReturnTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=18, textColor=colors.black, alignment=1)
        normal = ParagraphStyle("ReturnNormal", parent=styles["Normal"], fontName="Helvetica", fontSize=9, leading=12, textColor=colors.black)
        story = [
            Paragraph("TILE INDEX", title),
            Paragraph("RETURN / EXCHANGE NOTE", title),
            Spacer(1, 8),
            Paragraph(f"<b>Return:</b> {self.record['return_number']} &nbsp;&nbsp; <b>Original invoice:</b> {self.invoice.invoice_number}", normal),
            Paragraph(f"<b>Customer:</b> {self.invoice.customer_name} &nbsp;&nbsp; <b>Date:</b> {self.record.get('return_date', '')}", normal),
            Paragraph(f"<b>Reason:</b> {self.record.get('reason', '')}", normal),
            Spacer(1, 10),
        ]
        originals = {item.id: item for item in self.invoice.items}
        branches = {branch.id: branch.name for branch in BranchRepository.get_all()}
        returned_rows = [["Returned item", "Quantity", "Source branch", "Discounted value"]]
        for row in self.record.get("return_items", []):
            item = originals.get(row["invoice_item_id"])
            description = getattr(item, "description", None) or f"Invoice item {row['invoice_item_id']}"
            qty = f"{row['boxes']} boxes + {row['loose_pieces']} loose" if row["item_type"] == "tile" else f"{row['quantity']} units"
            returned_rows.append([description, qty, branches.get(row["source_branch_id"], str(row["source_branch_id"])), f"Rs. {float(row['discounted_line_total']):.2f}"])
        story.extend([Paragraph("<b>Returned Items</b>", normal), self._table(returned_rows), Spacer(1, 10)])

        exchanges = self.record.get("exchange_items", [])
        if exchanges:
            exchange_rows = [["Exchange item", "Quantity", "Source branch", "Value"]]
            for row in exchanges:
                qty = f"{row['boxes']} boxes + {row['loose_pieces']} loose" if row["item_type"] == "tile" else f"{row['quantity']} units"
                exchange_rows.append([row["description"], qty, branches.get(row["source_branch_id"], str(row["source_branch_id"])), f"Rs. {float(row['line_total']):.2f}"])
            story.extend([Paragraph("<b>Exchange Items</b>", normal), self._table(exchange_rows), Spacer(1, 10)])

        difference = float(self.record["difference_amount"])
        direction = "Refund owed to customer" if difference > 0 else "Additional payment owed by customer" if difference < 0 else "Even exchange"
        story.extend([
            Paragraph(f"Returned value: Rs. {float(self.record['returned_value']):.2f}", normal),
            Paragraph(f"Exchange value: Rs. {float(self.record['exchange_value']):.2f}", normal),
            Paragraph(f"<b>{direction}: Rs. {abs(difference):.2f}</b>", normal),
            Paragraph(f"Settled: Rs. {float(self.record.get('settled_amount', 0)):.2f} &nbsp;&nbsp; Outstanding: Rs. {float(self.record.get('outstanding_amount', 0)):.2f}", normal),
            Spacer(1, 18),
            Paragraph("Customer signature: ____________________ &nbsp;&nbsp;&nbsp; Authorized by: ____________________", normal),
        ])
        doc.build(story)
        return path

    @staticmethod
    def _table(rows):
        table = Table(rows, repeatRows=1, colWidths=[82 * mm, 34 * mm, 32 * mm, 35 * mm])
        table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        return table

    @staticmethod
    def open_pdf(path):
        os.startfile(path)
