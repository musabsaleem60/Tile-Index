"""
Authentication Service
Handles user authentication and authorization
"""

from repositories.user_repository import UserRepository


class AuthenticationService:
    """Service for authentication operations"""
    
    @staticmethod
    def login(username, password):
        """Authenticate user with username and password"""
        if not username or not password:
            raise ValueError("Username and password are required")
        
        user = UserRepository.get_by_username(username)
        
        if not user:
            raise ValueError("Invalid username or password")
        
        if not user.is_active:
            raise ValueError("User account is inactive. Please contact administrator.")
        
        if not UserRepository.verify_password(user, password):
            raise ValueError("Invalid username or password")
        
        return user
    
    @staticmethod
    def is_admin(user):
        """Check if user is admin"""
        return user and user.role == 'admin'
    
    @staticmethod
    def is_employee(user):
        """Check if user is employee"""
        return user and user.role == 'employee'
    
    @staticmethod
    def can_access_branch(user, branch_id):
        """Check if user can access a specific branch"""
        if not user:
            return False
        
        # Admin can access all branches
        if user.role == 'admin':
            return True
        
        # Employee can only access their assigned branch
        if user.role == 'employee':
            return user.branch_id == branch_id
        
        return False
    
    @staticmethod
    def can_manage_products(user):
        """Check if user can manage products"""
        return AuthenticationService.is_admin(user)
    
    @staticmethod
    def can_view_reports(user):
        """Check if user can view reports"""
        return AuthenticationService.is_admin(user)
    
    @staticmethod
    def can_manage_users(user):
        """Check if user can manage users"""
        return AuthenticationService.is_admin(user)

