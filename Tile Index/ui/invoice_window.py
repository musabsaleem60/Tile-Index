"""
Invoice & Billing Window
Create and manage invoices
"""

import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
from datetime import datetime
from urllib.parse import urlencode
from repositories.branch_repository import BranchRepository
from repositories.product_repository import ProductRepository
from repositories.accessory_repository import AccessoryRepository
from repositories.sanitary_repository import SanitaryProductRepository
from services.invoice_service import InvoiceService
from services.inventory_service import InventoryService
from services.accessory_service import AccessoryService
from desktop_client.api_client import ApiClientError
from desktop_client.session import api_client
from utils.validators import validate_positive_number, validate_integer, validate_required
from utils.invoice_printer import InvoicePrintWindow
from utils.grade_constants import VALID_GRADES, GRADE_1
from utils.searchable_combobox import SearchableCombobox
from utils.accessory_labels import accessory_display_label
from utils.invoice_draft_store import DRAFT_SCHEMA_VERSION, InvoiceDraftStore
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
        self.source_branch_options = []
        self.current_stock_overview_row = None
        self.resumed_from_draft = False
        self.draft_store = InvoiceDraftStore(self.current_user.id)
        
        # Filter branches for employees
        from services.auth_service import AuthenticationService
        if AuthenticationService.is_employee(self.current_user) and self.current_user.branch_id is not None:
            # Employee can only see their assigned branch
            self.branches = [b for b in self.branches if b.id == self.current_user.branch_id]
            if self.branches:
                self.selected_branch_id = self.branches[0].id
        
        self.setup_ui()
        
        # Set branch if employee
        if AuthenticationService.is_employee(self.current_user) and self.current_user.branch_id is not None and self.branches:
            self.branch_var.set(self.branches[0].name)

        self.parent.after_idle(self.offer_resume_draft)
    
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
        if AuthenticationService.is_employee(self.current_user) and self.current_user.branch_id is not None:
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

        self.form_label(left_frame, "Remarks:").grid(row=5, column=0, sticky=tk.NW, pady=5, padx=(12, 0))
        self.remarks_text = ctk.CTkTextbox(
            left_frame,
            height=72,
            font=FONTS["small"],
            fg_color=COLORS["app_bg"],
            border_color=COLORS["border"],
            text_color=COLORS["text"],
            border_width=1,
        )
        self.remarks_text.grid(row=5, column=1, pady=5, padx=(5, 12), sticky=tk.EW)
        
        # Add Item section
        item_frame = self.create_subpanel(left_frame, "Add Item")
        item_frame.grid(row=6, column=0, columnspan=2, sticky=tk.EW, pady=10, padx=12)
        
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

        self.source_branch_label = self.form_label(item_frame, "Source Branch:")
        self.source_branch_label.grid(row=4, column=0, sticky=tk.W, pady=3, padx=8)
        self.source_branch_var = tk.StringVar()
        self.source_branch_combo = ttk.Combobox(item_frame, textvariable=self.source_branch_var, width=SIZES["dropdown_width"], state="readonly", font=FONTS["small"])
        self.source_branch_combo.grid(row=4, column=1, pady=3, padx=8, sticky=tk.W)
        self.source_branch_combo.bind('<<ComboboxSelected>>', lambda _event: self.update_stock_info())
        
        self.boxes_label = self.form_label(item_frame, "Boxes:")
        self.boxes_label.grid(row=5, column=0, sticky=tk.W, pady=3, padx=8)
        self.item_boxes_entry = self.form_entry(item_frame, width=160)
        self.item_boxes_entry.grid(row=5, column=1, pady=3, padx=8)
        self.item_boxes_entry.insert(0, "0")
        
        self.pieces_label = self.form_label(item_frame, "Loose Pieces:")
        self.pieces_label.grid(row=6, column=0, sticky=tk.W, pady=3, padx=8)
        self.item_pieces_entry = self.form_entry(item_frame, width=160)
        self.item_pieces_entry.grid(row=6, column=1, pady=3, padx=8)
        self.item_pieces_entry.insert(0, "0")
        
        # Stock info display
        self.stock_info_label = ctk.CTkLabel(
            item_frame,
            text="",
            font=FONTS["stock_summary"],
            text_color=COLORS["primary_hover"],
            wraplength=300,
            height=SIZES["small_label_height"],
        )
        self.stock_info_label.grid(row=7, column=0, columnspan=2, pady=5)
        
        self.action_button(item_frame, "Add to Invoice", self.add_item, width=180).grid(row=8, column=0, columnspan=2, pady=10)
        
        # Totals section
        totals_frame = self.create_subpanel(left_frame, "Totals")
        totals_frame.grid(row=7, column=0, columnspan=2, sticky=tk.EW, pady=10, padx=12)
        
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
        btn_frame.grid(row=8, column=0, columnspan=2, pady=10)
        
        self.action_button(btn_frame, "Generate Invoice", self.generate_invoice, width=140).pack(side=tk.LEFT, padx=4)
        self.action_button(btn_frame, "Save Draft", self.save_draft, width=105, primary=False).pack(side=tk.LEFT, padx=4)
        self.action_button(btn_frame, "Clear All", self.clear_invoice, width=105, primary=False).pack(side=tk.LEFT, padx=4)
        self.action_button(btn_frame, "Print Invoice", self.print_invoice, width=115).pack(side=tk.LEFT, padx=4)
        
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
        columns = ('S.No', 'Product', 'Source', 'Size', 'Grade', 'Boxes', 'Pieces', 'Rate/Box', 'Rate/Piece', 'Total')
        table_frame = ctk.CTkFrame(right_frame, fg_color=COLORS["surface"], corner_radius=SIZES["corner_radius"], border_width=1, border_color=COLORS["border"])
        table_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 8))
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        self.items_tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=20)
        self.items_tree.tag_configure('draft_error', foreground=COLORS["danger"])

        column_widths = {
            'S.No': 55,
            'Product': 190,
            'Source': 135,
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
            self.source_branch_label.grid()
            self.source_branch_combo.grid()
            self.boxes_label.configure(text="Boxes:")
            self.pieces_label.grid()
            self.item_pieces_entry.grid()
        elif item_type == "Accessories":
            self.product_label.configure(text="Accessory:")
            self.product_combo.set_completion_list([self.format_accessory(a) for a in self.accessories])
            self.grade_label.grid_remove()
            self.grade_combo.grid_remove()
            self.source_branch_label.grid()
            self.source_branch_combo.grid()
            self.boxes_label.configure(text="Quantity:")
            self.pieces_label.grid_remove()
            self.item_pieces_entry.grid_remove()
        elif item_type == "Sanitary":
            self.product_label.configure(text="Sanitary Product:")
            self.product_combo.set_completion_list([self.format_sanitary(p) for p in self.sanitary_products])
            self.grade_label.grid_remove()
            self.grade_combo.grid_remove()
            self.source_branch_label.grid()
            self.source_branch_combo.grid()
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
                self.source_branch_var.set(branch.name)
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
                product = None
                for p in self.products:
                    if f"{p.name} - {p.tile_size}" == item_str:
                        product = p
                        break
                
                if not product:
                    self.stock_info_label.configure(text="")
                    return
                
                grade = self.grade_var.get()
                overview_row = self.load_stock_overview_row("tiles", product.id, grade=grade)
                self.current_stock_overview_row = overview_row
                if overview_row:
                    self.update_source_branch_options(overview_row)
                    selected_stock = self.selected_source_stock()
                    branch_lines = [
                        f"{b['branch_name']}: {b.get('boxes', 0)} boxes + {b.get('loose_pieces', 0)} loose"
                        for b in overview_row.get("branches", [])
                    ]
                    if selected_stock:
                        if (
                            selected_stock.get("rate_missing")
                            or selected_stock.get("rate_per_box") is None
                            or selected_stock.get("rate_per_piece") is None
                        ):
                            rate_line = "No rate set for this size and grade"
                        else:
                            rate_line = (
                                f"Selected source rate/box: Rs. {selected_stock.get('rate_per_box'):.2f} | "
                                f"rate/piece: Rs. {selected_stock.get('rate_per_piece'):.2f}"
                            )
                    else:
                        rate_line = "Select a source branch"
                    self.stock_info_label.configure(
                        text="\n".join(branch_lines + [rate_line]),
                        text_color=COLORS["primary"]
                    )
                else:
                    self.update_source_branch_options(None)
                    self.stock_info_label.configure(text="No stock available for this grade", text_color=COLORS["danger"])
            elif item_type == "Accessories":
                accessory = None
                for a in self.accessories:
                    if self.format_accessory(a) == item_str:
                        accessory = a
                        break
                
                if not accessory:
                    self.stock_info_label.configure(text="")
                    return
                
                overview_row = self.load_stock_overview_row("accessories", accessory.id)
                self.current_stock_overview_row = overview_row
                if overview_row:
                    self.update_source_branch_options(overview_row)
                    branch_lines = [
                        f"{b['branch_name']}: {b.get('quantity', 0)} items"
                        for b in overview_row.get("branches", [])
                    ]
                    available = self.selected_source_stock().get("quantity", 0) if self.selected_source_stock() else 0
                else:
                    self.update_source_branch_options(None)
                    branch_lines = []
                    available = 0
                self.stock_info_label.configure(
                    text="\n".join(branch_lines + [f"Selected source: {available} items | Unit Price: Rs. {accessory.unit_price:.2f}"]),
                    text_color=COLORS["primary"]
                )
            elif item_type == "Sanitary":
                product = next(
                    (p for p in self.sanitary_products if self.format_sanitary(p) == item_str),
                    None,
                )
                if not product:
                    self.stock_info_label.configure(text="")
                    return
                overview_row = self.load_stock_overview_row("sanitary", product.id)
                self.current_stock_overview_row = overview_row
                if overview_row:
                    self.update_source_branch_options(overview_row)
                    branch_lines = [
                        f"{b['branch_name']}: {b.get('quantity', 0)} items"
                        for b in overview_row.get("branches", [])
                    ]
                    selected = self.selected_source_stock()
                    available = selected.get("quantity", 0) if selected else 0
                else:
                    self.update_source_branch_options(None)
                    branch_lines = []
                    available = 0
                self.stock_info_label.configure(
                    text="\n".join(branch_lines + [
                        f"Selected source: {available} items | Unit Price: Rs. {product.sale_price:.2f}"
                    ]),
                    text_color=COLORS["primary"],
                )
        except:
            self.stock_info_label.configure(text="")

    def load_stock_overview_row(self, item_type, item_id, grade=None):
        try:
            params = {"item_type": {
                "tiles": "tile",
                "accessories": "accessory",
                "sanitary": "sanitary",
            }[item_type]}
            if item_type == "tiles":
                params["product_id"] = str(item_id)
                params["grade"] = grade
            elif item_type == "accessories":
                params["accessory_id"] = str(item_id)
            else:
                params["sanitary_product_id"] = str(item_id)
            data = api_client.get(f"/stock/item?{urlencode(params)}")
            return data.get("item")
        except ApiClientError:
            return None
        except Exception:
            return None
        return None

    def update_source_branch_options(self, overview_row):
        branches = overview_row.get("branches", []) if overview_row else []
        self.source_branch_options = branches
        names = [branch["branch_name"] for branch in branches]
        self.source_branch_combo["values"] = names
        current = self.source_branch_var.get()
        invoice_branch = self.invoice_branch_name()
        if invoice_branch in names and (not current or current not in names):
            self.source_branch_var.set(invoice_branch)
        elif names and current not in names:
            self.source_branch_var.set(names[0])
        elif not names:
            self.source_branch_var.set("")

    def selected_source_stock(self):
        selected = self.source_branch_var.get()
        for branch in self.source_branch_options:
            if branch.get("branch_name") == selected:
                return branch
        return None

    def selected_source_branch_id(self):
        stock = self.selected_source_stock()
        return stock.get("branch_id") if stock else self.selected_branch_id

    def invoice_branch_name(self):
        for branch in self.branches:
            if branch.id == self.selected_branch_id:
                return branch.name
        return ""

    def confirm_cross_branch_source(self, source_branch_id):
        if not source_branch_id or source_branch_id == self.selected_branch_id:
            return True
        source_name = self.source_branch_var.get()
        return messagebox.askyesno(
            "Confirm Cross-Branch Stock",
            f"This is {source_name} stock. Confirm you have arranged it with that branch?"
        )
    
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
                
                source_branch_id = self.selected_source_branch_id()
                if not self.confirm_cross_branch_source(source_branch_id):
                    return
                source_stock = self.selected_source_stock()
                if not source_stock:
                    raise ValueError(f"No source stock selected for {product.name} - Grade {grade}")
                if (
                    source_stock.get("rate_missing")
                    or source_stock.get("rate_per_box") is None
                    or source_stock.get("rate_per_piece") is None
                ):
                    raise ValueError("No rate set for this size and grade")
                
                total_available_pieces = source_stock.get("total_pieces", 0)
                total_requested_pieces = (boxes * product.pieces_per_box) + loose_pieces
                
                if total_requested_pieces > total_available_pieces:
                    raise ValueError(
                        f"Insufficient stock. Available at {self.source_branch_var.get()}: "
                        f"{source_stock.get('boxes', 0)} boxes + {source_stock.get('loose_pieces', 0)} pieces"
                    )
                
                # Calculate line total
                line_total = (boxes * source_stock["rate_per_box"]) + (loose_pieces * source_stock["rate_per_piece"])
                
                # Add to items list
                item_data = {
                    'type': 'Tiles',
                    'product_id': product.id,
                    'source_branch_id': source_branch_id,
                    'source_branch_name': self.source_branch_var.get(),
                    'product_name': product.name,
                    'tile_size': product.tile_size,
                    'grade': grade,
                    'boxes': boxes,
                    'loose_pieces': loose_pieces,
                    'rate_per_box': source_stock["rate_per_box"],
                    'rate_per_piece': source_stock["rate_per_piece"],
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
                
                source_branch_id = self.selected_source_branch_id()
                if not self.confirm_cross_branch_source(source_branch_id):
                    return
                source_stock = self.selected_source_stock()
                available = source_stock.get("quantity", 0) if source_stock else 0
                if quantity > available:
                    raise ValueError(
                        f"Insufficient stock for accessory {accessory_display_label(accessory)} at "
                        f"{self.source_branch_var.get()}. Available: {available}"
                    )
                
                # Calculate line total
                line_total = quantity * accessory.unit_price
                
                # Add to items list
                item_data = {
                    'type': 'Accessory',
                    'accessory_id': accessory.id,
                    'source_branch_id': source_branch_id,
                    'source_branch_name': self.source_branch_var.get(),
                    'product_name': accessory_display_label(accessory),
                    'tile_size': accessory.category,
                    'grade': '-',
                    'boxes': quantity,
                    'loose_pieces': 0,
                    'rate_per_box': accessory.unit_price,
                    'rate_per_piece': 0,
                    'line_total': line_total
                }
            elif item_type == "Sanitary":
                product = next(
                    (p for p in self.sanitary_products if self.format_sanitary(p) == item_str),
                    None,
                )
                if not product:
                    raise ValueError("Sanitary product not found")
                quantity = validate_integer(self.item_boxes_entry.get() or "0", "Quantity")
                if quantity <= 0:
                    raise ValueError("Please enter a valid quantity")
                source_branch_id = self.selected_source_branch_id()
                if not self.confirm_cross_branch_source(source_branch_id):
                    return
                source_stock = self.selected_source_stock()
                available = source_stock.get("quantity", 0) if source_stock else 0
                if quantity > available:
                    raise ValueError(
                        f"Insufficient stock for sanitary product {self.format_sanitary(product)} at "
                        f"{self.source_branch_var.get()}. Available: {available}"
                    )
                item_data = {
                    'type': 'Sanitary',
                    'sanitary_product_id': product.id,
                    'source_branch_id': source_branch_id,
                    'source_branch_name': self.source_branch_var.get(),
                    'product_name': self.format_sanitary(product),
                    'tile_size': product.color,
                    'grade': product.sku,
                    'boxes': quantity,
                    'loose_pieces': 0,
                    'rate_per_box': product.sale_price,
                    'rate_per_piece': 0,
                    'line_total': quantity * product.sale_price,
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
            product_name = item.get('product_name', item.get('display_label', 'Unavailable item'))
            if item.get('draft_error'):
                product_name = f"{product_name} [DRAFT ERROR: {item['draft_error']}]"
            self.items_tree.insert('', tk.END, values=(
                idx,
                product_name,
                item.get('source_branch_name', self.invoice_branch_name()),
                item.get('tile_size', '-'),
                item.get('grade') or '-',
                item.get('boxes', 0),
                item.get('loose_pieces', 0),
                f"Rs. {float(item.get('rate_per_box') or 0):.2f}",
                f"Rs. {float(item.get('rate_per_piece') or 0):.2f}",
                f"Rs. {float(item.get('line_total') or 0):.2f}"
            ), tags=('draft_error',) if item.get('draft_error') else ())
    
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

    def _draft_item_payload(self, item):
        item_type = item.get('type', '').lower()
        if item_type == 'tiles':
            item_type = 'tile'
        return {
            'item_type': item_type,
            'product_id': item.get('product_id'),
            'accessory_id': item.get('accessory_id'),
            'sanitary_product_id': item.get('sanitary_product_id'),
            'source_branch_id': item.get('source_branch_id'),
            'grade': item.get('grade') if item_type == 'tile' else None,
            'boxes': item.get('boxes', 0) if item_type == 'tile' else 0,
            'loose_pieces': item.get('loose_pieces', 0) if item_type == 'tile' else 0,
            'quantity': item.get('boxes', 0) if item_type != 'tile' else 0,
            'display_label': item.get('product_name', ''),
            'rate_per_box': item.get('rate_per_box'),
            'rate_per_piece': item.get('rate_per_piece'),
            'line_total': item.get('line_total'),
        }

    def _draft_payload(self):
        return {
            'schema_version': DRAFT_SCHEMA_VERSION,
            'saved_at': datetime.now().astimezone().isoformat(timespec='seconds'),
            'user_id': self.current_user.id,
            'branch_id': self.selected_branch_id,
            'customer_name': self.customer_name_entry.get().strip(),
            'customer_contact': self.customer_contact_entry.get().strip(),
            'remarks': self.remarks_text.get("1.0", tk.END).strip(),
            'discount': self.discount_entry.get().strip() or '0',
            'paid_amount': self.paid_entry.get().strip() or '0',
            'items': [self._draft_item_payload(item) for item in self.invoice_items],
        }

    def save_draft(self):
        """Save the current form locally without reserving stock."""
        try:
            if not self.selected_branch_id:
                raise ValueError("Please select a branch before saving the draft")
            if self.draft_store.exists() and not messagebox.askyesno(
                "Replace Invoice Draft",
                "A saved invoice draft already exists for this user on this machine. Replace it?",
            ):
                return
            path = self.draft_store.save(self._draft_payload())
            messagebox.showinfo(
                "Draft Saved",
                f"Invoice draft saved on this machine.\n\n{path}",
            )
        except Exception as exc:
            messagebox.showerror("Draft Save Failed", str(exc))

    def offer_resume_draft(self):
        """Offer to resume or discard this user's saved local draft."""
        if not self.draft_store.exists():
            return
        try:
            draft = self.draft_store.load()
        except Exception as exc:
            if messagebox.askyesno(
                "Invoice Draft Unavailable",
                f"The saved invoice draft cannot be read:\n{exc}\n\nDiscard it?",
            ):
                self.draft_store.delete()
            return

        saved_at = str(draft.get('saved_at') or 'an unknown time').replace('T', ' ')
        decision = self._show_draft_choice(saved_at)
        if decision == 'resume':
            self.resume_draft(draft)
        elif decision == 'discard':
            self.draft_store.delete()

    def _show_draft_choice(self, saved_at):
        """Show explicit Resume and Discard choices for a saved draft."""
        dialog = ctk.CTkToplevel(self.parent)
        dialog.title("Invoice Draft Available")
        dialog.geometry("500x210")
        dialog.resizable(False, False)
        dialog.transient(self.parent.winfo_toplevel())
        dialog.configure(fg_color=COLORS["app_bg"])
        result = {'value': None}

        ctk.CTkLabel(
            dialog,
            text=f"An invoice draft saved at {saved_at} is available.\nResume it?",
            font=FONTS["body_bold"],
            text_color=COLORS["text"],
            wraplength=440,
            justify=tk.CENTER,
        ).pack(fill=tk.X, padx=24, pady=(32, 22))

        buttons = ctk.CTkFrame(dialog, fg_color="transparent")
        buttons.pack(pady=8)

        def choose(value):
            result['value'] = value
            dialog.destroy()

        self.action_button(buttons, "Resume", lambda: choose('resume'), width=130).pack(side=tk.LEFT, padx=8)
        self.action_button(
            buttons, "Discard", lambda: choose('discard'), width=130, primary=False
        ).pack(side=tk.LEFT, padx=8)
        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
        dialog.grab_set()
        dialog.wait_window()
        return result['value']

    def _branch_by_id(self, branch_id):
        return next((branch for branch in self.branches if branch.id == branch_id), None)

    @staticmethod
    def _overview_branch(overview_row, branch_id):
        if not overview_row:
            return None
        return next(
            (branch for branch in overview_row.get('branches', []) if branch.get('branch_id') == branch_id),
            None,
        )

    def _invalid_draft_item(self, saved, reason):
        item_type = str(saved.get('item_type') or '').lower()
        quantity = int(saved.get('quantity') or 0)
        return {
            'type': {'tile': 'Tiles', 'accessory': 'Accessory', 'sanitary': 'Sanitary'}.get(item_type, item_type.title()),
            'product_id': saved.get('product_id'),
            'accessory_id': saved.get('accessory_id'),
            'sanitary_product_id': saved.get('sanitary_product_id'),
            'source_branch_id': saved.get('source_branch_id'),
            'source_branch_name': saved.get('source_branch_name', 'Unavailable branch'),
            'product_name': saved.get('display_label') or 'Unavailable item',
            'tile_size': saved.get('tile_size', '-'),
            'grade': saved.get('grade') or '-',
            'boxes': int(saved.get('boxes') or 0) if item_type == 'tile' else quantity,
            'loose_pieces': int(saved.get('loose_pieces') or 0) if item_type == 'tile' else 0,
            'rate_per_box': float(saved.get('rate_per_box') or 0),
            'rate_per_piece': float(saved.get('rate_per_piece') or 0),
            'line_total': float(saved.get('line_total') or 0),
            'draft_error': reason,
        }

    def _rebuild_draft_item(self, saved):
        """Rebuild one saved line from current catalogue, stock, and pricing."""
        item_type = str(saved.get('item_type') or '').lower()
        source_branch_id = saved.get('source_branch_id')
        source_branch = self._branch_by_id(source_branch_id)
        if not source_branch:
            return self._invalid_draft_item(saved, "Source branch is no longer available")

        if item_type == 'tile':
            product = next((p for p in self.products if p.id == saved.get('product_id')), None)
            if not product:
                return self._invalid_draft_item(saved, "Product was deleted or is unavailable")
            grade = saved.get('grade')
            overview = self.load_stock_overview_row('tiles', product.id, grade)
            stock = self._overview_branch(overview, source_branch_id)
            if not stock:
                return self._invalid_draft_item(saved, "Saved source branch is no longer valid for this product")
            if stock.get('rate_missing') or stock.get('rate_per_box') is None or stock.get('rate_per_piece') is None:
                return self._invalid_draft_item(saved, "No rate set for this size and grade")
            boxes = int(saved.get('boxes') or 0)
            loose = int(saved.get('loose_pieces') or 0)
            requested = boxes * int(product.pieces_per_box) + loose
            if requested > int(stock.get('total_pieces') or 0):
                return self._invalid_draft_item(
                    saved,
                    f"Insufficient stock at {source_branch.name}: requested {requested} pieces, "
                    f"available {int(stock.get('total_pieces') or 0)}",
                )
            rate_box = float(stock['rate_per_box'])
            rate_piece = float(stock['rate_per_piece'])
            return {
                'type': 'Tiles', 'product_id': product.id,
                'source_branch_id': source_branch_id, 'source_branch_name': source_branch.name,
                'product_name': product.name, 'tile_size': product.tile_size, 'grade': grade,
                'boxes': boxes, 'loose_pieces': loose, 'rate_per_box': rate_box,
                'rate_per_piece': rate_piece, 'line_total': boxes * rate_box + loose * rate_piece,
                '_draft_requested_units': requested,
                '_draft_available_units': int(stock.get('total_pieces') or 0),
            }

        if item_type == 'accessory':
            product = next((a for a in self.accessories if a.id == saved.get('accessory_id')), None)
            if not product:
                return self._invalid_draft_item(saved, "Accessory was deleted or is unavailable")
            overview = self.load_stock_overview_row('accessories', product.id)
            stock = self._overview_branch(overview, source_branch_id)
            quantity = int(saved.get('quantity') or 0)
            if not stock:
                return self._invalid_draft_item(saved, "Saved source branch is no longer valid for this accessory")
            if quantity > int(stock.get('quantity') or 0):
                return self._invalid_draft_item(
                    saved,
                    f"Insufficient stock at {source_branch.name}: requested {quantity}, "
                    f"available {int(stock.get('quantity') or 0)}",
                )
            rate = float(product.unit_price)
            return {
                'type': 'Accessory', 'accessory_id': product.id,
                'source_branch_id': source_branch_id, 'source_branch_name': source_branch.name,
                'product_name': accessory_display_label(product), 'tile_size': product.category,
                'grade': '-', 'boxes': quantity, 'loose_pieces': 0,
                'rate_per_box': rate, 'rate_per_piece': 0, 'line_total': quantity * rate,
                '_draft_requested_units': quantity,
                '_draft_available_units': int(stock.get('quantity') or 0),
            }

        if item_type == 'sanitary':
            product = next((p for p in self.sanitary_products if p.id == saved.get('sanitary_product_id')), None)
            if not product:
                return self._invalid_draft_item(saved, "Sanitary product was deleted or is unavailable")
            overview = self.load_stock_overview_row('sanitary', product.id)
            stock = self._overview_branch(overview, source_branch_id)
            quantity = int(saved.get('quantity') or 0)
            if not stock:
                return self._invalid_draft_item(saved, "Saved source branch is no longer valid for this sanitary product")
            if quantity > int(stock.get('quantity') or 0):
                return self._invalid_draft_item(
                    saved,
                    f"Insufficient stock at {source_branch.name}: requested {quantity}, "
                    f"available {int(stock.get('quantity') or 0)}",
                )
            rate = float(product.sale_price)
            return {
                'type': 'Sanitary', 'sanitary_product_id': product.id,
                'source_branch_id': source_branch_id, 'source_branch_name': source_branch.name,
                'product_name': self.format_sanitary(product), 'tile_size': product.color,
                'grade': product.sku, 'boxes': quantity, 'loose_pieces': 0,
                'rate_per_box': rate, 'rate_per_piece': 0, 'line_total': quantity * rate,
                '_draft_requested_units': quantity,
                '_draft_available_units': int(stock.get('quantity') or 0),
            }

        return self._invalid_draft_item(saved, "Unknown item type")

    @staticmethod
    def _flag_combined_draft_shortages(items):
        """Catch repeated lines that individually fit but exceed stock together."""
        running = {}
        for item in items:
            if item.get('draft_error'):
                continue
            item_type = item.get('type')
            item_id = item.get('product_id') or item.get('accessory_id') or item.get('sanitary_product_id')
            key = (item_type, item_id, item.get('source_branch_id'), item.get('grade'))
            running[key] = running.get(key, 0) + int(item.get('_draft_requested_units') or 0)
            available = int(item.get('_draft_available_units') or 0)
            if running[key] > available:
                item['draft_error'] = (
                    f"Combined draft quantity exceeds current stock at {item.get('source_branch_name')}: "
                    f"requested {running[key]}, available {available}"
                )
        return items

    def refresh_resumed_draft_lines(self, show_result=False):
        saved_items = [self._draft_item_payload(item) for item in self.invoice_items]
        self.invoice_items = self._flag_combined_draft_shortages(
            [self._rebuild_draft_item(item) for item in saved_items]
        )
        self.update_items_table()
        self.update_totals()
        errors = [item['draft_error'] for item in self.invoice_items if item.get('draft_error')]
        if show_result and errors:
            messagebox.showwarning(
                "Draft Needs Attention",
                "Some draft lines cannot be submitted with current data:\n\n- " + "\n- ".join(errors) +
                "\n\nRemove and add those lines again, or correct the stock/rate and retry.",
            )
        return errors

    def resume_draft(self, draft):
        try:
            branch = self._branch_by_id(draft.get('branch_id'))
            if not branch:
                raise ValueError("The draft branch is unavailable or is not accessible to this user")

            self.clear_invoice(prompt_for_saved_draft=False)
            self.branch_var.set(branch.name)
            self.on_branch_select(None)
            self.customer_name_entry.insert(0, draft.get('customer_name') or '')
            self.customer_contact_entry.insert(0, draft.get('customer_contact') or '')
            self.remarks_text.insert('1.0', draft.get('remarks') or '')
            self.discount_entry.delete(0, tk.END)
            self.discount_entry.insert(0, str(draft.get('discount') or '0'))
            self.paid_entry.delete(0, tk.END)
            self.paid_entry.insert(0, str(draft.get('paid_amount') or '0'))
            self.invoice_items = self._flag_combined_draft_shortages(
                [self._rebuild_draft_item(item) for item in draft.get('items', [])]
            )
            self.resumed_from_draft = True
            self.update_items_table()
            self.update_totals()
            errors = [item['draft_error'] for item in self.invoice_items if item.get('draft_error')]
            if errors:
                messagebox.showwarning(
                    "Draft Resumed With Changes Required",
                    "The draft was restored using current prices and stock. These lines need attention:\n\n- " +
                    "\n- ".join(errors) +
                    "\n\nThey must be fixed or removed before the invoice can be generated.",
                )
            else:
                messagebox.showinfo("Draft Resumed", "The draft was restored using current prices and stock.")
        except Exception as exc:
            messagebox.showerror("Draft Resume Failed", str(exc))
    
    def generate_invoice(self):
        """Generate and save invoice"""
        try:
            if self.resumed_from_draft:
                draft_errors = self.refresh_resumed_draft_lines(show_result=True)
                if draft_errors:
                    raise ValueError("Resolve or remove all flagged draft lines before generating the invoice")
            if not self.selected_branch_id:
                raise ValueError("Please select a branch")
            
            customer_name = validate_required(self.customer_name_entry.get(), "Customer Name")
            customer_contact = self.customer_contact_entry.get().strip() or None
            remarks = self.remarks_text.get("1.0", tk.END).strip() or None
            
            if len(self.invoice_items) == 0:
                raise ValueError("Please add at least one item to the invoice")
            
            discount = float(self.discount_entry.get() or "0")
            paid_amount = float(self.paid_entry.get() or "0")
            subtotal = sum(item['line_total'] for item in self.invoice_items)
            grand_total = subtotal - discount
            if paid_amount > grand_total:
                raise ValueError("Paid amount exceeds invoice total")
            
            # Prepare items data
            items_data = []
            for item in self.invoice_items:
                if item.get('type') == 'Tiles':
                    items_data.append({
                        'product_id': item['product_id'],
                        'source_branch_id': item.get('source_branch_id'),
                        'grade': item['grade'],
                        'boxes': item['boxes'],
                        'loose_pieces': item['loose_pieces']
                    })
                elif item.get('type') == 'Accessory':
                    items_data.append({
                        'accessory_id': item['accessory_id'],
                        'source_branch_id': item.get('source_branch_id'),
                        'quantity': item['boxes']  # boxes field used for quantity in accessories
                    })
                elif item.get('type') == 'Sanitary':
                    items_data.append({
                        'sanitary_product_id': item['sanitary_product_id'],
                        'source_branch_id': item.get('source_branch_id'),
                        'quantity': item['boxes'],
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
                user_id=self.current_user.id,
                remarks=remarks,
            )
            
            messagebox.showinfo("Success", f"Invoice generated successfully!\nInvoice Number: {invoice.invoice_number}")
            
            # Open invoice print window
            print_window = tk.Toplevel(self.parent)
            InvoicePrintWindow(print_window, invoice_id=invoice.id)

            self.draft_store.delete()
            self.clear_invoice(prompt_for_saved_draft=False)
            
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def clear_invoice(self, prompt_for_saved_draft=True):
        """Clear invoice form"""
        if prompt_for_saved_draft and self.draft_store.exists():
            if messagebox.askyesno(
                "Discard Saved Draft",
                "Clear the current form and also discard this user's saved invoice draft?\n\n"
                "Choose No to keep the saved draft for later.",
            ):
                self.draft_store.delete()
        self.customer_name_entry.delete(0, tk.END)
        self.customer_contact_entry.delete(0, tk.END)
        self.remarks_text.delete("1.0", tk.END)
        self.item_type_var.set("Tiles")
        self.on_item_type_change(None)
        self.product_var.set("")
        self.discount_entry.delete(0, tk.END)
        self.discount_entry.insert(0, "0")
        self.paid_entry.delete(0, tk.END)
        self.paid_entry.insert(0, "0")
        self.invoice_items = []
        self.resumed_from_draft = False
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
    def format_sanitary(product):
        return " - ".join(part for part in (
            product.company_name,
            product.product_category,
            product.color,
        ) if part)


