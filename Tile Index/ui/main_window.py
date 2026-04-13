"""
Main Window
Main application window with navigation
"""

import tkinter as tk
from tkinter import ttk, messagebox
from ui.inventory_window import InventoryWindow
from ui.invoice_window import InvoiceWindow
from ui.invoice_search_window import InvoiceSearchWindow
from ui.report_window import ReportWindow
from services.auth_service import AuthenticationService


class MainWindow:
    """Main application window"""
    
    def __init__(self, root, current_user):
        self.root = root
        self.current_user = current_user
        self.root.title("Tile Index - Inventory & Billing System")
        self.root.geometry("1200x700")
        self.root.state('zoomed')  # Maximize on Windows
        
        # Initialize database
        try:
            from database.init_db import init_database
            init_database()
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to initialize database: {str(e)}")
            self.root.destroy()
            return
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the main UI"""
        # Header
        header_frame = tk.Frame(self.root, bg="#2c3e50", height=80)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        
        # Top bar with user info and logout
        top_bar = tk.Frame(header_frame, bg="#34495e")
        top_bar.pack(fill=tk.X, padx=10, pady=5)
        
        user_info = tk.Label(
            top_bar,
            text=f"Logged in as: {self.current_user.username} ({self.current_user.role.upper()})",
            font=("Arial", 10, "bold"),
            bg="#34495e",
            fg="white"
        )
        user_info.pack(side=tk.LEFT)
        
        logout_btn = tk.Button(
            top_bar,
            text="Logout",
            command=self.logout,
            bg="#e74c3c",
            fg="white",
            font=("Arial", 9),
            width=10,
            cursor="hand2"
        )
        logout_btn.pack(side=tk.RIGHT)
        
        title_label = tk.Label(
            header_frame,
            text="Tile Index - Inventory & Billing System",
            font=("Arial", 24, "bold"),
            bg="#2c3e50",
            fg="white"
        )
        title_label.pack(pady=10)
        
        # Main content area
        content_frame = tk.Frame(self.root, bg="#ecf0f1")
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Menu buttons frame
        menu_frame = tk.Frame(content_frame, bg="#ecf0f1")
        menu_frame.pack(fill=tk.BOTH, expand=True)
        
        # Button style
        button_style = {
            'font': ('Arial', 14, 'bold'),
            'width': 25,
            'height': 3,
            'cursor': 'hand2',
            'relief': tk.RAISED,
            'bd': 3
        }
        
        # Inventory Management Button (Available to all)
        inv_btn = tk.Button(
            menu_frame,
            text="📦 Inventory Management",
            bg="#3498db",
            fg="white",
            command=self.open_inventory,
            **button_style
        )
        inv_btn.pack(pady=15)
        
        # Invoice & Billing Button (Available to all)
        invoice_btn = tk.Button(
            menu_frame,
            text="🧾 Invoice & Billing",
            bg="#27ae60",
            fg="white",
            command=self.open_invoice,
            **button_style
        )
        invoice_btn.pack(pady=15)
        
        # Search Invoices Button (Available to all)
        search_invoice_btn = tk.Button(
            menu_frame,
            text="🔍 Search Invoices",
            bg="#9b59b6",
            fg="white",
            command=self.open_invoice_search,
            **button_style
        )
        search_invoice_btn.pack(pady=15)
        
        # Reports Button (Admin only)
        if AuthenticationService.is_admin(self.current_user):
            report_btn = tk.Button(
                menu_frame,
                text="📊 Reports",
                bg="#e67e22",
                fg="white",
                command=self.open_reports,
                **button_style
            )
            report_btn.pack(pady=15)
        
        # User Management Button (Admin only)
        if AuthenticationService.is_admin(self.current_user):
            user_mgmt_btn = tk.Button(
                menu_frame,
                text="👥 User Management",
                bg="#16a085",
                fg="white",
                command=self.open_user_management,
                **button_style
            )
            user_mgmt_btn.pack(pady=15)
        
        # Activity Log Button (Admin only)
        if AuthenticationService.is_admin(self.current_user):
            activity_log_btn = tk.Button(
                menu_frame,
                text="📋 Activity Log",
                bg="#8e44ad",
                fg="white",
                command=self.open_activity_log,
                **button_style
            )
            activity_log_btn.pack(pady=15)
        
        # Status bar
        status_frame = tk.Frame(self.root, bg="#34495e", height=30)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        status_frame.pack_propagate(False)
        
        status_label = tk.Label(
            status_frame,
            text="Ready | Tile Index - Inventory & Billing System",
            font=("Arial", 10),
            bg="#34495e",
            fg="white",
            anchor=tk.W
        )
        status_label.pack(side=tk.LEFT, padx=10, pady=5)
    
    def open_inventory(self):
        """Open inventory management window"""
        window = tk.Toplevel(self.root)
        InventoryWindow(window, self.current_user)
    
    def open_invoice(self):
        """Open invoice creation window"""
        window = tk.Toplevel(self.root)
        InvoiceWindow(window, self.current_user)
    
    def open_reports(self):
        """Open reports window (Admin only)"""
        if not AuthenticationService.can_view_reports(self.current_user):
            messagebox.showerror("Access Denied", "You do not have permission to view reports.")
            return
        window = tk.Toplevel(self.root)
        ReportWindow(window)
    
    def open_invoice_search(self):
        """Open invoice search window"""
        window = tk.Toplevel(self.root)
        InvoiceSearchWindow(window)
    
    def open_user_management(self):
        """Open user management window (Admin only)"""
        if not AuthenticationService.can_manage_users(self.current_user):
            messagebox.showerror("Access Denied", "You do not have permission to manage users.")
            return
        from ui.user_management_window import UserManagementWindow
        window = tk.Toplevel(self.root)
        UserManagementWindow(window, current_user=self.current_user)
    
    def open_activity_log(self):
        """Open activity log window (Admin only)"""
        if not AuthenticationService.can_manage_users(self.current_user):
            messagebox.showerror("Access Denied", "You do not have permission to view activity logs.")
            return
        from ui.activity_log_window import ActivityLogWindow
        window = tk.Toplevel(self.root)
        ActivityLogWindow(window)
    
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

