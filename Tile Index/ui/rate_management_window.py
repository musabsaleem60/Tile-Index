"""Admin rate-card and product override management."""

import tkinter as tk
from tkinter import ttk, messagebox
from urllib.parse import urlencode

import customtkinter as ctk

from desktop_client.api_client import ApiClientError
from desktop_client.session import api_client
from repositories.product_repository import ProductRepository
from ui.theme import COLORS, FONTS, SIZES, SPACING
from utils.grade_constants import VALID_GRADES
from utils.searchable_combobox import SearchableCombobox


class RateManagementWindow:
    """Manage tile size rates and product-specific rate overrides."""

    def __init__(self, parent, current_user=None):
        self.parent = parent
        self.current_user = current_user
        self.rate_rows = []
        self.overrides = []
        self.products = []
        self.product_by_label = {}
        self.override_by_iid = {}

        self.setup_ui()
        self.load_products()
        self.refresh_rates()
        self.refresh_overrides()

    def setup_ui(self):
        header = ctk.CTkLabel(
            self.parent,
            text="Rate Management",
            font=FONTS["section"],
            fg_color=COLORS["surface"],
            text_color=COLORS["text"],
            height=48,
        )
        header.pack(fill=tk.X)

        main = ctk.CTkFrame(self.parent, fg_color=COLORS["app_bg"], corner_radius=0)
        main.pack(fill=tk.BOTH, expand=True, padx=SPACING["page_x"], pady=SPACING["page_y"])

        self.tabs = ctk.CTkTabview(
            main,
            fg_color=COLORS["surface"],
            segmented_button_fg_color=COLORS["card"],
            segmented_button_selected_color=COLORS["primary"],
            segmented_button_selected_hover_color=COLORS["primary_hover"],
            segmented_button_unselected_color=COLORS["card"],
            segmented_button_unselected_hover_color=COLORS["card_hover"],
            text_color=COLORS["text"],
            corner_radius=SIZES["corner_radius"],
            border_width=1,
            border_color=COLORS["border"],
        )
        self.tabs.pack(fill=tk.BOTH, expand=True)
        self.card_tab = self.tabs.add("Rate Card")
        self.override_tab = self.tabs.add("Product Overrides")

        self.setup_card_tab()
        self.setup_override_tab()

    def setup_card_tab(self):
        top = ctk.CTkFrame(self.card_tab, fg_color="transparent", corner_radius=0)
        top.pack(fill=tk.X, padx=12, pady=(12, 8))

        ctk.CTkLabel(
            top,
            text="Tile Rate Card",
            font=FONTS["body_bold"],
            text_color=COLORS["text"],
            height=SIZES["small_label_height"],
        ).pack(side=tk.LEFT)
        self.action_button(top, "Refresh", self.refresh_rates, width=110, primary=False).pack(side=tk.RIGHT, padx=(8, 0))
        self.action_button(top, "Add New Size", self.open_add_size_dialog, width=140).pack(side=tk.RIGHT, padx=(8, 0))
        self.action_button(top, "Edit Selected Rate", self.open_edit_rate_dialog, width=160).pack(side=tk.RIGHT)

        table_panel = self.panel(self.card_tab)
        table_panel.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))
        table_panel.grid_rowconfigure(0, weight=1)
        table_panel.grid_columnconfigure(0, weight=1)

        columns = ("size", "pieces", "area", "g1", "g2", "g3")
        self.rate_tree = ttk.Treeview(table_panel, columns=columns, show="headings", height=18)
        headings = {
            "size": "Tile Size",
            "pieces": "Pieces/Box",
            "area": "Area/Box",
            "g1": "G1 Prime",
            "g2": "G2 Standard",
            "g3": "G3 Regular",
        }
        widths = {"size": 130, "pieces": 100, "area": 100, "g1": 130, "g2": 130, "g3": 130}
        for column in columns:
            self.rate_tree.heading(column, text=headings[column])
            self.rate_tree.column(column, width=widths[column], anchor=tk.CENTER)
        self.rate_tree.grid(row=0, column=0, sticky=tk.NSEW, padx=(12, 0), pady=12)
        scroll = ttk.Scrollbar(table_panel, orient=tk.VERTICAL, command=self.rate_tree.yview)
        scroll.grid(row=0, column=1, sticky=tk.NS, padx=(0, 12), pady=12)
        self.rate_tree.configure(yscrollcommand=scroll.set)

    def setup_override_tab(self):
        form = self.panel(self.override_tab)
        form.pack(fill=tk.X, padx=12, pady=(12, 8))

        self.form_label(form, "Product:").grid(row=0, column=0, sticky=tk.W, padx=(12, 8), pady=8)
        self.override_product_var = tk.StringVar()
        self.override_product_combo = SearchableCombobox(
            form,
            textvariable=self.override_product_var,
            width=52,
            state="normal",
            font=FONTS["small"],
        )
        self.override_product_combo.grid(row=0, column=1, columnspan=3, sticky=tk.W, padx=(0, 12), pady=8)

        self.form_label(form, "Grade:").grid(row=1, column=0, sticky=tk.W, padx=(12, 8), pady=8)
        self.override_grade_var = tk.StringVar(value=VALID_GRADES[0])
        grade_combo = ttk.Combobox(
            form,
            textvariable=self.override_grade_var,
            values=VALID_GRADES,
            width=SIZES["compact_dropdown_width"],
            state="readonly",
            font=FONTS["small"],
        )
        grade_combo.grid(row=1, column=1, sticky=tk.W, padx=(0, 12), pady=8)

        self.form_label(form, "Rate/m2:").grid(row=1, column=2, sticky=tk.W, padx=(8, 8), pady=8)
        self.override_rate_entry = self.form_entry(form, width=150)
        self.override_rate_entry.grid(row=1, column=3, sticky=tk.W, padx=(0, 12), pady=8)

        self.form_label(form, "Reason:").grid(row=2, column=0, sticky=tk.W, padx=(12, 8), pady=8)
        self.override_reason_entry = self.form_entry(form, width=540)
        self.override_reason_entry.grid(row=2, column=1, columnspan=3, sticky=tk.W, padx=(0, 12), pady=8)

        btns = ctk.CTkFrame(form, fg_color="transparent", corner_radius=0)
        btns.grid(row=3, column=0, columnspan=4, pady=(4, 12))
        self.action_button(btns, "Save Override", self.save_override, width=150).pack(side=tk.LEFT, padx=5)
        self.action_button(btns, "Remove Selected", self.remove_selected_override, width=150, primary=False).pack(side=tk.LEFT, padx=5)
        self.action_button(btns, "Refresh", self.refresh_overrides, width=110, primary=False).pack(side=tk.LEFT, padx=5)

        table_panel = self.panel(self.override_tab)
        table_panel.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))
        table_panel.grid_rowconfigure(0, weight=1)
        table_panel.grid_columnconfigure(0, weight=1)

        columns = ("product", "size", "grade", "override", "card", "reason")
        self.override_tree = ttk.Treeview(table_panel, columns=columns, show="headings", height=14)
        headings = {
            "product": "Product",
            "size": "Size",
            "grade": "Grade",
            "override": "Override",
            "card": "Card",
            "reason": "Reason",
        }
        widths = {"product": 280, "size": 80, "grade": 110, "override": 90, "card": 90, "reason": 300}
        for column in columns:
            self.override_tree.heading(column, text=headings[column])
            anchor = tk.W if column in ("product", "reason") else tk.CENTER
            self.override_tree.column(column, width=widths[column], anchor=anchor)
        self.override_tree.grid(row=0, column=0, sticky=tk.NSEW, padx=(12, 0), pady=12)
        scroll = ttk.Scrollbar(table_panel, orient=tk.VERTICAL, command=self.override_tree.yview)
        scroll.grid(row=0, column=1, sticky=tk.NS, padx=(0, 12), pady=12)
        self.override_tree.configure(yscrollcommand=scroll.set)
        self.override_tree.bind("<<TreeviewSelect>>", self.on_override_select)

    def panel(self, parent):
        return ctk.CTkFrame(
            parent,
            fg_color=COLORS["surface"],
            corner_radius=SIZES["corner_radius"],
            border_width=1,
            border_color=COLORS["border"],
        )

    def form_label(self, parent, text):
        return ctk.CTkLabel(
            parent,
            text=text,
            font=FONTS["small_bold"],
            text_color=COLORS["text"],
            height=SIZES["small_label_height"],
            anchor=tk.W,
        )

    def form_entry(self, parent, width=180):
        return ctk.CTkEntry(
            parent,
            width=width,
            height=SIZES["input_height"],
            font=FONTS["small"],
            fg_color=COLORS["app_bg"],
            border_color=COLORS["border"],
            text_color=COLORS["text"],
        )

    def action_button(self, parent, text, command, width=140, primary=True):
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

    def load_products(self):
        self.products = ProductRepository.get_all()
        labels = [self.product_label(product) for product in self.products]
        self.product_by_label = dict(zip(labels, self.products))
        self.override_product_combo.set_completion_list(labels)

    def refresh_rates(self):
        try:
            self.rate_rows = api_client.get("/rates/card")
            for item in self.rate_tree.get_children():
                self.rate_tree.delete(item)
            for row in self.rate_rows:
                rates = row.get("rates") or {}
                self.rate_tree.insert(
                    "",
                    tk.END,
                    values=(
                        row.get("tile_size", ""),
                        row.get("pieces_per_box", ""),
                        self.format_number(row.get("area_per_box")),
                        self.format_rate(rates.get("G1 Prime")),
                        self.format_rate(rates.get("G2 Standard")),
                        self.format_rate(rates.get("G3 Regular")),
                    ),
                )
        except Exception as exc:
            messagebox.showerror("Rate Management", f"Failed to load rate card: {exc}")

    def refresh_overrides(self):
        try:
            self.overrides = api_client.get("/rates/overrides")
            self.override_by_iid.clear()
            for item in self.override_tree.get_children():
                self.override_tree.delete(item)
            for index, row in enumerate(self.overrides):
                iid = str(index)
                self.override_by_iid[iid] = row
                self.override_tree.insert(
                    "",
                    tk.END,
                    iid=iid,
                    values=(
                        row.get("product_name", ""),
                        row.get("tile_size", ""),
                        row.get("grade", ""),
                        self.money(row.get("rate_per_meter")),
                        self.money(row.get("card_rate_per_meter")) if row.get("card_rate_per_meter") is not None else "No card",
                        row.get("reason", ""),
                    ),
                )
        except Exception as exc:
            messagebox.showerror("Rate Management", f"Failed to load overrides: {exc}")

    def open_edit_rate_dialog(self):
        selection = self.rate_tree.selection()
        if not selection:
            messagebox.showwarning("Rate Management", "Please select a tile size.")
            return
        values = self.rate_tree.item(selection[0], "values")
        tile_size = values[0]

        dialog = self.dialog("Edit Rate", "420x300")
        self.form_label(dialog, "Grade:").pack(anchor=tk.W, padx=16, pady=(16, 4))
        grade_var = tk.StringVar(value=VALID_GRADES[0])
        ttk.Combobox(dialog, textvariable=grade_var, values=VALID_GRADES, width=30, state="readonly", font=FONTS["small"]).pack(anchor=tk.W, padx=16)
        self.form_label(dialog, "New Rate/m2:").pack(anchor=tk.W, padx=16, pady=(12, 4))
        rate_entry = self.form_entry(dialog, width=260)
        rate_entry.pack(anchor=tk.W, padx=16)
        self.form_label(dialog, "Reason:").pack(anchor=tk.W, padx=16, pady=(12, 4))
        reason_entry = self.form_entry(dialog, width=360)
        reason_entry.pack(anchor=tk.W, padx=16)

        def save():
            try:
                grade = grade_var.get()
                new_rate = float(rate_entry.get().strip())
                reason = reason_entry.get().strip()
                if len(reason) < 5:
                    raise ValueError("Please enter a reason of at least 5 characters.")
                row = self.find_rate_row(tile_size, grade)
                if not row:
                    raise ValueError("Rate card row not found.")
                old_rate = row["rate_per_meter"]
                params = urlencode({"tile_size": tile_size, "grade": grade})
                impact = api_client.get(f"/rates/impact?{params}")
                if not messagebox.askyesno(
                    "Confirm Rate Change",
                    f"Changing {tile_size} {grade} from {old_rate:g} to {new_rate:g}.\n"
                    f"This affects {impact.get('affected_products', 0)} products across "
                    f"{impact.get('affected_branches', 0)} branches. Continue?",
                ):
                    return
                api_client.put(f"/rates/card?{params}", {"rate_per_meter": new_rate, "reason": reason})
                dialog.destroy()
                self.refresh_rates()
                self.refresh_overrides()
                messagebox.showinfo("Rate Management", "Rate card updated.")
            except (ValueError, ApiClientError) as exc:
                messagebox.showerror("Rate Management", str(exc))
            except Exception as exc:
                messagebox.showerror("Rate Management", f"Failed to update rate: {exc}")

        self.action_button(dialog, "Save Rate", save, width=140).pack(pady=16)

    def open_add_size_dialog(self):
        dialog = self.dialog("Add New Tile Size", "480x470")
        entries = {}
        fields = [
            ("tile_size", "Tile Size:"),
            ("pieces_per_box", "Pieces per Box:"),
            ("area_per_box", "Area per Box:"),
            ("g1_prime", "G1 Prime Rate/m2:"),
            ("g2_standard", "G2 Standard Rate/m2:"),
            ("g3_regular", "G3 Regular Rate/m2:"),
            ("reason", "Reason:"),
        ]
        for key, label in fields:
            self.form_label(dialog, label).pack(anchor=tk.W, padx=16, pady=(10, 2))
            entry = self.form_entry(dialog, width=360)
            entry.pack(anchor=tk.W, padx=16)
            entries[key] = entry

        def save():
            try:
                payload = {
                    "tile_size": entries["tile_size"].get().strip(),
                    "pieces_per_box": int(entries["pieces_per_box"].get().strip()),
                    "area_per_box": float(entries["area_per_box"].get().strip()),
                    "g1_prime": float(entries["g1_prime"].get().strip()),
                    "g2_standard": float(entries["g2_standard"].get().strip()),
                    "g3_regular": float(entries["g3_regular"].get().strip()),
                    "reason": entries["reason"].get().strip(),
                }
                if not payload["tile_size"]:
                    raise ValueError("Tile size is required.")
                if len(payload["reason"]) < 5:
                    raise ValueError("Please enter a reason of at least 5 characters.")
                api_client.post("/rates/sizes", payload)
                dialog.destroy()
                self.refresh_rates()
                messagebox.showinfo("Rate Management", "Tile size and rates added.")
            except (ValueError, ApiClientError) as exc:
                messagebox.showerror("Rate Management", str(exc))
            except Exception as exc:
                messagebox.showerror("Rate Management", f"Failed to add tile size: {exc}")

        self.action_button(dialog, "Add Size", save, width=140).pack(pady=16)

    def save_override(self):
        try:
            product = self.product_by_label.get(self.override_product_var.get())
            if not product:
                raise ValueError("Please select a product.")
            reason = self.override_reason_entry.get().strip()
            if len(reason) < 5:
                raise ValueError("Please enter a reason of at least 5 characters.")
            payload = {
                "product_id": product.id,
                "grade": self.override_grade_var.get(),
                "rate_per_meter": float(self.override_rate_entry.get().strip()),
                "reason": reason,
            }
            api_client.post("/rates/overrides", payload)
            self.override_rate_entry.delete(0, tk.END)
            self.override_reason_entry.delete(0, tk.END)
            self.refresh_overrides()
            messagebox.showinfo("Rate Management", "Product override saved.")
        except (ValueError, ApiClientError) as exc:
            messagebox.showerror("Rate Management", str(exc))
        except Exception as exc:
            messagebox.showerror("Rate Management", f"Failed to save override: {exc}")

    def remove_selected_override(self):
        selection = self.override_tree.selection()
        if not selection:
            messagebox.showwarning("Rate Management", "Please select an override to remove.")
            return
        row = self.override_by_iid.get(selection[0])
        if not row:
            return
        reason = self.override_reason_entry.get().strip()
        if len(reason) < 5:
            messagebox.showerror("Rate Management", "Please enter a reason of at least 5 characters.")
            return
        if not messagebox.askyesno("Remove Override", "Remove the selected product override?"):
            return
        try:
            api_client.post(
                "/rates/overrides/remove",
                {"product_id": row["product_id"], "grade": row["grade"], "reason": reason},
            )
            self.override_reason_entry.delete(0, tk.END)
            self.refresh_overrides()
            messagebox.showinfo("Rate Management", "Product override removed.")
        except Exception as exc:
            messagebox.showerror("Rate Management", f"Failed to remove override: {exc}")

    def on_override_select(self, _event=None):
        selection = self.override_tree.selection()
        if not selection:
            return
        row = self.override_by_iid.get(selection[0])
        if not row:
            return
        for label, product in self.product_by_label.items():
            if product.id == row.get("product_id"):
                self.override_product_var.set(label)
                break
        self.override_grade_var.set(row.get("grade") or VALID_GRADES[0])
        self.override_rate_entry.delete(0, tk.END)
        self.override_rate_entry.insert(0, str(row.get("rate_per_meter") or ""))

    def find_rate_row(self, tile_size, grade):
        for row in self.rate_rows:
            if row.get("tile_size") == tile_size:
                rate = (row.get("rates") or {}).get(grade)
                return rate
        return None

    def dialog(self, title, geometry):
        dialog = ctk.CTkToplevel(self.parent)
        dialog.title(title)
        dialog.geometry(geometry)
        dialog.resizable(False, False)
        dialog.configure(fg_color=COLORS["app_bg"])
        dialog.transient(self.parent.winfo_toplevel())
        dialog.grab_set()
        dialog.focus()
        return dialog

    @staticmethod
    def product_label(product):
        return f"{product.name} - {product.tile_size}"

    @staticmethod
    def format_rate(rate_row):
        if not rate_row:
            return "No rate"
        return RateManagementWindow.money(rate_row.get("rate_per_meter"))

    @staticmethod
    def money(value):
        if value is None:
            return ""
        try:
            return f"Rs. {float(value):.2f}"
        except Exception:
            return str(value)

    @staticmethod
    def format_number(value):
        try:
            return f"{float(value):g}"
        except Exception:
            return str(value or "")
