"""
Tile Index - Inventory & Billing System
Main entry point for the application
"""

import tkinter as tk
from ui.login_window import LoginWindow
from ui.main_window import MainWindow


def on_login_success(user):
    """Callback when user successfully logs in"""
    root = tk.Tk()
    app = MainWindow(root, user)
    root.mainloop()


def main():
    """Main function to start the application"""
    # Initialize database first
    try:
        from database.init_db import init_database
        init_database()
    except Exception as e:
        import tkinter.messagebox as messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Database Error", f"Failed to initialize database: {str(e)}")
        return
    
    # Show login window
    login_root = tk.Tk()
    login_app = LoginWindow(login_root, on_login_success)
    login_root.mainloop()


if __name__ == "__main__":
    main()

