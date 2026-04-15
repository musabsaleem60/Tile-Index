"""
Main Window
Main application window with navigation
"""

import tkinter as tk
from tkinter import ttk, messagebox
from ui.inventory_window import InventoryWindow
from ui.accessory_window import AccessoryWindow
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
        self.root.geometry("1400x850")
        self.root.state('zoomed')  # Maximize on Windows
        
        # Navigation stack
        self.view_stack = []
        
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
        
        # Main content area (Container for all views)
        self.content_frame = tk.Frame(self.root, bg="#ecf0f1")
        self.content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Setup Home Scrollable Container
        self.home_scroll_container = tk.Frame(self.content_frame, bg="#ecf0f1")
        
        home_canvas = tk.Canvas(self.home_scroll_container, bg="#ecf0f1", highlightthickness=0)
        home_scrollbar = ttk.Scrollbar(self.home_scroll_container, orient="vertical", command=home_canvas.yview)
        self.home_frame = tk.Frame(home_canvas, bg="#ecf0f1")
        
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
        tk.Label(
            self.home_frame, 
            text="Dashboard", 
            font=("Arial", 18, "bold"), 
            bg="#ecf0f1", 
            fg="#2c3e50"
        ).pack(pady=(20, 10))
        
        # Menu buttons container
        menu_container = tk.Frame(self.home_frame, bg="#ecf0f1")
        menu_container.pack(pady=20)
        
        # Button style
        button_style = {
            'font': ('Arial', 14, 'bold'),
            'width': 25,
            'height': 2,
            'cursor': 'hand2',
            'relief': tk.RAISED,
            'bd': 3
        }
        
        # Grid layout for buttons
        buttons = [
            ("📦 Inventory Management", "#3498db", self.open_inventory),
            ("🛠️ Accessories", "#8e44ad", self.open_accessories),
            ("🧾 Invoice & Billing", "#27ae60", self.open_invoice),
            ("🔍 Search Invoices", "#9b59b6", self.open_invoice_search)
        ]
        
        for i, (text, color, cmd) in enumerate(buttons):
            btn = tk.Button(menu_container, text=text, bg=color, fg="white", command=cmd, **button_style)
            btn.grid(row=i//2, column=i%2, padx=20, pady=15)
        
        # Admin Buttons
        if AuthenticationService.is_admin(self.current_user):
            admin_label = tk.Label(self.home_frame, text="Administration", font=("Arial", 16, "bold"), bg="#ecf0f1", fg="#c0392b")
            admin_label.pack(pady=(20, 10))
            
            admin_container = tk.Frame(self.home_frame, bg="#ecf0f1")
            admin_container.pack()
            
            admin_buttons = [
                ("📊 Reports", "#e67e22", self.open_reports),
                ("👥 User Management", "#16a085", self.open_user_management),
                ("📋 Activity Log", "#8e44ad", self.open_activity_log)
            ]
            
            for i, (text, color, cmd) in enumerate(admin_buttons):
                btn = tk.Button(admin_container, text=text, bg=color, fg="white", command=cmd, **button_style)
                btn.grid(row=0, column=i, padx=10, pady=10)
        
        # Back Button (Initially hidden)
        self.nav_bar = tk.Frame(self.content_frame, bg="#bdc3c7", height=40)
        tk.Button(
            self.nav_bar, 
            text="← Back to Dashboard", 
            command=self.show_home, 
            bg="#7f8c8d", 
            fg="white", 
            font=("Arial", 10, "bold"),
            padx=15
        ).pack(side=tk.LEFT, padx=10, pady=5)
        
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
        self.home_scroll_container.pack(fill=tk.BOTH, expand=True)
    
    def switch_view(self, view_class, *args, **kwargs):
        """Switch current view to a new frame-based view with scrolling support"""
        self.clear_content()
        self.nav_bar.pack(fill=tk.X, side=tk.TOP)
        
        # Create scrollable container
        container = tk.Frame(self.content_frame, bg="#ecf0f1")
        container.pack(fill=tk.BOTH, expand=True)
        
        canvas = tk.Canvas(container, bg="#ecf0f1", highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#ecf0f1")
        
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
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        # Bind to canvas and scrollable_frame, not 'all' to avoid focus issues
        def _bind_mousewheel(widget):
            widget.bind("<MouseWheel>", _on_mousewheel)
            for child in widget.winfo_children():
                _bind_mousewheel(child)
        
        _bind_mousewheel(canvas)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Initialize the view class into the scrollable frame
        view_class(scrollable_frame, *args, **kwargs)
    
    def open_inventory(self):
        """Open inventory management within the same window"""
        self.switch_view(InventoryWindow, self.current_user)
    
    def open_accessories(self):
        """Open accessories management within the same window"""
        self.switch_view(AccessoryWindow, self.current_user)
    
    def open_invoice(self):
        """Open invoice creation within the same window"""
        self.switch_view(InvoiceWindow, self.current_user)
    
    def open_reports(self):
        """Open reports within the same window (Admin only)"""
        if not AuthenticationService.can_view_reports(self.current_user):
            messagebox.showerror("Access Denied", "You do not have permission to view reports.")
            return
        self.switch_view(ReportWindow)
    
    def open_invoice_search(self):
        """Open invoice search within the same window"""
        self.switch_view(InvoiceSearchWindow)
    
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

