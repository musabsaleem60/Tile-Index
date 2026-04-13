"""
User Repository
Data access layer for users
"""

import hashlib
from database.init_db import get_connection
from models.user import User


class UserRepository:
    """Repository for user operations"""
    
    @staticmethod
    def hash_password(password):
        """Hash a password using SHA256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    @staticmethod
    def get_by_username(username):
        """Get user by username"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, username, password_hash, role, branch_id, is_active, created_at
            FROM users WHERE username = ?
        """, (username,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return User(id=row[0], username=row[1], password_hash=row[2], role=row[3],
                       branch_id=row[4], is_active=bool(row[5]), created_at=row[6])
        return None
    
    @staticmethod
    def get_by_id(user_id):
        """Get user by ID"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, username, password_hash, role, branch_id, is_active, created_at
            FROM users WHERE id = ?
        """, (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return User(id=row[0], username=row[1], password_hash=row[2], role=row[3],
                       branch_id=row[4], is_active=bool(row[5]), created_at=row[6])
        return None
    
    @staticmethod
    def get_all():
        """Get all users"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, username, password_hash, role, branch_id, is_active, created_at
            FROM users ORDER BY username
        """)
        rows = cursor.fetchall()
        conn.close()
        
        return [User(id=r[0], username=r[1], password_hash=r[2], role=r[3],
                    branch_id=r[4], is_active=bool(r[5]), created_at=r[6]) for r in rows]
    
    @staticmethod
    def create(user, created_by_user=None):
        """Create a new user"""
        conn = get_connection()
        cursor = conn.cursor()
        
        # Hash password if provided as plain text
        password_hash = user.password_hash
        if not password_hash or len(password_hash) < 64:  # SHA256 hash is 64 chars
            password_hash = UserRepository.hash_password(password_hash or "")
        
        cursor.execute("""
            INSERT INTO users (username, password_hash, role, branch_id, is_active)
            VALUES (?, ?, ?, ?, ?)
        """, (user.username, password_hash, user.role, user.branch_id, 1 if user.is_active else 0))
        
        user.id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Log activity
        if created_by_user:
            try:
                from services.activity_log_service import ActivityLogService
                ActivityLogService.log_user_created(created_by_user, user.username, user.role)
            except:
                pass
        
        return user
    
    @staticmethod
    def update(user, updated_by_user=None):
        """Update an existing user"""
        # Get old user data for logging
        old_user = None
        if updated_by_user:
            old_user = UserRepository.get_by_id(user.id)
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # If password_hash is provided and looks like plain text, hash it
        password_hash = user.password_hash
        if password_hash and len(password_hash) < 64:
            password_hash = UserRepository.hash_password(password_hash)
        
        if password_hash:
            cursor.execute("""
                UPDATE users SET username = ?, password_hash = ?, role = ?, 
                               branch_id = ?, is_active = ?
                WHERE id = ?
            """, (user.username, password_hash, user.role, user.branch_id,
                  1 if user.is_active else 0, user.id))
        else:
            cursor.execute("""
                UPDATE users SET username = ?, role = ?, branch_id = ?, is_active = ?
                WHERE id = ?
            """, (user.username, user.role, user.branch_id,
                  1 if user.is_active else 0, user.id))
        
        conn.commit()
        conn.close()
        
        # Log activity
        if updated_by_user and old_user:
            try:
                from services.activity_log_service import ActivityLogService
                ActivityLogService.log_user_edited(updated_by_user, user.username)
                
                # Log status change if it changed
                if old_user.is_active != user.is_active:
                    ActivityLogService.log_user_status_changed(updated_by_user, user.username, user.is_active)
            except:
                pass
        
        return user
    
    @staticmethod
    def update_password(user_id, new_password, changed_by_user=None):
        """Update user password"""
        # Get user info for logging
        target_user = None
        if changed_by_user:
            target_user = UserRepository.get_by_id(user_id)
        
        conn = get_connection()
        cursor = conn.cursor()
        password_hash = UserRepository.hash_password(new_password)
        
        cursor.execute("""
            UPDATE users SET password_hash = ? WHERE id = ?
        """, (password_hash, user_id))
        
        conn.commit()
        conn.close()
        
        # Log activity
        if changed_by_user and target_user:
            try:
                from services.activity_log_service import ActivityLogService
                ActivityLogService.log_password_changed(changed_by_user, target_user.username)
            except:
                pass
    
    @staticmethod
    def verify_password(user, password):
        """Verify if password matches user's hash"""
        password_hash = UserRepository.hash_password(password)
        return password_hash == user.password_hash

