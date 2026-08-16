"""
Main Window
Main application window with navigation
"""

import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from ui.inventory_window import InventoryWindow
from ui.accessory_window import AccessoryWindow
from ui.sanitary_window import SanitaryWindow
from ui.invoice_window import InvoiceWindow
from ui.invoice_search_window import InvoiceSearchWindow
from ui.stock_overview_window import StockOverviewWindow
from ui.report_window import ReportWindow
from services.auth_service import AuthenticationService
from desktop_client.session import get_update_warning
from desktop_client.updater import UpdateError, download_update, launch_installer, verify_signature
from ui.theme import APP_TITLE, COLORS, FONTS, SIZES, SPACING, apply_theme


class MainWindow:
    """Main application window"""

    def __init__(self, root, current_user):
        apply_theme()
        self.root = root
        self.current_user = current_user
        self.root.title(APP_TITLE)
        self.root.geometry(self.initial_window_geometry())
        self.root.minsize(900, 600)
        self.root.configure(bg=COLORS["app_bg"])
        self.root.after(100, self.maximize_window)

        # Navigation stack
        self.view_stack = []
        self.current_view = None

        # Initialize database
        try:
            from database.init_db import init_database
            init_database()
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to initialize database: {str(e)}")
            self.root.destroy()
            return

        self.setup_ui()
        self.show_home()

    def initial_window_geometry(self):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        width = min(1400, max(900, screen_width - 80))
        height = min(760, max(600, screen_height - 120))
        return f"{width}x{height}+20+10"

    def maximize_window(self):
        try:
            self.root.state('zoomed')  # Maximize on Windows
        except Exception:
            pass

    def setup_ui(self):
        """Setup the main UI"""
        update_warning = get_update_warning()
        if update_warning:
            warning_frame = ctk.CTkFrame(
                self.root,
                fg_color=COLORS["danger"],
                corner_radius=0,
                height=44,
            )
            warning_frame.pack(fill=tk.X)
            warning_frame.pack_propagate(False)
            ctk.CTkLabel(
                warning_frame,
                text=update_warning.get(
                    "warning_message",
                    "This version is out of date. Stock and prices may display incorrectly. Please contact your administrator to update."
                ),
                font=FONTS["small_bold"],
                text_color=COLORS["text"],
                height=SIZES["small_label_height"],
            ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10, pady=9)
            if (
                update_warning.get("download_url")
                and update_warning.get("sha256")
                and not update_warning.get("updates_disabled")
            ):
                ctk.CTkButton(
                    warning_frame,
                    text="Install Update",
                    command=self.install_update,
                    fg_color=COLORS["warning"],
                    hover_color=COLORS["warning_hover"],
                    text_color=COLORS["text"],
                    font=FONTS["small_bold"],
                    corner_radius=SIZES["corner_radius"],
                    cursor="hand2",
                ).pack(side=tk.RIGHT, padx=10, pady=5)

        # Header
        header_frame = ctk.CTkFrame(
            self.root,
            fg_color=COLORS["surface"],
            corner_radius=0,
            height=SIZES["header_height"],
        )
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)

        # Top bar with user info and logout
        top_bar = ctk.CTkFrame(
            header_frame,
            fg_color=COLORS["surface_alt"],
            corner_radius=SIZES["corner_radius"],
            height=SIZES["top_bar_height"],
        )
        top_bar.pack(fill=tk.X, padx=14, pady=(8, 4))
        top_bar.pack_propagate(False)

        user_info = ctk.CTkLabel(
            top_bar,
            text=f"Logged in as: {self.current_user.username} ({self.current_user.role.upper()})",
            font=FONTS["small_bold"],
            text_color=COLORS["text_muted"],
            height=SIZES["small_label_height"],
        )
        user_info.pack(side=tk.LEFT, padx=12, pady=8)

        logout_btn = ctk.CTkButton(
            top_bar,
            text="Logout",
            command=self.logout,
            fg_color=COLORS["danger"],
            hover_color=COLORS["danger_hover"],
            text_color=COLORS["text"],
            font=FONTS["small"],
            width=96,
            height=30,
            corner_radius=SIZES["corner_radius"],
            cursor="hand2",
        )
        logout_btn.pack(side=tk.RIGHT, padx=8, pady=5)

        title_label = ctk.CTkLabel(
            header_frame,
            text=APP_TITLE,
            font=FONTS["title"],
            text_color=COLORS["text"],
            height=SIZES["title_label_height"],
        )
        title_label.pack(pady=(4, 12))

        # Status bar
        status_frame = ctk.CTkFrame(
            self.root,
            fg_color=COLORS["surface"],
            corner_radius=0,
            height=SIZES["status_height"],
        )
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        status_frame.pack_propagate(False)

        status_label = ctk.CTkLabel(
            status_frame,
            text=f"Ready | {APP_TITLE}",
            font=FONTS["status"],
            text_color=COLORS["text_muted"],
            anchor=tk.W,
            height=SIZES["status_label_height"],
        )
        status_label.pack(side=tk.LEFT, padx=10, pady=7)

        # Main content area (Container for all views)
        self.content_frame = ctk.CTkFrame(self.root, fg_color=COLORS["app_bg"], corner_radius=0)
        self.content_frame.pack(fill=tk.BOTH, expand=True)

        # Setup Home Scrollable Container
        self.home_scroll_container = ctk.CTkFrame(self.content_frame, fg_color=COLORS["app_bg"], corner_radius=0)

        home_canvas = tk.Canvas(self.home_scroll_container, bg=COLORS["app_bg"], highlightthickness=0)
        home_scrollbar = ctk.CTkScrollbar(self.home_scroll_container, orientation="vertical", command=home_canvas.yview)
        self.home_frame = ctk.CTkFrame(home_canvas, fg_color=COLORS["app_bg"], corner_radius=0)

        self.home_frame.bind(
            "<Configure>",
            lambda e: home_canvas.configure(scrollregion=home_canvas.bbox("all"))
        )

        home_canvas_window = home_canvas.create_window((0, 0), window=self.home_frame, anchor="nw")

        def configure_home_canvas(event):
            home_canvas.itemconfig(home_canvas_window, width=event.width)

        home_canvas.bind("<Configure>", configure_home_canvas)
        home_canvas.configure(yscrollcommand=home_scrollbar.set)

        home_canvas.pack(side="left", fill="both", expand=True)
        home_scrollbar.pack(side="right", fill="y")

        # Dashboard label
        ctk.CTkLabel(
            self.home_frame,
            text="Dashboard",
            font=FONTS["section"],
            text_color=COLORS["text"],
            height=SIZES["section_label_height"],
        ).pack(pady=(24, 12))

        # Menu buttons container
        menu_container = ctk.CTkFrame(self.home_frame, fg_color="transparent", corner_radius=0)
        menu_container.pack(pady=20)

        # Grid layout for buttons
        buttons = [
            ("Inventory Management", COLORS["primary"], COLORS["primary_hover"], self.open_inventory),
            ("Stock Overview", COLORS["search"], COLORS["search_hover"], self.open_stock_overview),
            ("Accessories", COLORS["accessory"], COLORS["accessory_hover"], self.open_accessories),
            ("Invoice & Billing", COLORS["success"], COLORS["success_hover"], self.open_invoice),
            ("Search Invoices", COLORS["search"], COLORS["search_hover"], self.open_invoice_search),
        ]

        for i, (text, color, hover, cmd) in enumerate(buttons):
            btn = ctk.CTkButton(
                menu_container,
                text=text,
                fg_color=color,
                hover_color=hover,
                text_color=COLORS["text"],
                border_width=1 if color != COLORS["primary"] else 0,
                border_color=COLORS["border"],
                command=cmd,
                font=FONTS["button"],
                width=SIZES["button_width"],
                height=SIZES["button_height"],
                corner_radius=SIZES["button_corner_radius"],
                cursor="hand2",
            )
            btn.grid(row=i // 2, column=i % 2, padx=SPACING["button_pad_x"], pady=SPACING["button_pad_y"])

        # Admin Buttons
        if AuthenticationService.is_admin(self.current_user):
            admin_label = ctk.CTkLabel(
                self.home_frame,
                text="Administration",
                font=FONTS["eyebrow"],
                text_color=COLORS["text_muted"],
                height=SIZES["section_label_height"],
            )
            admin_label.configure(text="ADMINISTRATION")
            admin_label.pack(pady=(20, 12))

            admin_container = ctk.CTkFrame(self.home_frame, fg_color="transparent", corner_radius=0)
            admin_container.pack()

            admin_buttons = [
                ("Reports", COLORS["reports"], COLORS["reports_hover"], self.open_reports),
                ("User Management", COLORS["users"], COLORS["users_hover"], self.open_user_management),
                ("Activity Log", COLORS["activity"], COLORS["activity_hover"], self.open_activity_log),
            ]

            for i, (text, color, hover, cmd) in enumerate(admin_buttons):
                btn = ctk.CTkButton(
                    admin_container,
                    text=text,
                    fg_color=color,
                    hover_color=hover,
                    text_color=COLORS["text"],
                    border_width=1,
                    border_color=COLORS["border"],
                    command=cmd,
                    font=FONTS["button"],
                    width=SIZES["admin_button_width"],
                    height=SIZES["admin_button_height"],
                    corner_radius=SIZES["button_corner_radius"],
                    cursor="hand2",
                )
                btn.grid(row=0, column=i, padx=10, pady=10)

        # Back Button (Initially hidden)
        self.nav_bar = ctk.CTkFrame(self.content_frame, fg_color=COLORS["surface_alt"], corner_radius=0, height=44)
        ctk.CTkButton(
            self.nav_bar,
            text="< Back to Dashboard",
            command=self.show_home,
            fg_color=COLORS["secondary"],
            hover_color=COLORS["secondary_hover"],
            text_color=COLORS["text"],
            font=FONTS["small_bold"],
            width=176,
            height=32,
            corner_radius=SIZES["corner_radius"],
        ).pack(side=tk.LEFT, padx=10, pady=6)

    def clear_content(self):
        """Clear current view in content frame"""
        # We now have a more complex structure (Canvas -> Frame)
        # We just need to hide/destroy the view-specific parts
        for widget in self.content_frame.winfo_children():
            if widget not in (self.nav_bar, self.home_scroll_container):
                widget.destroy()
        self.home_scroll_container.pack_forget()
        self.nav_bar.pack_forget()

    def show_home(self):
        """Show home dashboard"""
        self.clear_content()
        self.current_view = None
        self.root.title(APP_TITLE)
        self.home_scroll_container.pack(fill=tk.BOTH, expand=True)

    def switch_view(self, view_class, *args, **kwargs):
        """Switch current view to a new frame-based view with scrolling support"""
        self.clear_content()
        self.nav_bar.pack(fill=tk.X, side=tk.TOP)

        # Create scrollable container
        container = ctk.CTkFrame(self.content_frame, fg_color=COLORS["app_bg"], corner_radius=0)
        container.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(container, bg=COLORS["app_bg"], highlightthickness=0)
        scrollbar = ctk.CTkScrollbar(container, orientation="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=COLORS["app_bg"])

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        # Update canvas window width to match canvas width
        def configure_canvas(event):
            canvas.itemconfig(canvas_window, width=event.width)

        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.bind("<Configure>", configure_canvas)

        canvas.configure(yscrollcommand=scrollbar.set)

        # Mousewheel binding
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        # Bind to canvas and scrollable_frame, not 'all' to avoid focus issues
        def _bind_mousewheel(widget):
            widget.bind("<MouseWheel>", _on_mousewheel)
            for child in widget.winfo_children():
                _bind_mousewheel(child)

        _bind_mousewheel(canvas)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Initialize the view class into the scrollable frame
        self.current_view = view_class(scrollable_frame, *args, **kwargs)

    def open_inventory(self):
        """Open inventory management within the same window"""
        self.switch_view(InventoryWindow, self.current_user)

    def open_accessories(self):
        """Open accessories management within the same window"""
        self.switch_view(AccessoryWindow, self.current_user)

    def open_sanitary(self):
        """Open sanitary management within the same window"""
        self.switch_view(SanitaryWindow, self.current_user)

    def open_invoice(self):
        """Open invoice creation within the same window"""
        self.switch_view(InvoiceWindow, self.current_user)

    def open_stock_overview(self):
        """Open read-only stock overview within the same window"""
        self.switch_view(StockOverviewWindow, self.current_user)

    def open_reports(self):
        """Open reports within the same window (Admin only)"""
        if not AuthenticationService.can_view_reports(self.current_user):
            messagebox.showerror("Access Denied", "You do not have permission to view reports.")
            return
        self.switch_view(ReportWindow)

    def open_invoice_search(self):
        """Open invoice search within the same window"""
        self.switch_view(InvoiceSearchWindow, self.current_user)

    def open_user_management(self):
        """Open user management within the same window (Admin only)"""
        if not AuthenticationService.can_manage_users(self.current_user):
            messagebox.showerror("Access Denied", "You do not have permission to manage users.")
            return
        from ui.user_management_window import UserManagementWindow
        self.switch_view(UserManagementWindow, current_user=self.current_user)

    def open_activity_log(self):
        """Open activity log within the same window (Admin only)"""
        if not AuthenticationService.can_manage_users(self.current_user):
            messagebox.showerror("Access Denied", "You do not have permission to view activity logs.")
            return
        from ui.activity_log_window import ActivityLogWindow
        self.switch_view(ActivityLogWindow)

    def logout(self):
        """Logout and return to login screen"""
        if messagebox.askyesno("Logout", "Are you sure you want to logout?"):
            # Log logout activity
            try:
                from services.activity_log_service import ActivityLogService
                ActivityLogService.log_logout(self.current_user)
            except:
                pass  # Don't fail logout if logging fails

            self.root.destroy()
            # Restart application with login
            import tkinter as tk
            from ui.login_window import LoginWindow
            login_root = tk.Tk()
            login_app = LoginWindow(login_root, self.on_login_success)
            login_root.mainloop()

    def on_login_success(self, user):
        """Callback when user logs in again"""
        self.current_user = user
        # Refresh UI if needed
        pass

    def install_update(self):
        update_warning = get_update_warning()
        if not update_warning:
            return
        if isinstance(self.current_view, InvoiceWindow) and getattr(self.current_view, "invoice_items", None):
            messagebox.showwarning(
                "Finish Invoice First",
                "Finish or clear the open invoice before installing an update."
            )
            return
        if not messagebox.askyesno(
            "Install Update",
            "Update available. Install now?\n\nThe app will close after the update installer starts."
        ):
            return
        try:
            installer = download_update(update_warning)
            verify_signature(
                installer,
                update_warning.get("signature_publisher"),
                update_warning.get("signature_thumbprint"),
            )
            launch_installer(installer, update_warning)
            self.root.destroy()
        except UpdateError as exc:
            messagebox.showerror("Update Failed", str(exc))
        except Exception as exc:
            messagebox.showerror("Update Failed", f"Could not install update: {exc}")
