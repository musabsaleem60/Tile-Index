"""
Activity Log Window
Admin-only window for viewing user activity audit logs
"""

import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
from datetime import datetime, date
from repositories.activity_log_repository import ActivityLogRepository
from repositories.branch_repository import BranchRepository
from repositories.user_repository import UserRepository
from services.activity_log_service import ActivityLogService
from services.auth_service import AuthenticationService
from utils.datetime_format import format_business_datetime
from utils.activity_log_formatter import activity_reason, format_activity_details
from ui.theme import COLORS, FONTS, SIZES, SPACING


class ActivityLogWindow:
    """Activity Log window (Admin only)"""
    
    def __init__(self, parent):
        self.parent = parent
        
        self.branches = BranchRepository.get_all()
        self.users = UserRepository.get_all()
        
        self.setup_ui()
        # Load activities after UI is ready
        self.parent.after(100, self.load_all_activities)

    def set_window_title(self, title):
        """Update the containing window title when this view is not embedded."""
        try:
            window = self.parent.winfo_toplevel()
            if hasattr(window, "title"):
                window.title(title)
        except Exception:
            pass
    
    def setup_ui(self):
        """Setup the activity log UI"""
        header = ctk.CTkLabel(
            self.parent,
            text="Activity Log / Audit Trail",
            font=FONTS["section"],
            fg_color=COLORS["surface"],
            text_color=COLORS["text"],
            height=48,
        )
        header.pack(fill=tk.X)

        main_frame = ctk.CTkFrame(self.parent, fg_color=COLORS["app_bg"], corner_radius=0)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=SPACING["page_x"], pady=SPACING["page_y"])

        left_frame = self.panel(main_frame, "Filters")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 5))

        self.form_label(left_frame, "User:").grid(row=1, column=0, sticky=tk.W, pady=5, padx=(12, 8))
        self.user_var = tk.StringVar(value="All Users")
        user_combo = ttk.Combobox(left_frame, textvariable=self.user_var, width=SIZES["compact_dropdown_width"], state="readonly", font=FONTS["small"])
        user_combo['values'] = ["All Users"] + [f"{u.username} ({u.role})" for u in self.users]
        user_combo.grid(row=1, column=1, pady=5, padx=(0, 12), sticky=tk.W)

        self.form_label(left_frame, "Branch:").grid(row=2, column=0, sticky=tk.W, pady=5, padx=(12, 8))
        self.branch_var = tk.StringVar(value="All Branches")
        branch_combo = ttk.Combobox(left_frame, textvariable=self.branch_var, width=SIZES["compact_dropdown_width"], state="readonly", font=FONTS["small"])
        branch_combo['values'] = ["All Branches"] + [f"{b.name}" for b in self.branches]
        branch_combo.grid(row=2, column=1, pady=5, padx=(0, 12), sticky=tk.W)

        self.form_label(left_frame, "Action Type:").grid(row=3, column=0, sticky=tk.W, pady=5, padx=(12, 8))
        self.action_type_var = tk.StringVar(value="All Actions")
        action_combo = ttk.Combobox(left_frame, textvariable=self.action_type_var, width=SIZES["compact_dropdown_width"], state="readonly", font=FONTS["small"])
        action_types = [
            "All Actions",
            ActivityLogService.ACTION_STOCK_IN,
            ActivityLogService.ACTION_STOCK_OUT,
            "Accessory Stock IN",
            "Accessory Stock OUT",
            ActivityLogService.ACTION_INVOICE_CREATED,
            "Invoice Voided",
            "Cross-Branch Sale",
            ActivityLogService.ACTION_PRODUCT_ADDED,
            ActivityLogService.ACTION_PRODUCT_EDITED,
            ActivityLogService.ACTION_PRODUCT_DELETED,
            "Accessory Added",
            "Accessory Edited",
            "Accessory Deleted",
            ActivityLogService.ACTION_USER_CREATED,
            ActivityLogService.ACTION_USER_EDITED,
            ActivityLogService.ACTION_USER_DEACTIVATED,
            ActivityLogService.ACTION_USER_ACTIVATED,
            ActivityLogService.ACTION_PASSWORD_CHANGED,
            ActivityLogService.ACTION_LOGIN,
            ActivityLogService.ACTION_LOGOUT
        ]
        action_combo['values'] = action_types
        action_combo.grid(row=3, column=1, pady=5, padx=(0, 12), sticky=tk.W)

        self.form_label(left_frame, "Date From:").grid(row=4, column=0, sticky=tk.W, pady=5, padx=(12, 8))
        self.date_from_entry = self.form_entry(left_frame, width=210)
        self.date_from_entry.grid(row=4, column=1, pady=5, padx=(0, 12), sticky=tk.W)
        # Set default to first day of current month
        first_day = date.today().replace(day=1)
        self.date_from_entry.insert(0, first_day.strftime("%Y-%m-%d"))

        self.form_label(left_frame, "Date To:").grid(row=5, column=0, sticky=tk.W, pady=5, padx=(12, 8))
        self.date_to_entry = self.form_entry(left_frame, width=210)
        self.date_to_entry.grid(row=5, column=1, pady=5, padx=(0, 12), sticky=tk.W)
        self.date_to_entry.insert(0, date.today().strftime("%Y-%m-%d"))

        self.action_button(left_frame, "Search", self.search_activities, width=170).grid(row=6, column=0, columnspan=2, pady=(15, 5))
        self.action_button(left_frame, "Clear Filters", self.clear_filters, width=170, primary=False).grid(row=7, column=0, columnspan=2, pady=(5, 12))

        right_frame = self.panel(main_frame, "Activity Log")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        right_frame.grid_rowconfigure(1, weight=1)
        right_frame.grid_columnconfigure(0, weight=1)

        columns = ('Date/Time', 'User', 'Role', 'Branch', 'Action', 'Reason', 'Details')
        self.activities_tree = ttk.Treeview(right_frame, columns=columns, show='headings', height=25)

        column_widths = {
            'Date/Time': 150,
            'User': 120,
            'Role': 80,
            'Branch': 150,
            'Action': 150,
            'Reason': 180,
            'Details': 360,
        }
        for col in columns:
            self.activities_tree.heading(col, text=col)
            self.activities_tree.column(col, width=column_widths[col], anchor=tk.W)

        scrollbar = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=self.activities_tree.yview)
        xscrollbar = ttk.Scrollbar(right_frame, orient=tk.HORIZONTAL, command=self.activities_tree.xview)
        self.activities_tree.configure(yscrollcommand=scrollbar.set, xscrollcommand=xscrollbar.set)

        self.activities_tree.grid(row=1, column=0, sticky=tk.NSEW, padx=(12, 0), pady=(0, 0))
        scrollbar.grid(row=1, column=1, sticky=tk.NS, padx=(0, 12), pady=(0, 0))
        xscrollbar.grid(row=2, column=0, sticky=tk.EW, padx=(12, 0), pady=(0, 8))

        self.activities_tree.bind('<<TreeviewSelect>>', self.on_activity_select)

        details_frame = self.subpanel(right_frame, "Activity Details")
        details_frame.grid(row=3, column=0, columnspan=2, sticky=tk.EW, padx=12, pady=(0, 8))
        details_frame.grid_columnconfigure(0, weight=1)

        self.details_text = tk.Text(
            details_frame,
            height=5,
            font=("Consolas", 9),
            state=tk.DISABLED,
            wrap=tk.WORD,
            bg=COLORS["app_bg"],
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            selectbackground=COLORS["primary"],
            selectforeground=COLORS["text"],
            relief=tk.FLAT,
            borderwidth=0,
            padx=10,
            pady=8,
        )
        self.details_text.grid(row=1, column=0, sticky=tk.EW, padx=8, pady=(0, 8))

        self.action_button(right_frame, "Export Log", self.export_log, width=170).grid(row=4, column=0, columnspan=2, pady=(0, 12))

    def panel(self, parent, title):
        panel = ctk.CTkFrame(
            parent,
            fg_color=COLORS["surface"],
            corner_radius=SIZES["corner_radius"],
            border_width=1,
            border_color=COLORS["border"],
        )
        ctk.CTkLabel(
            panel,
            text=title,
            font=FONTS["body_bold"],
            text_color=COLORS["text"],
            height=SIZES["section_label_height"],
        ).grid(row=0, column=0, columnspan=2, sticky=tk.EW, padx=12, pady=(10, 8))
        return panel

    def subpanel(self, parent, title):
        panel = ctk.CTkFrame(
            parent,
            fg_color=COLORS["card"],
            corner_radius=SIZES["corner_radius"],
            border_width=1,
            border_color=COLORS["border"],
        )
        ctk.CTkLabel(
            panel,
            text=title,
            font=FONTS["small_bold"],
            text_color=COLORS["text"],
            height=SIZES["small_label_height"],
        ).grid(row=0, column=0, columnspan=2, sticky=tk.EW, padx=8, pady=(8, 4))
        return panel

    def form_label(self, parent, text):
        return ctk.CTkLabel(
            parent,
            text=text,
            font=FONTS["small"],
            text_color=COLORS["text"],
            height=SIZES["small_label_height"],
            anchor=tk.W,
        )

    def form_entry(self, parent, width=200):
        return ctk.CTkEntry(
            parent,
            width=width,
            height=SIZES["input_height"],
            font=FONTS["small"],
            fg_color=COLORS["app_bg"],
            border_color=COLORS["border"],
            text_color=COLORS["text"],
        )

    def action_button(self, parent, text, command, width=150, primary=True):
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
    
    def load_all_activities(self):
        """Load all activities without popup messages"""
        try:
            # Search with current filters but don't show popup
            user_str = self.user_var.get() if hasattr(self, 'user_var') else "All Users"
            user_id = None
            if user_str and user_str != "All Users":
                username = user_str.split(' (')[0]
                for user in self.users:
                    if user.username == username:
                        user_id = user.id
                        break
            
            branch_str = self.branch_var.get() if hasattr(self, 'branch_var') else "All Branches"
            branch_id = None
            if branch_str and branch_str != "All Branches":
                for branch in self.branches:
                    if branch.name == branch_str:
                        branch_id = branch.id
                        break
            
            action_type = None
            action_str = self.action_type_var.get() if hasattr(self, 'action_type_var') else "All Actions"
            if action_str and action_str != "All Actions":
                action_type = action_str
            
            date_from = self.date_from_entry.get().strip() if hasattr(self, 'date_from_entry') else None
            date_to = self.date_to_entry.get().strip() if hasattr(self, 'date_to_entry') else None
            
            # Search activities
            activities = ActivityLogRepository.search(
                user_id=user_id,
                action_type=action_type,
                branch_id=branch_id,
                date_from=date_from,
                date_to=date_to,
                limit=2000
            )
            
            # Clear existing items
            for item in self.activities_tree.get_children():
                self.activities_tree.delete(item)
            
            # Display activities
            for activity in activities:
                date_str = format_business_datetime(activity.action_date)
                
                branch_name = activity.branch_name or "N/A"
                details = format_activity_details(activity)
                details_one_line = " | ".join(details.splitlines())
                details_short = details_one_line[:80] + "..." if len(details_one_line) > 80 else details_one_line
                reason = activity_reason(activity)
                
                self.activities_tree.insert('', tk.END, values=(
                    date_str,
                    activity.username,
                    activity.user_role.upper(),
                    branch_name,
                    activity.action_type,
                    reason,
                    details_short
                ), tags=(activity.id,))
            
            # Update window title to show count
            count = len(activities)
            if count > 0:
                self.set_window_title(f"Activity Log - Tile Index ({count} entries)")
            else:
                self.set_window_title("Activity Log - Tile Index (No entries)")
        except Exception as e:
            # Show error only if it's a real problem
            import traceback
            print(f"Error loading activities: {e}")
            print(traceback.format_exc())
            messagebox.showerror("Error", f"Failed to load activities: {str(e)}")
    
    def search_activities(self):
        """Search activities with filters"""
        try:
            # Get filter values
            user_str = self.user_var.get()
            user_id = None
            if user_str and user_str != "All Users":
                username = user_str.split(' (')[0]
                for user in self.users:
                    if user.username == username:
                        user_id = user.id
                        break
            
            branch_str = self.branch_var.get()
            branch_id = None
            if branch_str and branch_str != "All Branches":
                for branch in self.branches:
                    if branch.name == branch_str:
                        branch_id = branch.id
                        break
            
            action_type = None
            action_str = self.action_type_var.get()
            if action_str and action_str != "All Actions":
                action_type = action_str
            
            date_from = self.date_from_entry.get().strip() or None
            date_to = self.date_to_entry.get().strip() or None
            
            # Validate date format (only if dates are provided)
            if date_from:
                try:
                    datetime.strptime(date_from, "%Y-%m-%d")
                except ValueError:
                    messagebox.showerror("Invalid Date", f"Date From format is invalid. Use YYYY-MM-DD format.\nCurrent value: {date_from}\nExample: 2026-01-22")
                    return
            
            if date_to:
                try:
                    datetime.strptime(date_to, "%Y-%m-%d")
                except ValueError:
                    messagebox.showerror("Invalid Date", f"Date To format is invalid. Use YYYY-MM-DD format.\nCurrent value: {date_to}\nExample: 2026-01-22")
                    return
            
            # Search activities
            activities = ActivityLogRepository.search(
                user_id=user_id,
                action_type=action_type,
                branch_id=branch_id,
                date_from=date_from,
                date_to=date_to,
                limit=2000
            )
            
            # Clear existing items
            for item in self.activities_tree.get_children():
                self.activities_tree.delete(item)
            
            # Display activities
            for activity in activities:
                date_str = format_business_datetime(activity.action_date)
                
                branch_name = activity.branch_name or "N/A"
                details = format_activity_details(activity)
                details_one_line = " | ".join(details.splitlines())
                details_short = details_one_line[:80] + "..." if len(details_one_line) > 80 else details_one_line
                reason = activity_reason(activity)
                
                self.activities_tree.insert('', tk.END, values=(
                    date_str,
                    activity.username,
                    activity.user_role.upper(),
                    branch_name,
                    activity.action_type,
                    reason,
                    details_short
                ), tags=(activity.id,))
            
            # Update window title to show count
            count = len(activities)
            if count > 0:
                self.set_window_title(f"Activity Log - Tile Index ({count} entries)")
            else:
                self.set_window_title("Activity Log - Tile Index (No entries)")
            
            # Show message only if filters are applied and no results
            if count == 0 and (user_id or branch_id or action_type or (date_from and date_to)):
                messagebox.showinfo("No Results", "No activity log entries found for the selected filters.\nTry clearing filters or adjusting date range.")
            
        except Exception as e:
            import traceback
            error_msg = str(e)
            print(f"Search error: {error_msg}")
            print(traceback.format_exc())
            messagebox.showerror("Error", f"Search failed: {error_msg}")
    
    def on_activity_select(self, event):
        """Handle activity selection to show full details"""
        selection = self.activities_tree.selection()
        if not selection:
            return
        
        item = self.activities_tree.item(selection[0])
        activity_id = item['tags'][0] if item['tags'] else None
        
        if not activity_id:
            return
        
        try:
            # Get full activity details
            activity = ActivityLogRepository.get_by_id(activity_id)
            
            if activity:
                self.details_text.config(state=tk.NORMAL)
                self.details_text.delete(1.0, tk.END)
                
                self.details_text.insert(tk.END, f"Activity ID: {activity.id}\n")
                self.details_text.insert(tk.END, f"User: {activity.username} ({activity.user_role})\n")
                self.details_text.insert(tk.END, f"Date/Time: {format_business_datetime(activity.action_date)}\n")
                self.details_text.insert(tk.END, f"Branch: {activity.branch_name or 'N/A'}\n")
                self.details_text.insert(tk.END, f"Action: {activity.action_type}\n\n")
                self.details_text.insert(tk.END, "Details:\n")
                self.details_text.insert(tk.END, format_activity_details(activity) or "No additional details")
                
                self.details_text.config(state=tk.DISABLED)
        except Exception as e:
            self.details_text.config(state=tk.NORMAL)
            self.details_text.delete(1.0, tk.END)
            self.details_text.insert(tk.END, f"Error loading details: {str(e)}")
            self.details_text.config(state=tk.DISABLED)
    
    def clear_filters(self):
        """Clear all filters"""
        self.user_var.set("All Users")
        self.branch_var.set("All Branches")
        self.action_type_var.set("All Actions")
        self.date_from_entry.delete(0, tk.END)
        self.date_from_entry.insert(0, (date.today() - date.today().replace(day=1)).strftime("%Y-%m-%d") if date.today().day > 1 else date.today().replace(day=1).strftime("%Y-%m-%d"))
        self.date_to_entry.delete(0, tk.END)
        self.date_to_entry.insert(0, date.today().strftime("%Y-%m-%d"))
        self.load_all_activities()
    
    def export_log(self):
        """Export activity log to file"""
        try:
            from tkinter import filedialog
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                title="Save Activity Log"
            )
            
            if not filename:
                return
            
            # Get all displayed activities
            activities = []
            for item_id in self.activities_tree.get_children():
                item = self.activities_tree.item(item_id)
                activities.append(item['values'])
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("=" * 100 + "\n")
                f.write("TILE INDEX - ACTIVITY LOG / AUDIT TRAIL\n")
                f.write("=" * 100 + "\n\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(f"{'Date/Time':<20} {'User':<15} {'Role':<10} {'Branch':<20} {'Action':<20} {'Reason':<25} {'Details':<30}\n")
                f.write("-" * 100 + "\n")
                
                for activity in activities:
                    f.write(f"{activity[0]:<20} {activity[1]:<15} {activity[2]:<10} {activity[3]:<20} {activity[4]:<20} {activity[5]:<25} {activity[6]:<30}\n")
            
            messagebox.showinfo("Success", f"Activity log exported to:\n{filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export log: {str(e)}")

