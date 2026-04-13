"""
Activity Log Service
Business logic for activity logging (audit trail)
"""

from repositories.activity_log_repository import ActivityLogRepository
from repositories.branch_repository import BranchRepository
from models.activity_log import ActivityLog
from datetime import datetime
import json


class ActivityLogService:
    """Service for activity logging"""
    
    # Action types
    ACTION_STOCK_IN = "Stock IN"
    ACTION_STOCK_OUT = "Stock OUT"
    ACTION_INVOICE_CREATED = "Invoice Created"
    ACTION_INVOICE_DELETED = "Invoice Deleted"
    ACTION_PRODUCT_ADDED = "Product Added"
    ACTION_PRODUCT_EDITED = "Product Edited"
    ACTION_PRODUCT_DELETED = "Product Deleted"
    ACTION_USER_CREATED = "User Created"
    ACTION_USER_EDITED = "User Edited"
    ACTION_USER_DEACTIVATED = "User Deactivated"
    ACTION_USER_ACTIVATED = "User Activated"
    ACTION_PASSWORD_CHANGED = "Password Changed"
    ACTION_LOGIN = "Login"
    ACTION_LOGOUT = "Logout"
    ACTION_INVENTORY_ADJUSTMENT = "Inventory Adjustment"
    
    @staticmethod
    def log_activity(user, action_type, action_details=None, branch_id=None, ip_address=None):
        """
        Log an activity
        
        Args:
            user: User object (must have id, username, role)
            action_type: Type of action (use constants from ActivityLogService)
            action_details: Details of the action (dict or string)
            branch_id: Branch ID if applicable
            ip_address: IP address if available
        """
        try:
            # Get branch name if branch_id provided
            branch_name = None
            if branch_id:
                branch = BranchRepository.get_by_id(branch_id)
                branch_name = branch.name if branch else None
            
            # Convert action_details to string if it's a dict
            details_str = action_details
            if isinstance(action_details, dict):
                details_str = json.dumps(action_details, indent=2)
            elif action_details is None:
                details_str = ""
            
            activity_log = ActivityLog(
                user_id=user.id,
                username=user.username,
                user_role=user.role,
                branch_id=branch_id,
                branch_name=branch_name,
                action_type=action_type,
                action_details=details_str,
                action_date=datetime.now(),
                ip_address=ip_address
            )
            
            ActivityLogRepository.create(activity_log)
        except Exception as e:
            # Don't let logging errors break the application
            # In production, you might want to log this to a file
            print(f"Failed to log activity: {e}")
    
    @staticmethod
    def log_stock_in(user, branch_id, product_name, grade, boxes, loose_pieces, notes=None):
        """Log Stock IN activity"""
        details = {
            'product': product_name,
            'grade': grade,
            'boxes': boxes,
            'loose_pieces': loose_pieces,
            'notes': notes or ''
        }
        ActivityLogService.log_activity(user, ActivityLogService.ACTION_STOCK_IN, details, branch_id)
    
    @staticmethod
    def log_stock_out(user, branch_id, product_name, grade, boxes, loose_pieces, reason=None):
        """Log Stock OUT activity"""
        details = {
            'product': product_name,
            'grade': grade,
            'boxes': boxes,
            'loose_pieces': loose_pieces,
            'reason': reason or ''
        }
        ActivityLogService.log_activity(user, ActivityLogService.ACTION_STOCK_OUT, details, branch_id)
    
    @staticmethod
    def log_invoice_created(user, branch_id, invoice_number, customer_name, total_amount):
        """Log Invoice Created activity"""
        details = {
            'invoice_number': invoice_number,
            'customer_name': customer_name,
            'total_amount': total_amount
        }
        ActivityLogService.log_activity(user, ActivityLogService.ACTION_INVOICE_CREATED, details, branch_id)
    
    @staticmethod
    def log_product_added(user, product_name, tile_size):
        """Log Product Added activity"""
        details = {
            'product_name': product_name,
            'tile_size': tile_size
        }
        ActivityLogService.log_activity(user, ActivityLogService.ACTION_PRODUCT_ADDED, details)
    
    @staticmethod
    def log_product_edited(user, product_name, tile_size):
        """Log Product Edited activity"""
        details = {
            'product_name': product_name,
            'tile_size': tile_size
        }
        ActivityLogService.log_activity(user, ActivityLogService.ACTION_PRODUCT_EDITED, details)
    
    @staticmethod
    def log_product_deleted(user, product_name, tile_size):
        """Log Product Deleted activity"""
        details = {
            'product_name': product_name,
            'tile_size': tile_size
        }
        ActivityLogService.log_activity(user, ActivityLogService.ACTION_PRODUCT_DELETED, details)
    
    @staticmethod
    def log_user_created(user, created_username, role):
        """Log User Created activity"""
        details = {
            'created_username': created_username,
            'role': role
        }
        ActivityLogService.log_activity(user, ActivityLogService.ACTION_USER_CREATED, details)
    
    @staticmethod
    def log_user_edited(user, edited_username):
        """Log User Edited activity"""
        details = {
            'edited_username': edited_username
        }
        ActivityLogService.log_activity(user, ActivityLogService.ACTION_USER_EDITED, details)
    
    @staticmethod
    def log_user_status_changed(user, target_username, is_active):
        """Log User Status Changed activity"""
        action = ActivityLogService.ACTION_USER_ACTIVATED if is_active else ActivityLogService.ACTION_USER_DEACTIVATED
        details = {
            'target_username': target_username,
            'status': 'activated' if is_active else 'deactivated'
        }
        ActivityLogService.log_activity(user, action, details)
    
    @staticmethod
    def log_password_changed(user, target_username):
        """Log Password Changed activity"""
        details = {
            'target_username': target_username
        }
        ActivityLogService.log_activity(user, ActivityLogService.ACTION_PASSWORD_CHANGED, details)
    
    @staticmethod
    def log_login(user, ip_address=None):
        """Log Login activity"""
        ActivityLogService.log_activity(user, ActivityLogService.ACTION_LOGIN, None, None, ip_address)
    
    @staticmethod
    def log_logout(user):
        """Log Logout activity"""
        ActivityLogService.log_activity(user, ActivityLogService.ACTION_LOGOUT)

