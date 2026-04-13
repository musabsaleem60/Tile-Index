"""
Activity Log model
Represents an audit log entry for user activities
"""

from datetime import datetime


class ActivityLog:
    """Activity Log model class"""
    
    def __init__(self, id=None, user_id=None, username=None, user_role=None,
                 branch_id=None, branch_name=None, action_type=None,
                 action_details=None, action_date=None, ip_address=None):
        self.id = id
        self.user_id = user_id
        self.username = username
        self.user_role = user_role  # 'admin' or 'employee'
        self.branch_id = branch_id
        self.branch_name = branch_name
        self.action_type = action_type  # e.g., 'Stock IN', 'Stock OUT', 'Invoice Created', etc.
        self.action_details = action_details  # JSON string or text with details
        self.action_date = action_date if action_date else datetime.now()
        self.ip_address = ip_address
    
    def __repr__(self):
        return f"ActivityLog(id={self.id}, user='{self.username}', action='{self.action_type}', date={self.action_date})"
    
    def to_dict(self):
        """Convert activity log to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.username,
            'user_role': self.user_role,
            'branch_id': self.branch_id,
            'branch_name': self.branch_name,
            'action_type': self.action_type,
            'action_details': self.action_details,
            'action_date': self.action_date,
            'ip_address': self.ip_address
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create activity log from dictionary"""
        return cls(
            id=data.get('id'),
            user_id=data.get('user_id'),
            username=data.get('username'),
            user_role=data.get('user_role'),
            branch_id=data.get('branch_id'),
            branch_name=data.get('branch_name'),
            action_type=data.get('action_type'),
            action_details=data.get('action_details'),
            action_date=data.get('action_date'),
            ip_address=data.get('ip_address')
        )

