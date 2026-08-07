"""Shared presentation values for the desktop UI."""

import tkinter as tk
from tkinter import ttk

import customtkinter as ctk


APP_TITLE = "Tile Index - Inventory & Billing System"
APPEARANCE_MODE = "dark"
COLOR_THEME = "blue"

COLORS = {
    "app_bg": "#0f172a",
    "surface": "#111827",
    "surface_alt": "#1f2937",
    "card": "#1e2530",
    "card_hover": "#2a3443",
    "surface_muted": "#334155",
    "text": "#f8fafc",
    "text_muted": "#cbd5e1",
    "border": "#334155",
    "danger": "#dc2626",
    "danger_hover": "#b91c1c",
    "warning": "#f97316",
    "warning_hover": "#ea580c",
    "primary": "#2563eb",
    "primary_hover": "#1d4ed8",
    "accessory": "#1e2530",
    "accessory_hover": "#2a3443",
    "success": "#1e2530",
    "success_hover": "#2a3443",
    "search": "#1e2530",
    "search_hover": "#2a3443",
    "reports": "#1e2530",
    "reports_hover": "#2a3443",
    "users": "#1e2530",
    "users_hover": "#2a3443",
    "activity": "#1e2530",
    "activity_hover": "#2a3443",
    "secondary": "#475569",
    "secondary_hover": "#334155",
}

FONTS = {
    "status": ("Segoe UI", 10),
    "small": ("Segoe UI", 10),
    "small_bold": ("Segoe UI", 10, "bold"),
    "body_bold": ("Segoe UI", 12, "bold"),
    "eyebrow": ("Segoe UI", 11, "bold"),
    "button": ("Segoe UI", 15, "bold"),
    "section": ("Segoe UI", 17, "bold"),
    "title": ("Segoe UI", 24, "bold"),
}

SIZES = {
    "corner_radius": 12,
    "button_corner_radius": 14,
    "button_width": 300,
    "button_height": 68,
    "admin_button_width": 260,
    "admin_button_height": 62,
    "header_height": 112,
    "top_bar_height": 40,
    "title_label_height": 42,
    "section_label_height": 36,
    "small_label_height": 24,
    "status_height": 40,
    "status_label_height": 26,
    "login_width": 460,
    "login_height": 440,
    "login_header_height": 118,
    "input_height": 36,
    "dropdown_width": 45,
    "compact_dropdown_width": 30,
}

SPACING = {
    "page_x": 18,
    "page_y": 18,
    "button_pad_x": 20,
    "button_pad_y": 14,
}

_TTK_IMAGES = []


def apply_theme():
    ctk.set_appearance_mode(APPEARANCE_MODE)
    ctk.set_default_color_theme(COLOR_THEME)
    apply_ttk_theme()


