"""
Login Window
User authentication screen
"""

import tkinter as tk
from tkinter import messagebox
from desktop_client.api_client import ApiClientError
from desktop_client.config import API_BASE_URL, CHECK_UPDATES
from desktop_client.session import api_client, set_authenticated_session
from desktop_client.update_checker import check_for_update
from models.user import User


class LoginWindow:
    """Login window for user authentication"""
    
    def __init__(self, parent, on_success_callback):
        self.parent = parent
        self.parent.title("Login - Tile Index")
        self.parent.geometry("400x300")
        self.parent.resizable(False, False)
        
        # Center the window
        self.center_window()
        
        self.on_success_callback = on_success_callback
        self.current_user = None
        
        self.setup_ui()
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
        header_frame = tk.Frame(self.parent, bg="#2c3e50", height=80)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        
        tk.Label(
            header_frame,
            text="Tile Index",
            font=("Arial", 24, "bold"),
            bg="#2c3e50",
            fg="white"
        ).pack(pady=15)
        
        tk.Label(
            header_frame,
            text="Inventory & Billing System",
            font=("Arial", 12),
            bg="#2c3e50",
            fg="#ecf0f1"
        ).pack()
        
        # Main content
        content_frame = tk.Frame(self.parent, bg="#ecf0f1")
        content_frame.pack(fill=tk.BOTH, expand=True, padx=40, pady=30)
        
        # Username
        tk.Label(
            content_frame,
            text="Username:",
            font=("Arial", 11),
            bg="#ecf0f1"
        ).pack(anchor=tk.W, pady=(10, 5))
        
        self.username_entry = tk.Entry(content_frame, width=30, font=("Arial", 11))
        self.username_entry.pack(pady=(0, 15))
        self.username_entry.focus()
        self.username_entry.bind('<Return>', lambda e: self.password_entry.focus())
        
        # Password
        tk.Label(
            content_frame,
            text="Password:",
            font=("Arial", 11),
            bg="#ecf0f1"
        ).pack(anchor=tk.W, pady=(0, 5))
        
        self.password_entry = tk.Entry(content_frame, width=30, font=("Arial", 11), show="*")
        self.password_entry.pack(pady=(0, 20))
        self.password_entry.bind('<Return>', lambda e: self.login())
        
        # Login button
        login_btn = tk.Button(
            content_frame,
            text="Login",
            command=self.login,
            bg="#3498db",
            fg="white",
            font=("Arial", 12, "bold"),
            width=20,
            height=2,
            cursor="hand2"
        )
        login_btn.pack(pady=10)
        
        # Default credentials hint (for first-time setup)
        hint_frame = tk.Frame(content_frame, bg="#ecf0f1")
        hint_frame.pack(pady=(10, 0))
        
        tk.Label(
            hint_frame,
            text=f"API: {API_BASE_URL}",
            font=("Arial", 9),
            bg="#ecf0f1",
            fg="#7f8c8d"
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
        if not CHECK_UPDATES:
            return
        try:
            update = check_for_update(api_client)
            if update:
                message = (
                    f"A new Tile Index version is available: {update['latest_version']}\n\n"
                    f"{update.get('release_notes') or ''}\n\n"
                    f"Download: {update.get('download_url') or 'Ask administrator for installer'}"
                )
                messagebox.showinfo("Update Available", message)
        except Exception:
            pass

