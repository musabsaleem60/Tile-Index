"""
User model
Represents a system user (admin or employee)
"""


class User:
    """User model class"""
    
    def __init__(self, id=None, username=None, password_hash=None, role=None,
                 branch_id=None, is_active=True, created_at=None):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.role = role  # 'admin' or 'employee'
        self.branch_id = branch_id  # For employees, their assigned branch
        self.is_active = is_active
        self.created_at = created_at
    
    def __repr__(self):
        return f"User(id={self.id}, username='{self.username}', role='{self.role}')"
    
    def to_dict(self):
        """Convert user to dictionary"""
        return {
            'id': self.id,
            'username': self.username,
            'role': self.role,
            'branch_id': self.branch_id,
            'is_active': self.is_active,
            'created_at': self.created_at
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create user from dictionary"""
        return cls(
            id=data.get('id'),
            username=data.get('username'),
            password_hash=data.get('password_hash'),
            role=data.get('role'),
            branch_id=data.get('branch_id'),
            is_active=data.get('is_active', True),
            created_at=data.get('created_at')
        )

