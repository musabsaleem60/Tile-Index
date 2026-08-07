"""
User Management Window
Admin-only window for managing users
"""

import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
from repositories.user_repository import UserRepository
from repositories.branch_repository import BranchRepository
from models.user import User
from services.auth_service import AuthenticationService
from ui.theme import COLORS, FONTS, SIZES, SPACING


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
        header = ctk.CTkLabel(
            self.parent,
            text="User Management",
            font=FONTS["section"],
            fg_color=COLORS["surface"],
            text_color=COLORS["text"],
            height=48,
        )
        header.pack(fill=tk.X)

        main_frame = ctk.CTkFrame(self.parent, fg_color=COLORS["app_bg"], corner_radius=0)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=SPACING["page_x"], pady=SPACING["page_y"])

        left_frame = self.panel(main_frame, "Add/Edit User")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 5))

        self.form_label(left_frame, "Username:").grid(row=1, column=0, sticky=tk.W, pady=5, padx=(12, 8))
        self.username_entry = self.form_entry(left_frame, width=230)
        self.username_entry.grid(row=1, column=1, pady=5, padx=(0, 12), sticky=tk.W)

        self.form_label(left_frame, "Password:").grid(row=2, column=0, sticky=tk.W, pady=5, padx=(12, 8))
        self.password_entry = self.form_entry(left_frame, width=230, show="*")
        self.password_entry.grid(row=2, column=1, pady=5, padx=(0, 12), sticky=tk.W)
        ctk.CTkLabel(
            left_frame,
            text="(Leave blank to keep current)",
            font=FONTS["status"],
            text_color=COLORS["text_muted"],
            height=SIZES["small_label_height"],
        ).grid(row=3, column=1, sticky=tk.W, padx=(0, 12))

        self.form_label(left_frame, "Role:").grid(row=4, column=0, sticky=tk.W, pady=5, padx=(12, 8))
        self.role_var = tk.StringVar(value="employee")
        role_combo = ttk.Combobox(left_frame, textvariable=self.role_var, width=SIZES["compact_dropdown_width"], state="readonly", font=FONTS["small"])
        role_combo['values'] = ['admin', 'employee']
        role_combo.grid(row=4, column=1, pady=5, padx=(0, 12), sticky=tk.W)
        role_combo.bind('<<ComboboxSelected>>', self.on_role_change)

        self.form_label(left_frame, "Branch:").grid(row=5, column=0, sticky=tk.W, pady=5, padx=(12, 8))
        self.branch_var = tk.StringVar()
        self.branch_combo = ttk.Combobox(left_frame, textvariable=self.branch_var, width=SIZES["compact_dropdown_width"], state="readonly", font=FONTS["small"])
        self.branch_combo['values'] = [f"{b.name}" for b in self.branches]
        self.branch_combo.grid(row=5, column=1, pady=5, padx=(0, 12), sticky=tk.W)
        self.on_role_change()  # Initialize branch visibility

        self.is_active_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            left_frame,
            text="Active",
            variable=self.is_active_var,
            font=FONTS["small"],
            text_color=COLORS["text"],
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            border_color=COLORS["border"],
        ).grid(row=6, column=0, columnspan=2, sticky=tk.W, pady=8, padx=12)

        btn_frame = ctk.CTkFrame(left_frame, fg_color="transparent", corner_radius=0)
        btn_frame.grid(row=7, column=0, columnspan=2, pady=15)

        self.add_update_btn = self.action_button(btn_frame, "Add User", self.add_or_update_user, width=130)
        self.add_update_btn.pack(side=tk.LEFT, padx=5)
        self.action_button(btn_frame, "Clear", self.clear_form, width=120, primary=False).pack(side=tk.LEFT, padx=5)

        right_frame = self.panel(main_frame, "Users List")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        right_frame.grid_rowconfigure(1, weight=1)
        right_frame.grid_columnconfigure(0, weight=1)

        columns = ('Username', 'Role', 'Branch', 'Status')
        self.users_tree = ttk.Treeview(right_frame, columns=columns, show='headings', height=20)

        column_widths = {
            'Username': 180,
            'Role': 120,
            'Branch': 220,
            'Status': 120,
        }
        for col in columns:
            self.users_tree.heading(col, text=col)
            self.users_tree.column(col, width=column_widths[col], anchor=tk.CENTER)

        scrollbar = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=self.users_tree.yview)
        self.users_tree.configure(yscrollcommand=scrollbar.set)

        self.users_tree.grid(row=1, column=0, sticky=tk.NSEW, padx=(12, 0), pady=(0, 8))
        scrollbar.grid(row=1, column=1, sticky=tk.NS, padx=(0, 12), pady=(0, 8))

        self.users_tree.bind('<<TreeviewSelect>>', self.on_user_select)

        action_frame = ctk.CTkFrame(right_frame, fg_color="transparent", corner_radius=0)
        action_frame.grid(row=2, column=0, columnspan=2, pady=(4, 12))

        self.action_button(action_frame, "Edit User", self.edit_selected_user, width=130).pack(side=tk.LEFT, padx=5)
        self.action_button(action_frame, "Deactivate/Activate", self.toggle_user_status, width=180, warning=True).pack(side=tk.LEFT, padx=5)
        self.action_button(action_frame, "Change Password", self.change_password, width=160).pack(side=tk.LEFT, padx=5)

        left_frame.grid_columnconfigure(1, weight=1)

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

    def form_label(self, parent, text):
        return ctk.CTkLabel(
            parent,
            text=text,
            font=FONTS["small"],
            text_color=COLORS["text"],
            height=SIZES["small_label_height"],
            anchor=tk.W,
        )

    def form_entry(self, parent, width=220, show=None):
        return ctk.CTkEntry(
            parent,
            width=width,
            height=SIZES["input_height"],
            font=FONTS["small"],
            fg_color=COLORS["app_bg"],
            border_color=COLORS["border"],
            text_color=COLORS["text"],
            show=show,
        )

    def action_button(self, parent, text, command, width=140, primary=True, warning=False):
        if warning:
            fg_color = COLORS["warning"]
            hover_color = COLORS["warning_hover"]
        elif primary:
            fg_color = COLORS["primary"]
            hover_color = COLORS["primary_hover"]
        else:
            fg_color = COLORS["card"]
            hover_color = COLORS["card_hover"]
        return ctk.CTkButton(
            parent,
            text=text,
            command=command,
            width=width,
            height=34,
            fg_color=fg_color,
            hover_color=hover_color,
            text_color=COLORS["text"],
            font=FONTS["small_bold"],
            border_width=0 if primary or warning else 1,
            border_color=COLORS["border"],
            corner_radius=SIZES["corner_radius"],
            cursor="hand2",
        )
    
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
            self.add_update_btn.configure(text="Update User", fg_color=COLORS["warning"], hover_color=COLORS["warning_hover"])
            
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
        dialog = ctk.CTkToplevel(self.parent)
        dialog.title("Change Password")
        dialog.geometry("350x150")
        dialog.resizable(False, False)
        dialog.configure(fg_color=COLORS["app_bg"])
        
        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (175)
        y = (dialog.winfo_screenheight() // 2) - (75)
        dialog.geometry(f'350x150+{x}+{y}')
        
        ctk.CTkLabel(
            dialog,
            text="New Password:",
            font=FONTS["small_bold"],
            text_color=COLORS["text"],
            height=SIZES["small_label_height"],
        ).pack(pady=(12, 4))
        password_entry = self.form_entry(dialog, width=260, show="*")
        password_entry.pack(pady=4)
        password_entry.focus()

        ctk.CTkLabel(
            dialog,
            text="Confirm Password:",
            font=FONTS["small_bold"],
            text_color=COLORS["text"],
            height=SIZES["small_label_height"],
        ).pack(pady=(6, 4))
        confirm_entry = self.form_entry(dialog, width=260, show="*")
        confirm_entry.pack(pady=4)
        
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
        
        self.action_button(dialog, "Change Password", save_password, width=180).pack(pady=10)
        confirm_entry.bind('<Return>', lambda e: save_password())
    
    def clear_form(self):
        """Clear user form"""
        self.username_entry.delete(0, tk.END)
        self.password_entry.delete(0, tk.END)
        self.role_var.set("employee")
        self.branch_var.set("")
        self.is_active_var.set(True)
        self.editing_user_id = None
        self.add_update_btn.configure(text="Add User", fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"])
        self.on_role_change()

