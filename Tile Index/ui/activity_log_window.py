"""
Activity Log Window
Admin-only window for viewing user activity audit logs
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date
from repositories.activity_log_repository import ActivityLogRepository
from repositories.branch_repository import BranchRepository
from repositories.user_repository import UserRepository
from services.activity_log_service import ActivityLogService
from services.auth_service import AuthenticationService


class ActivityLogWindow:
    """Activity Log window (Admin only)"""
    
    def __init__(self, parent):
        self.parent = parent
        
        self.branches = BranchRepository.get_all()
        self.users = UserRepository.get_all()
        
        self.setup_ui()
        # Load activities after UI is ready
        self.parent.after(100, self.load_all_activities)
    
    def setup_ui(self):
        """Setup the activity log UI"""
        # Header
        header = tk.Label(
            self.parent,
            text="Activity Log / Audit Trail",
            font=("Arial", 18, "bold"),
            bg="#8e44ad",
            fg="white",
            pady=10
        )
        header.pack(fill=tk.X)
        
        # Main container
        main_frame = tk.Frame(self.parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel - Filters
        left_frame = tk.LabelFrame(main_frame, text="Filters", font=("Arial", 12, "bold"), padx=10, pady=10)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 5))
        
        # User filter
        tk.Label(left_frame, text="User:", font=("Arial", 10)).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.user_var = tk.StringVar(value="All Users")
        user_combo = ttk.Combobox(left_frame, textvariable=self.user_var, width=25, state="readonly", font=("Arial", 10))
        user_combo['values'] = ["All Users"] + [f"{u.username} ({u.role})" for u in self.users]
        user_combo.grid(row=0, column=1, pady=5, padx=5, sticky=tk.W)
        
        # Branch filter
        tk.Label(left_frame, text="Branch:", font=("Arial", 10)).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.branch_var = tk.StringVar(value="All Branches")
        branch_combo = ttk.Combobox(left_frame, textvariable=self.branch_var, width=25, state="readonly", font=("Arial", 10))
        branch_combo['values'] = ["All Branches"] + [f"{b.name}" for b in self.branches]
        branch_combo.grid(row=1, column=1, pady=5, padx=5, sticky=tk.W)
        
        # Action type filter
        tk.Label(left_frame, text="Action Type:", font=("Arial", 10)).grid(row=2, column=0, sticky=tk.W, pady=5)
        self.action_type_var = tk.StringVar(value="All Actions")
        action_combo = ttk.Combobox(left_frame, textvariable=self.action_type_var, width=25, state="readonly", font=("Arial", 10))
        action_types = [
            "All Actions",
            ActivityLogService.ACTION_STOCK_IN,
            ActivityLogService.ACTION_STOCK_OUT,
            ActivityLogService.ACTION_INVOICE_CREATED,
            ActivityLogService.ACTION_PRODUCT_ADDED,
            ActivityLogService.ACTION_PRODUCT_EDITED,
            ActivityLogService.ACTION_PRODUCT_DELETED,
            ActivityLogService.ACTION_USER_CREATED,
            ActivityLogService.ACTION_USER_EDITED,
            ActivityLogService.ACTION_USER_DEACTIVATED,
            ActivityLogService.ACTION_USER_ACTIVATED,
            ActivityLogService.ACTION_PASSWORD_CHANGED,
            ActivityLogService.ACTION_LOGIN,
            ActivityLogService.ACTION_LOGOUT
        ]
        action_combo['values'] = action_types
        action_combo.grid(row=2, column=1, pady=5, padx=5, sticky=tk.W)
        
        # Date from
        tk.Label(left_frame, text="Date From:", font=("Arial", 10)).grid(row=3, column=0, sticky=tk.W, pady=5)
        self.date_from_entry = tk.Entry(left_frame, width=25, font=("Arial", 10))
        self.date_from_entry.grid(row=3, column=1, pady=5, padx=5)
        # Set default to first day of current month
        first_day = date.today().replace(day=1)
        self.date_from_entry.insert(0, first_day.strftime("%Y-%m-%d"))
        
        # Date to
        tk.Label(left_frame, text="Date To:", font=("Arial", 10)).grid(row=4, column=0, sticky=tk.W, pady=5)
        self.date_to_entry = tk.Entry(left_frame, width=25, font=("Arial", 10))
        self.date_to_entry.grid(row=4, column=1, pady=5, padx=5)
        self.date_to_entry.insert(0, date.today().strftime("%Y-%m-%d"))
        
        # Search button
        tk.Button(left_frame, text="Search", command=self.search_activities, bg="#3498db", fg="white", width=20, font=("Arial", 10, "bold")).grid(row=5, column=0, columnspan=2, pady=15)
        
        # Clear filters button
        tk.Button(left_frame, text="Clear Filters", command=self.clear_filters, bg="#95a5a6", fg="white", width=20).grid(row=6, column=0, columnspan=2, pady=5)
        
        # Right panel - Activity Log Display
        right_frame = tk.LabelFrame(main_frame, text="Activity Log", font=("Arial", 12, "bold"), padx=10, pady=10)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # Treeview for activities
        columns = ('Date/Time', 'User', 'Role', 'Branch', 'Action', 'Details')
        self.activities_tree = ttk.Treeview(right_frame, columns=columns, show='headings', height=25)
        
        for col in columns:
            self.activities_tree.heading(col, text=col)
            self.activities_tree.column(col, width=150, anchor=tk.W)
        
        self.activities_tree.column('Date/Time', width=150)
        self.activities_tree.column('User', width=120)
        self.activities_tree.column('Role', width=80)
        self.activities_tree.column('Branch', width=150)
        self.activities_tree.column('Action', width=150)
        self.activities_tree.column('Details', width=300)
        
        scrollbar = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=self.activities_tree.yview)
        self.activities_tree.configure(yscrollcommand=scrollbar.set)
        
        self.activities_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.activities_tree.bind('<<TreeviewSelect>>', self.on_activity_select)
        
        # Details text area
        details_frame = tk.LabelFrame(right_frame, text="Activity Details", font=("Arial", 10, "bold"), padx=5, pady=5)
        details_frame.pack(fill=tk.X, pady=5)
        
        self.details_text = tk.Text(details_frame, height=5, font=("Courier", 9), state=tk.DISABLED, wrap=tk.WORD)
        self.details_text.pack(fill=tk.BOTH, expand=True)
        
        # Export button
        tk.Button(right_frame, text="Export Log", command=self.export_log, bg="#27ae60", fg="white", width=20).pack(pady=5)
    
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
                action_date = activity.action_date
                if isinstance(action_date, str):
                    date_str = action_date[:19] if len(action_date) >= 19 else action_date
                else:
                    try:
                        date_str = activity.action_date.strftime("%Y-%m-%d %H:%M:%S")
                    except:
                        date_str = str(action_date)[:19]
                
                branch_name = activity.branch_name or "N/A"
                details_short = activity.action_details[:50] + "..." if activity.action_details and len(activity.action_details) > 50 else (activity.action_details or "")
                
                self.activities_tree.insert('', tk.END, values=(
                    date_str,
                    activity.username,
                    activity.user_role.upper(),
                    branch_name,
                    activity.action_type,
                    details_short
                ), tags=(activity.id,))
            
            # Update window title to show count
            count = len(activities)
            if count > 0:
                self.parent.title(f"Activity Log - Tile Index ({count} entries)")
            else:
                self.parent.title("Activity Log - Tile Index (No entries)")
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
                action_date = activity.action_date
                if isinstance(action_date, str):
                    date_str = action_date[:19] if len(action_date) >= 19 else action_date
                else:
                    try:
                        date_str = activity.action_date.strftime("%Y-%m-%d %H:%M:%S")
                    except:
                        date_str = str(action_date)[:19]
                
                branch_name = activity.branch_name or "N/A"
                details_short = activity.action_details[:50] + "..." if activity.action_details and len(activity.action_details) > 50 else (activity.action_details or "")
                
                self.activities_tree.insert('', tk.END, values=(
                    date_str,
                    activity.username,
                    activity.user_role.upper(),
                    branch_name,
                    activity.action_type,
                    details_short
                ), tags=(activity.id,))
            
            # Update window title to show count
            count = len(activities)
            if count > 0:
                self.parent.title(f"Activity Log - Tile Index ({count} entries)")
            else:
                self.parent.title("Activity Log - Tile Index (No entries)")
            
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
                self.details_text.insert(tk.END, f"Date/Time: {activity.action_date}\n")
                self.details_text.insert(tk.END, f"Branch: {activity.branch_name or 'N/A'}\n")
                self.details_text.insert(tk.END, f"Action: {activity.action_type}\n\n")
                self.details_text.insert(tk.END, "Details:\n")
                self.details_text.insert(tk.END, activity.action_details or "No additional details")
                
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
                f.write(f"{'Date/Time':<20} {'User':<15} {'Role':<10} {'Branch':<20} {'Action':<20} {'Details':<30}\n")
                f.write("-" * 100 + "\n")
                
                for activity in activities:
                    f.write(f"{activity[0]:<20} {activity[1]:<15} {activity[2]:<10} {activity[3]:<20} {activity[4]:<20} {activity[5]:<30}\n")
            
            messagebox.showinfo("Success", f"Activity log exported to:\n{filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export log: {str(e)}")

