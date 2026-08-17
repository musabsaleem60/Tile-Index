"""
Login Window
User authentication screen
"""

import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from desktop_client.api_client import ApiClientError
from desktop_client.catalog_preload import preload_catalogues
from desktop_client.config import API_BASE_URL, CHECK_UPDATES
from desktop_client.machine_status import report_desktop_status
from desktop_client.session import api_client, set_authenticated_session, set_update_warning
from desktop_client.update_checker import check_for_update, is_version_older
from desktop_client.updater import (
    UpdateError,
    clear_update_state,
    download_update,
    launch_installer,
    read_update_state,
    verify_signature,
)
from models.user import User
from ui.theme import COLORS, FONTS, SIZES, apply_theme


class LoginWindow:
    """Login window for user authentication"""
    
    def __init__(self, parent, on_success_callback):
        apply_theme()
        self.parent = parent
        self.parent.title("Login - Tile Index")
        self.parent.geometry(f"{SIZES['login_width']}x{SIZES['login_height']}")
        self.parent.minsize(420, 420)
        self.parent.configure(bg=COLORS["app_bg"])
        
        # Center the window
        self.center_window()
        
        self.on_success_callback = on_success_callback
        self.current_user = None
        self.update_warning = None
        self.update_warning_label = None
        self.update_button = None
        
        self.setup_ui()
        self.check_previous_update_state()
        self.check_for_updates()
    
    def center_window(self):
        """Center the window on screen"""
        self.parent.update_idletasks()
        width = self.parent.winfo_width()
        height = self.parent.winfo_height()
        x = (self.parent.winfo_screenwidth() // 2) - (width // 2)
        y = (self.parent.winfo_screenheight() // 2) - (height // 2)
        self.parent.geometry(f'{width}x{height}+{x}+{y}')
    
    def setup_ui(self):
        """Setup the login UI"""
        # Header
        header_frame = ctk.CTkFrame(
            self.parent,
            fg_color=COLORS["surface"],
            corner_radius=0,
            height=SIZES["login_header_height"],
        )
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        
        ctk.CTkLabel(
            header_frame,
            text="Tile Index",
            font=FONTS["title"],
            text_color=COLORS["text"],
            height=SIZES["title_label_height"],
        ).pack(pady=(18, 4))
        
        ctk.CTkLabel(
            header_frame,
            text="Inventory & Billing System",
            font=FONTS["body_bold"],
            text_color=COLORS["text_muted"],
            height=SIZES["small_label_height"],
        ).pack()
        
        # Main content
        content_frame = ctk.CTkFrame(
            self.parent,
            fg_color=COLORS["app_bg"],
            corner_radius=0,
        )
        content_frame.pack(fill=tk.BOTH, expand=True, padx=40, pady=24)

        self.update_warning_label = ctk.CTkLabel(
            content_frame,
            font=FONTS["small_bold"],
            fg_color=COLORS["danger"],
            text_color=COLORS["text"],
            wraplength=320,
            justify=tk.CENTER,
            padx=8,
            height=56,
            corner_radius=SIZES["corner_radius"],
        )
        self.update_button = ctk.CTkButton(
            content_frame,
            text="Install Update",
            command=self.install_update,
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            text_color=COLORS["text"],
            font=FONTS["small_bold"],
            height=34,
            corner_radius=SIZES["corner_radius"],
            cursor="hand2",
        )
        
        # Username
        self.username_label = ctk.CTkLabel(
            content_frame,
            text="Username:",
            font=FONTS["small_bold"],
            text_color=COLORS["text"],
            height=SIZES["small_label_height"],
        )
        self.username_label.pack(anchor=tk.W, pady=(4, 6))
        
        self.username_entry = ctk.CTkEntry(
            content_frame,
            width=340,
            height=SIZES["input_height"],
            font=FONTS["small"],
            fg_color=COLORS["surface"],
            border_color=COLORS["border"],
            text_color=COLORS["text"],
        )
        self.username_entry.pack(fill=tk.X, pady=(0, 14))
        self.username_entry.focus()
        self.username_entry.bind('<Return>', lambda e: self.password_entry.focus())
        
        # Password
        ctk.CTkLabel(
            content_frame,
            text="Password:",
            font=FONTS["small_bold"],
            text_color=COLORS["text"],
            height=SIZES["small_label_height"],
        ).pack(anchor=tk.W, pady=(0, 6))
        
        self.password_entry = ctk.CTkEntry(
            content_frame,
            width=340,
            height=SIZES["input_height"],
            font=FONTS["small"],
            fg_color=COLORS["surface"],
            border_color=COLORS["border"],
            text_color=COLORS["text"],
            show="*",
        )
        self.password_entry.pack(fill=tk.X, pady=(0, 18))
        self.password_entry.bind('<Return>', lambda e: self.login())
        
        # Login button
        login_btn = ctk.CTkButton(
            content_frame,
            text="Login",
            command=self.login,
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            text_color=COLORS["text"],
            font=FONTS["button"],
            height=44,
            corner_radius=SIZES["button_corner_radius"],
            cursor="hand2",
        )
        login_btn.pack(fill=tk.X, pady=(0, 14))
        
        # Default credentials hint (for first-time setup)
        hint_frame = ctk.CTkFrame(content_frame, fg_color="transparent", corner_radius=0)
        hint_frame.pack(fill=tk.X)
        
        ctk.CTkLabel(
            hint_frame,
            text=f"API: {API_BASE_URL}",
            font=FONTS["status"],
            text_color=COLORS["text_muted"],
            height=SIZES["small_label_height"],
        ).pack()
    
    def login(self):
        """Handle login attempt"""
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        
        if not username or not password:
            messagebox.showerror("Login Error", "Please enter both username and password")
            return
        
        try:
            response = api_client.post("/auth/login", {
                "username": username,
                "password": password
            })
            set_authenticated_session(response["access_token"])

            api_user = response["user"]
            user = User(
                id=api_user["id"],
                username=api_user["username"],
                role=api_user["role"],
                branch_id=api_user.get("branch_id"),
                is_active=api_user.get("is_active", True),
                created_at=api_user.get("created_at")
            )
            user.api_token = response["access_token"]
            self.current_user = user
            try:
                preload_catalogues()
            except Exception:
                pass
            try:
                report_desktop_status(api_client, self.update_warning)
            except Exception:
                pass

            self.parent.destroy()
            self.on_success_callback(user)
        except ApiClientError as e:
            messagebox.showerror("Login Failed", str(e))
            self.password_entry.delete(0, tk.END)
        except ValueError as e:
            messagebox.showerror("Login Failed", str(e))
            self.password_entry.delete(0, tk.END)
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")

    def check_for_updates(self):
        """Notify users when a newer desktop build is available."""
        self.update_warning = None
        set_update_warning(None)
        if not CHECK_UPDATES:
            return
        try:
            update = check_for_update(api_client)
            if update:
                self.update_warning = update
                set_update_warning(update)
                self.show_update_warning()
        except Exception:
            pass

    def check_previous_update_state(self):
        state = read_update_state()
        if not state or state.get("status") != "installer_started":
            return
        target_version = state.get("version")
        try:
            from desktop_client.config import APP_VERSION
            if target_version and not is_version_older(APP_VERSION, target_version):
                clear_update_state()
                return
        except Exception:
            pass
        messagebox.showwarning(
            "Update Did Not Complete",
            "The previous update did not complete. The app is still available, "
            "and your configuration file was preserved. Please try the update again "
            "or contact your administrator."
        )

    def show_update_warning(self):
        if not self.update_warning_label or not self.update_warning:
            return
        self.update_warning_label.configure(text=self.update_warning.get("warning_message", ""))
        self.update_warning_label.pack(fill=tk.X, pady=(0, 15), before=self.username_label)
        if (
            self.update_warning.get("download_url")
            and self.update_warning.get("sha256")
            and not self.update_warning.get("updates_disabled")
        ):
            self.update_button.pack(fill=tk.X, pady=(0, 15), before=self.username_label)

    def install_update(self):
        if not self.update_warning:
            return
        if not messagebox.askyesno(
            "Install Update",
            "Update available. Install now?\n\nThe app will close after the update installer starts."
        ):
            return
        try:
            self.update_button.configure(state=tk.DISABLED, text="Downloading update...")
            self.parent.update_idletasks()
            installer = download_update(self.update_warning)
            self.update_button.configure(text="Verifying update...")
            self.parent.update_idletasks()
            verify_signature(
                installer,
                self.update_warning.get("signature_publisher"),
                self.update_warning.get("signature_thumbprint"),
            )
            launch_installer(installer, self.update_warning)
            self.parent.destroy()
        except UpdateError as exc:
            self.update_button.configure(state=tk.NORMAL, text="Install Update")
            messagebox.showerror("Update Failed", str(exc))
        except Exception as exc:
            self.update_button.configure(state=tk.NORMAL, text="Install Update")
            messagebox.showerror("Update Failed", f"Could not install update: {exc}")

