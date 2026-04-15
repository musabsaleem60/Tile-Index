"""
User Management Window
Admin-only window for managing users
"""

import tkinter as tk
from tkinter import ttk, messagebox
from repositories.user_repository import UserRepository
from repositories.branch_repository import BranchRepository
from models.user import User
from services.auth_service import AuthenticationService


class UserManagementWindow:
    """User management window (Admin only)"""
    
    def __init__(self, parent, current_user=None):
        self.parent = parent
        self.current_user = current_user  # Admin user managing others
        
        self.branches = BranchRepository.get_all()
        self.users = UserRepository.get_all()
        self.editing_user_id = None
        
        self.setup_ui()
        self.load_users()
    
    def setup_ui(self):
        """Setup the user management UI"""
        # Header
        header = tk.Label(
            self.parent,
            text="User Management",
            font=("Arial", 18, "bold"),
            bg="#16a085",
            fg="white",
            pady=10
        )
        header.pack(fill=tk.X)
        
        # Main container
        main_frame = tk.Frame(self.parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel - User Form
        left_frame = tk.LabelFrame(main_frame, text="Add/Edit User", font=("Arial", 12, "bold"), padx=10, pady=10)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 5))
        
        # Username
        tk.Label(left_frame, text="Username:", font=("Arial", 10)).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.username_entry = tk.Entry(left_frame, width=25, font=("Arial", 10))
        self.username_entry.grid(row=0, column=1, pady=5, padx=5)
        
        # Password
        tk.Label(left_frame, text="Password:", font=("Arial", 10)).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.password_entry = tk.Entry(left_frame, width=25, font=("Arial", 10), show="*")
        self.password_entry.grid(row=1, column=1, pady=5, padx=5)
        tk.Label(left_frame, text="(Leave blank to keep current)", font=("Arial", 8), fg="gray").grid(row=2, column=1, sticky=tk.W, padx=5)
        
        # Role
        tk.Label(left_frame, text="Role:", font=("Arial", 10)).grid(row=3, column=0, sticky=tk.W, pady=5)
        self.role_var = tk.StringVar(value="employee")
        role_combo = ttk.Combobox(left_frame, textvariable=self.role_var, width=22, state="readonly", font=("Arial", 10))
        role_combo['values'] = ['admin', 'employee']
        role_combo.grid(row=3, column=1, pady=5, padx=5, sticky=tk.W)
        role_combo.bind('<<ComboboxSelected>>', self.on_role_change)
        
        # Branch (for employees)
        tk.Label(left_frame, text="Branch:", font=("Arial", 10)).grid(row=4, column=0, sticky=tk.W, pady=5)
        self.branch_var = tk.StringVar()
        self.branch_combo = ttk.Combobox(left_frame, textvariable=self.branch_var, width=22, state="readonly", font=("Arial", 10))
        self.branch_combo['values'] = [f"{b.name}" for b in self.branches]
        self.branch_combo.grid(row=4, column=1, pady=5, padx=5, sticky=tk.W)
        self.on_role_change()  # Initialize branch visibility
        
        # Active status
        self.is_active_var = tk.BooleanVar(value=True)
        tk.Checkbutton(left_frame, text="Active", variable=self.is_active_var, font=("Arial", 10)).grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=5, padx=5)
        
        # Buttons
        btn_frame = tk.Frame(left_frame)
        btn_frame.grid(row=6, column=0, columnspan=2, pady=15)
        
        self.add_update_btn = tk.Button(btn_frame, text="Add User", command=self.add_or_update_user, bg="#3498db", fg="white", width=15)
        self.add_update_btn.pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Clear", command=self.clear_form, bg="#95a5a6", fg="white", width=15).pack(side=tk.LEFT, padx=5)
        
        # Right panel - Users List
        right_frame = tk.LabelFrame(main_frame, text="Users List", font=("Arial", 12, "bold"), padx=10, pady=10)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # Treeview
        columns = ('Username', 'Role', 'Branch', 'Status')
        self.users_tree = ttk.Treeview(right_frame, columns=columns, show='headings', height=20)
        
        for col in columns:
            self.users_tree.heading(col, text=col)
            self.users_tree.column(col, width=150, anchor=tk.CENTER)
        
        scrollbar = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=self.users_tree.yview)
        self.users_tree.configure(yscrollcommand=scrollbar.set)
        
        self.users_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.users_tree.bind('<<TreeviewSelect>>', self.on_user_select)
        
        # Action buttons
        action_frame = tk.Frame(right_frame)
        action_frame.pack(pady=5)
        
        tk.Button(action_frame, text="Edit User", command=self.edit_selected_user, bg="#f39c12", fg="white", width=15).pack(side=tk.LEFT, padx=5)
        tk.Button(action_frame, text="Deactivate/Activate", command=self.toggle_user_status, bg="#e67e22", fg="white", width=18).pack(side=tk.LEFT, padx=5)
        tk.Button(action_frame, text="Change Password", command=self.change_password, bg="#9b59b6", fg="white", width=15).pack(side=tk.LEFT, padx=5)
    
    def on_role_change(self, event=None):
        """Show/hide branch selection based on role"""
        if self.role_var.get() == 'employee':
            self.branch_combo.grid()
        else:
            self.branch_combo.grid_remove()
    
    def load_users(self):
        """Load users into treeview"""
        self.users = UserRepository.get_all()
        
        # Clear existing items
        for item in self.users_tree.get_children():
            self.users_tree.delete(item)
        
        branch_dict = {b.id: b.name for b in self.branches}
        
        for user in self.users:
            branch_name = branch_dict.get(user.branch_id, "All Branches") if user.branch_id else "All Branches"
            status = "Active" if user.is_active else "Inactive"
            
            item_id = self.users_tree.insert('', tk.END, values=(
                user.username,
                user.role.upper(),
                branch_name,
                status
            ), tags=(user.id,))
    
    def on_user_select(self, event):
        """Handle user selection"""
        pass
    
    def add_or_update_user(self):
        """Add or update user"""
        try:
            username = self.username_entry.get().strip()
            if not username:
                raise ValueError("Username is required")
            
            role = self.role_var.get()
            is_active = self.is_active_var.get()
            
            # Get branch for employees
            branch_id = None
            if role == 'employee':
                branch_name = self.branch_var.get()
                if not branch_name:
                    raise ValueError("Branch is required for employees")
                for branch in self.branches:
                    if branch.name == branch_name:
                        branch_id = branch.id
                        break
                if not branch_id:
                    raise ValueError("Invalid branch selected")
            
            password = self.password_entry.get()
            
            if self.editing_user_id:
                # Update existing user
                user = UserRepository.get_by_id(self.editing_user_id)
                if not user:
                    raise ValueError("User not found")
                
                user.username = username
                user.role = role
                user.branch_id = branch_id
                user.is_active = is_active
                
                # Update password if provided
                if password:
                    user.password_hash = password
                
                UserRepository.update(user, updated_by_user=self.current_user)
                messagebox.showinfo("Success", f"User '{username}' updated successfully!")
            else:
                # Create new user
                if not password:
                    raise ValueError("Password is required for new users")
                
                user = User(
                    username=username,
                    password_hash=password,
                    role=role,
                    branch_id=branch_id,
                    is_active=is_active
                )
                
                UserRepository.create(user, created_by_user=self.current_user)
                messagebox.showinfo("Success", f"User '{username}' created successfully!")
            
            self.clear_form()
            self.load_users()
            
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def edit_selected_user(self):
        """Edit selected user"""
        selection = self.users_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a user to edit")
            return
        
        item = self.users_tree.item(selection[0])
        user_id = item['tags'][0] if item['tags'] else None
        
        if not user_id:
            messagebox.showerror("Error", "Could not retrieve user ID")
            return
        
        try:
            user = UserRepository.get_by_id(user_id)
            if not user:
                raise ValueError("User not found")
            
            # Load user data into form
            self.username_entry.delete(0, tk.END)
            self.username_entry.insert(0, user.username)
            
            self.password_entry.delete(0, tk.END)
            
            self.role_var.set(user.role)
            self.on_role_change()
            
            if user.branch_id:
                for branch in self.branches:
                    if branch.id == user.branch_id:
                        self.branch_var.set(branch.name)
                        break
            
            self.is_active_var.set(user.is_active)
            
            self.editing_user_id = user.id
            self.add_update_btn.config(text="Update User", bg="#f39c12")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load user: {str(e)}")
    
    def toggle_user_status(self):
        """Toggle user active/inactive status"""
        selection = self.users_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a user")
            return
        
        item = self.users_tree.item(selection[0])
        user_id = item['tags'][0] if item['tags'] else None
        
        if not user_id:
            messagebox.showerror("Error", "Could not retrieve user ID")
            return
        
        try:
            user = UserRepository.get_by_id(user_id)
            if not user:
                raise ValueError("User not found")
            
            new_status = not user.is_active
            user.is_active = new_status
            UserRepository.update(user, updated_by_user=self.current_user)
            
            status_text = "activated" if new_status else "deactivated"
            messagebox.showinfo("Success", f"User '{user.username}' has been {status_text}")
            self.load_users()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update user: {str(e)}")
    
    def change_password(self):
        """Change user password"""
        selection = self.users_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a user")
            return
        
        item = self.users_tree.item(selection[0])
        user_id = item['tags'][0] if item['tags'] else None
        
        if not user_id:
            messagebox.showerror("Error", "Could not retrieve user ID")
            return
        
        # Create password dialog
        dialog = tk.Toplevel(self.parent)
        dialog.title("Change Password")
        dialog.geometry("350x150")
        dialog.resizable(False, False)
        
        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (175)
        y = (dialog.winfo_screenheight() // 2) - (75)
        dialog.geometry(f'350x150+{x}+{y}')
        
        tk.Label(dialog, text="New Password:", font=("Arial", 10)).pack(pady=10)
        password_entry = tk.Entry(dialog, width=30, font=("Arial", 10), show="*")
        password_entry.pack(pady=5)
        password_entry.focus()
        
        tk.Label(dialog, text="Confirm Password:", font=("Arial", 10)).pack(pady=5)
        confirm_entry = tk.Entry(dialog, width=30, font=("Arial", 10), show="*")
        confirm_entry.pack(pady=5)
        
        def save_password():
            new_password = password_entry.get()
            confirm = confirm_entry.get()
            
            if not new_password:
                messagebox.showerror("Error", "Password cannot be empty")
                return
            
            if new_password != confirm:
                messagebox.showerror("Error", "Passwords do not match")
                return
            
            try:
                # Get current user from parent window or use a default
                from services.auth_service import AuthenticationService
                admin_user = self.current_user
                if not admin_user:
                    # Try to get from main window if available
                    admin_user = getattr(self.parent, 'current_user', None)
                
                UserRepository.update_password(user_id, new_password, changed_by_user=admin_user)
                messagebox.showinfo("Success", "Password changed successfully!")
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to change password: {str(e)}")
        
        tk.Button(dialog, text="Change Password", command=save_password, bg="#3498db", fg="white", width=20).pack(pady=10)
        confirm_entry.bind('<Return>', lambda e: save_password())
    
    def clear_form(self):
        """Clear user form"""
        self.username_entry.delete(0, tk.END)
        self.password_entry.delete(0, tk.END)
        self.role_var.set("employee")
        self.branch_var.set("")
        self.is_active_var.set(True)
        self.editing_user_id = None
        self.add_update_btn.config(text="Add User", bg="#3498db")
        self.on_role_change()

