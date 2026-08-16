"""Read-only all-branch stock overview."""

import tkinter as tk
from tkinter import ttk, messagebox
from urllib.parse import urlencode

import customtkinter as ctk

from desktop_client.api_client import ApiClientError
from desktop_client.session import api_client
from ui.theme import COLORS, FONTS, SIZES, SPACING


class StockOverviewWindow:
    """Fast read-only stock search across branches."""

    GRADES = ["All", "G1 Prime", "G2 Standard", "G3 Regular"]

    def __init__(self, parent, current_user):
        self.parent = parent
        self.current_user = current_user
        self.active_tab = "tiles"
        self.search_after_id = None
        self.branches = []
        self.tiles = []
        self.accessories = []
        self.rows_by_iid = {}

        self.setup_ui()
        self.refresh_data()

    def setup_ui(self):
        header = ctk.CTkLabel(
            self.parent,
            text="Complete Stock Overview",
            font=FONTS["section"],
            fg_color=COLORS["surface"],
            text_color=COLORS["text"],
            height=48,
        )
        header.pack(fill=tk.X)

        main = ctk.CTkFrame(self.parent, fg_color=COLORS["app_bg"], corner_radius=0)
        main.pack(fill=tk.BOTH, expand=True, padx=SPACING["page_x"], pady=SPACING["page_y"])

        controls = ctk.CTkFrame(
            main,
            fg_color=COLORS["surface"],
            corner_radius=SIZES["corner_radius"],
            border_width=1,
            border_color=COLORS["border"],
        )
        controls.pack(fill=tk.X, pady=(0, 12))

        self.tab_control = ctk.CTkSegmentedButton(
            controls,
            values=["Tiles", "Accessories"],
            command=self.on_tab_change,
            selected_color=COLORS["primary"],
            selected_hover_color=COLORS["primary_hover"],
            unselected_color=COLORS["card"],
            unselected_hover_color=COLORS["card_hover"],
            text_color=COLORS["text"],
            font=FONTS["small_bold"],
            height=34,
        )
        self.tab_control.set("Tiles")
        self.tab_control.grid(row=0, column=0, padx=12, pady=12, sticky=tk.W)

        ctk.CTkLabel(
            controls,
            text="Search",
            font=FONTS["small_bold"],
            text_color=COLORS["text_muted"],
        ).grid(row=0, column=1, padx=(12, 6), pady=12, sticky=tk.W)
        self.search_var = tk.StringVar()
        self.search_entry = ctk.CTkEntry(
            controls,
            textvariable=self.search_var,
            width=300,
            height=SIZES["input_height"],
            fg_color=COLORS["card"],
            border_color=COLORS["border"],
            text_color=COLORS["text"],
            font=FONTS["small"],
        )
        self.search_entry.grid(row=0, column=2, padx=(0, 12), pady=12, sticky=tk.W)
        self.search_var.trace_add("write", self.on_search_change)

        ctk.CTkLabel(
            controls,
            text="Branch",
            font=FONTS["small_bold"],
            text_color=COLORS["text_muted"],
        ).grid(row=0, column=3, padx=(6, 6), pady=12, sticky=tk.W)
        self.branch_var = tk.StringVar(value="All")
        self.branch_combo = ttk.Combobox(controls, textvariable=self.branch_var, width=26, state="readonly", font=FONTS["small"])
        self.branch_combo["values"] = ["All"]
        self.branch_combo.grid(row=0, column=4, padx=(0, 12), pady=12, sticky=tk.W)
        self.branch_combo.bind("<<ComboboxSelected>>", lambda _e: self.refresh_data())

        ctk.CTkLabel(
            controls,
            text="Grade",
            font=FONTS["small_bold"],
            text_color=COLORS["text_muted"],
        ).grid(row=0, column=5, padx=(6, 6), pady=12, sticky=tk.W)
        self.grade_var = tk.StringVar(value="All")
        self.grade_combo = ttk.Combobox(controls, textvariable=self.grade_var, width=18, state="readonly", font=FONTS["small"])
        self.grade_combo["values"] = self.GRADES
        self.grade_combo.grid(row=0, column=6, padx=(0, 12), pady=12, sticky=tk.W)
        self.grade_combo.bind("<<ComboboxSelected>>", lambda _e: self.refresh_data())

        ctk.CTkLabel(
            controls,
            text="Category",
            font=FONTS["small_bold"],
            text_color=COLORS["text_muted"],
        ).grid(row=0, column=7, padx=(6, 6), pady=12, sticky=tk.W)
        self.category_var = tk.StringVar(value="All")
        self.category_combo = ttk.Combobox(controls, textvariable=self.category_var, width=18, state="readonly", font=FONTS["small"])
        self.category_combo["values"] = ["All", "Grout", "Bond", "Spacer", "Floor Waste"]
        self.category_combo.grid(row=0, column=8, padx=(0, 12), pady=12, sticky=tk.W)
        self.category_combo.bind("<<ComboboxSelected>>", lambda _e: self.refresh_data())

        self.show_all_var = tk.BooleanVar(value=False)
        self.show_all_check = ctk.CTkCheckBox(
            controls,
            text="Show all",
            variable=self.show_all_var,
            command=self.refresh_data,
            font=FONTS["small_bold"],
            text_color=COLORS["text"],
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            border_color=COLORS["border"],
        )
        self.show_all_check.grid(row=0, column=9, padx=(0, 12), pady=12, sticky=tk.W)
        controls.grid_columnconfigure(10, weight=1)

        body = ctk.CTkFrame(main, fg_color="transparent", corner_radius=0)
        body.pack(fill=tk.BOTH, expand=True)
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        table_panel = self.panel(body)
        table_panel.grid(row=0, column=0, sticky=tk.NSEW, padx=(0, 10))
        table_panel.grid_rowconfigure(1, weight=1)
        table_panel.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            table_panel,
            text="Loading stock...",
            font=FONTS["small"],
            text_color=COLORS["text_muted"],
            anchor=tk.W,
            height=SIZES["small_label_height"],
        )
        self.status_label.grid(row=0, column=0, sticky=tk.EW, padx=12, pady=(10, 4))

        self.tree = ttk.Treeview(table_panel, show="headings", height=18)
        self.tree.grid(row=1, column=0, sticky=tk.NSEW, padx=(12, 0), pady=(0, 12))
        scroll = ttk.Scrollbar(table_panel, orient=tk.VERTICAL, command=self.tree.yview)
        scroll.grid(row=1, column=1, sticky=tk.NS, padx=(0, 12), pady=(0, 12))
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.bind("<<TreeviewSelect>>", self.on_row_select)

        self.breakdown_panel = self.panel(body)
        self.breakdown_panel.grid(row=0, column=1, sticky=tk.NSEW)
        self.breakdown_panel.grid_rowconfigure(2, weight=1)
        self.breakdown_panel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.breakdown_panel,
            text="Branch Breakdown",
            font=FONTS["body_bold"],
            text_color=COLORS["text"],
            height=34,
        ).grid(row=0, column=0, sticky=tk.W, padx=12, pady=(10, 2))
        self.breakdown_title = ctk.CTkLabel(
            self.breakdown_panel,
            text="Select a row",
            font=FONTS["small"],
            text_color=COLORS["text_muted"],
            wraplength=320,
            justify=tk.LEFT,
            anchor=tk.W,
            height=48,
        )
        self.breakdown_title.grid(row=1, column=0, sticky=tk.EW, padx=12, pady=(0, 8))

        self.breakdown_tree = ttk.Treeview(self.breakdown_panel, show="headings", height=12)
        self.breakdown_tree.grid(row=2, column=0, sticky=tk.NSEW, padx=(12, 0), pady=(0, 12))
        breakdown_scroll = ttk.Scrollbar(self.breakdown_panel, orient=tk.VERTICAL, command=self.breakdown_tree.yview)
        breakdown_scroll.grid(row=2, column=1, sticky=tk.NS, padx=(0, 12), pady=(0, 12))
        self.breakdown_tree.configure(yscrollcommand=breakdown_scroll.set)

        self.configure_for_tab()

    def panel(self, parent):
        return ctk.CTkFrame(
            parent,
            fg_color=COLORS["surface"],
            corner_radius=SIZES["corner_radius"],
            border_width=1,
            border_color=COLORS["border"],
        )

    def on_tab_change(self, value):
        self.active_tab = "tiles" if value == "Tiles" else "accessories"
        self.configure_for_tab()
        self.populate_table()

    def configure_for_tab(self):
        if self.active_tab == "tiles":
            self.grade_combo.configure(state="readonly")
            self.category_combo.configure(state="disabled")
            columns = ("product", "size", "grade", "total_boxes", "total_loose", "total_pieces")
            headings = {
                "product": "Product",
                "size": "Size",
                "grade": "Grade",
                "total_boxes": "Total Boxes",
                "total_loose": "Total Loose",
                "total_pieces": "Total Pieces",
            }
            widths = {
                "product": 420,
                "size": 80,
                "grade": 110,
                "total_boxes": 95,
                "total_loose": 95,
                "total_pieces": 100,
            }
            breakdown_columns = ("branch", "boxes", "loose", "pieces")
            breakdown_headings = {"branch": "Branch", "boxes": "Boxes", "loose": "Loose", "pieces": "Pieces"}
            breakdown_widths = {"branch": 190, "boxes": 65, "loose": 65, "pieces": 70}
        else:
            self.grade_combo.configure(state="disabled")
            self.category_combo.configure(state="readonly")
            columns = ("product", "category", "total_quantity")
            headings = {
                "product": "Accessory",
                "category": "Category",
                "total_quantity": "Total Qty",
            }
            widths = {
                "product": 520,
                "category": 140,
                "total_quantity": 110,
            }
            breakdown_columns = ("branch", "quantity")
            breakdown_headings = {"branch": "Branch", "quantity": "Quantity"}
            breakdown_widths = {"branch": 230, "quantity": 90}

        self.configure_tree(self.tree, columns, headings, widths)
        self.configure_tree(self.breakdown_tree, breakdown_columns, breakdown_headings, breakdown_widths)
        self.clear_breakdown()

    def configure_tree(self, tree, columns, headings, widths):
        tree["columns"] = columns
        for column in columns:
            tree.heading(column, text=headings[column])
            anchor = tk.W if column in ("product", "branch", "category", "grade", "size") else tk.E
            tree.column(column, width=widths[column], minwidth=60, anchor=anchor, stretch=column in ("product", "branch"))

    def on_search_change(self, *_args):
        if self.search_after_id:
            self.parent.after_cancel(self.search_after_id)
        self.search_after_id = self.parent.after(220, self.refresh_data)

    def refresh_data(self):
        try:
            params = {
                "item_type": self.active_tab,
                "include_zero": str(bool(self.show_all_var.get())).lower(),
            }
            search = self.search_var.get().strip()
            if search:
                params["q"] = search
            branch_id = self.selected_branch_id()
            if branch_id:
                params["branch_id"] = str(branch_id)
            if self.active_tab == "tiles" and self.grade_var.get() != "All":
                params["grade"] = self.grade_var.get()
            if self.active_tab == "accessories" and self.category_var.get() != "All":
                params["category"] = self.category_var.get()

            data = api_client.get(f"/stock/overview?{urlencode(params)}")
            self.branches = data.get("branches", [])
            self.tiles = data.get("tiles", [])
            self.accessories = data.get("accessories", [])
            self.update_branch_filter()
            self.populate_table()
        except ApiClientError as exc:
            messagebox.showerror("Stock Overview", f"Failed to load stock overview: {exc}")
        except Exception as exc:
            messagebox.showerror("Stock Overview", f"Failed to load stock overview: {exc}")

    def update_branch_filter(self):
        current = self.branch_var.get()
        values = ["All"] + [branch["name"] for branch in self.branches]
        self.branch_combo["values"] = values
        if current not in values:
            self.branch_var.set("All")

    def selected_branch_id(self):
        branch_name = self.branch_var.get()
        for branch in self.branches:
            if branch["name"] == branch_name:
                return branch["id"]
        return None

    def populate_table(self):
        self.rows_by_iid.clear()
        for item in self.tree.get_children():
            self.tree.delete(item)

        rows = self.tiles if self.active_tab == "tiles" else self.accessories
        for index, row in enumerate(rows):
            iid = str(index)
            self.rows_by_iid[iid] = row
            if self.active_tab == "tiles":
                values = (
                    row.get("product", ""),
                    row.get("size", ""),
                    row.get("grade", ""),
                    self.format_int(row.get("total_boxes")),
                    self.format_int(row.get("total_loose_pieces")),
                    self.format_int(row.get("total_pieces")),
                )
            else:
                values = (
                    row.get("product", ""),
                    row.get("category", ""),
                    self.format_int(row.get("total_quantity")),
                )
            self.tree.insert("", tk.END, iid=iid, values=values)

        noun = "tile rows" if self.active_tab == "tiles" else "accessory rows"
        if rows:
            self.status_label.configure(text=f"{len(rows)} {noun} found")
        elif self.show_all_var.get():
            self.status_label.configure(text="No catalogue rows found for this search.")
        else:
            self.status_label.configure(text="No stock found - try Show all.")
        self.clear_breakdown()

    def on_row_select(self, _event=None):
        selection = self.tree.selection()
        if not selection:
            self.clear_breakdown()
            return
        row = self.rows_by_iid.get(selection[0])
        if not row:
            self.clear_breakdown()
            return

        self.breakdown_title.configure(text=row.get("product", "Selected item"))
        for item in self.breakdown_tree.get_children():
            self.breakdown_tree.delete(item)

        for branch_row in row.get("branches", []):
            if self.active_tab == "tiles":
                values = (
                    branch_row.get("branch_name", ""),
                    self.format_int(branch_row.get("boxes")),
                    self.format_int(branch_row.get("loose_pieces")),
                    self.format_int(branch_row.get("total_pieces")),
                )
            else:
                values = (
                    branch_row.get("branch_name", ""),
                    self.format_int(branch_row.get("quantity")),
                )
            self.breakdown_tree.insert("", tk.END, values=values)

    def clear_breakdown(self):
        self.breakdown_title.configure(text="Select a row")
        for item in self.breakdown_tree.get_children():
            self.breakdown_tree.delete(item)

    @staticmethod
    def format_int(value):
        try:
            return f"{int(value or 0):,}"
        except (TypeError, ValueError):
            return "0"