def apply_ttk_theme():
    """Style native ttk widgets used for searchable dropdowns and data tables."""
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass

    _install_combobox_arrow(style)

    style.configure(
        "TCombobox",
        fieldbackground=COLORS["surface"],
        background=COLORS["surface"],
        foreground=COLORS["text"],
        arrowcolor=COLORS["text_muted"],
        bordercolor=COLORS["border"],
        lightcolor=COLORS["border"],
        darkcolor=COLORS["border"],
        selectbackground=COLORS["primary"],
        selectforeground=COLORS["text"],
        buttonbackground=COLORS["surface"],
        padding=(8, 4),
        relief="flat",
        arrowsize=14,
    )
    style.map(
        "TCombobox",
        fieldbackground=[
            ("readonly", COLORS["surface"]),
            ("focus", COLORS["surface"]),
            ("active", COLORS["surface"]),
            ("disabled", COLORS["surface_alt"]),
        ],
        foreground=[
            ("readonly", COLORS["text"]),
            ("focus", COLORS["text"]),
            ("active", COLORS["text"]),
            ("disabled", COLORS["text_muted"]),
        ],
        background=[
            ("readonly", COLORS["surface"]),
            ("focus", COLORS["surface"]),
            ("active", COLORS["card_hover"]),
            ("disabled", COLORS["surface_alt"]),
        ],
        buttonbackground=[
            ("readonly", COLORS["surface"]),
            ("focus", COLORS["surface"]),
            ("active", COLORS["card_hover"]),
            ("disabled", COLORS["surface_alt"]),
        ],
        arrowcolor=[
            ("readonly", COLORS["text_muted"]),
            ("focus", COLORS["text"]),
            ("active", COLORS["text"]),
            ("disabled", COLORS["text_muted"]),
        ],
        bordercolor=[
            ("focus", COLORS["primary"]),
            ("active", COLORS["border"]),
            ("disabled", COLORS["border"]),
        ],
    )
    try:
        style.master.option_add("*TCombobox*Listbox.background", COLORS["surface"])
        style.master.option_add("*TCombobox*Listbox.foreground", COLORS["text"])
        style.master.option_add("*TCombobox*Listbox.selectBackground", COLORS["primary"])
        style.master.option_add("*TCombobox*Listbox.selectForeground", COLORS["text"])
    except Exception:
        pass

    style.configure(
        "Treeview",
        background=COLORS["surface"],
        fieldbackground=COLORS["surface"],
        foreground=COLORS["text"],
        bordercolor=COLORS["border"],
        lightcolor=COLORS["border"],
        darkcolor=COLORS["border"],
        rowheight=28,
        font=FONTS["small"],
    )
    style.configure(
        "Treeview.Heading",
        background=COLORS["surface_alt"],
        foreground=COLORS["text"],
        bordercolor=COLORS["border"],
        lightcolor=COLORS["border"],
        darkcolor=COLORS["border"],
        font=FONTS["small_bold"],
        padding=(8, 6),
    )
    style.map(
        "Treeview",
        background=[("selected", COLORS["primary"])],
        foreground=[("selected", COLORS["text"])],
    )
    style.map(
        "Treeview.Heading",
        background=[("active", COLORS["card_hover"])],
        foreground=[("active", COLORS["text"])],
    )


def _make_combobox_arrow(width=24, height=30, bg=None, border=None, arrow=None):
    image = tk.PhotoImage(width=width, height=height)
    bg = bg or COLORS["surface"]
    border = border or COLORS["border"]
    arrow = arrow or COLORS["text_muted"]
    image.put(bg, to=(0, 0, width, height))
    image.put(border, to=(0, 0, 1, height))

    mid_x = width // 2
    mid_y = height // 2 + 1
    rows = [
        (mid_y - 3, mid_x - 5, mid_x + 5),
        (mid_y - 2, mid_x - 4, mid_x + 4),
        (mid_y - 1, mid_x - 3, mid_x + 3),
        (mid_y, mid_x - 2, mid_x + 2),
        (mid_y + 1, mid_x - 1, mid_x + 1),
        (mid_y + 2, mid_x, mid_x),
    ]
    for y, x1, x2 in rows:
        image.put(arrow, to=(x1, y, x2 + 1, y + 1))
    _TTK_IMAGES.append(image)
    return image


def _install_combobox_arrow(style):
    """Replace the native combobox arrow button with a dark image element."""
    normal = _make_combobox_arrow(bg=COLORS["surface"], border=COLORS["border"], arrow=COLORS["text_muted"])
    active = _make_combobox_arrow(bg=COLORS["card_hover"], border=COLORS["border"], arrow=COLORS["text"])
    disabled = _make_combobox_arrow(bg=COLORS["surface_alt"], border=COLORS["border"], arrow=COLORS["text_muted"])
    try:
        style.element_create(
            "DarkCombobox.downarrow",
            "image",
            normal,
            ("active", active),
            ("focus", active),
            ("disabled", disabled),
            sticky=tk.NSEW,
        )
        style.layout(
            "TCombobox",
            [
                (
                    "Combobox.field",
                    {
                        "sticky": tk.NSEW,
                        "children": [
                            (
                                "Combobox.padding",
                                {
                                    "sticky": tk.NSEW,
                                    "children": [("Combobox.textarea", {"sticky": tk.NSEW})],
                                },
                            ),
                            ("DarkCombobox.downarrow", {"side": tk.RIGHT, "sticky": tk.NS}),
                        ],
                    },
                )
            ],
        )
    except tk.TclError:
        pass
