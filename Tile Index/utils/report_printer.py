"""PDF report generation for the Reports screen."""

import os
import re
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


class ReportPrinter:
    """Generate black-on-white PDF reports from structured report data."""

    def __init__(self, report):
        self.report = report

    def generate_pdf(self):
        pdf_path = self.next_report_pdf_path()
        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=landscape(A4),
            rightMargin=10 * mm,
            leftMargin=10 * mm,
            topMargin=10 * mm,
            bottomMargin=10 * mm,
            title=self.report.get("title", "Report"),
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "ReportTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=colors.black,
            alignment=1,
            spaceAfter=4,
        )
        subtitle_style = ParagraphStyle(
            "ReportSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=11,
            textColor=colors.black,
            alignment=1,
        )
        normal = ParagraphStyle(
            "ReportNormal",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7,
            leading=9,
            textColor=colors.black,
        )
        normal_bold = ParagraphStyle("ReportNormalBold", parent=normal, fontName="Helvetica-Bold")

        story = [
            Paragraph("TILE INDEX", title_style),
            Paragraph(self.escape_text(self.report.get("title", "Report")), subtitle_style),
            Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", subtitle_style),
            Spacer(1, 8),
        ]

        summary = self.report.get("summary") or []
        if summary:
            summary_table = Table(
                [[Paragraph(self.escape_text(part), normal) for part in summary]],
                repeatRows=0,
            )
            summary_table.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.35, colors.black),
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.extend([summary_table, Spacer(1, 8)])

        columns = self.report.get("columns") or []
        rows = self.report.get("rows") or []
        table_data = [[Paragraph(f"<b>{self.escape_text(column)}</b>", normal_bold) for column in columns]]
        for row in rows:
            table_data.append([Paragraph(self.escape_text(row.get(column, "")), normal) for column in columns])

        if len(table_data) == 1:
            table_data.append([Paragraph("No rows found", normal)] + ["" for _ in columns[1:]])

        table = Table(table_data, colWidths=self.column_widths(columns), repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.white),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.black),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("LEADING", (0, 0), (-1, -1), 9),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(table)

        doc.build(story)
        return pdf_path

    @staticmethod
    def column_widths(columns):
        width_map = {
            "Invoice No": 24 * mm,
            "Customer": 45 * mm,
            "Time": 20 * mm,
            "Total": 25 * mm,
            "Paid": 25 * mm,
            "Balance": 25 * mm,
            "Branch": 35 * mm,
            "Product": 58 * mm,
            "Size": 20 * mm,
            "Grade": 28 * mm,
            "Boxes": 16 * mm,
            "Loose": 16 * mm,
            "Total Pieces": 24 * mm,
            "Value": 28 * mm,
            "Month": 22 * mm,
            "Invoice Count": 26 * mm,
            "Total Sales": 28 * mm,
            "Total Paid": 28 * mm,
            "Total Balance": 30 * mm,
        }
        return [width_map.get(column, 28 * mm) for column in columns]

    def report_pdf_dir(self):
        base_dir = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        path = os.path.join(base_dir, "TileIndex", "reports")
        os.makedirs(path, exist_ok=True)
        return path

    def next_report_pdf_path(self):
        report_type = self.safe_filename(self.report.get("type", "report")).lower()
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base = f"{report_type}_{stamp}.pdf"
        folder = self.report_pdf_dir()
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
        return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value)).strip("_") or "report"

    @staticmethod
    def escape_text(value):
        return (
            str(value or "")
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
