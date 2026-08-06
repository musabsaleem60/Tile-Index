"""Shared presentation values for the desktop UI."""

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
}

SPACING = {
    "page_x": 18,
    "page_y": 18,
    "button_pad_x": 20,
    "button_pad_y": 14,
}


def apply_theme():
    ctk.set_appearance_mode(APPEARANCE_MODE)
    ctk.set_default_color_theme(COLOR_THEME)
