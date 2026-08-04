"""
Activity Log Repository
Data access layer for activity logs (audit trail)
"""

from database.init_db import get_connection
from models.activity_log import ActivityLog


class ActivityLogRepository:
    """Repository for activity log operations"""
    
    @staticmethod
    def create(activity_log):
        """Create a new activity log entry"""
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO activity_log (user_id, username, user_role, branch_id, branch_name,
                                    action_type, action_details, action_date, ip_address)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (activity_log.user_id, activity_log.username, activity_log.user_role,
              activity_log.branch_id, activity_log.branch_name, activity_log.action_type,
              activity_log.action_details, activity_log.action_date, activity_log.ip_address))
        
        activity_log.id = cursor.lastrowid
        conn.commit()
        conn.close()
        return activity_log
    
    @staticmethod
    def search(user_id=None, action_type=None, branch_id=None, date_from=None, date_to=None, limit=1000):
        """Search activity logs with filters"""
        conn = get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT id, user_id, username, user_role, branch_id, branch_name,
                   action_type, action_details, action_date, ip_address
            FROM activity_log WHERE 1=1
        """
        params = []
        
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        
        if action_type:
            query += " AND action_type = ?"
            params.append(action_type)
        
        if branch_id:
            query += " AND branch_id = ?"
            params.append(branch_id)
        
        if date_from:
            # Handle date comparison properly
            query += " AND DATE(action_date) >= DATE(?)"
            params.append(date_from)
        
        if date_to:
            # Handle date comparison properly
            query += " AND DATE(action_date) <= DATE(?)"
            params.append(date_to)
        
        query += " ORDER BY action_date DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [ActivityLog(id=r[0], user_id=r[1], username=r[2], user_role=r[3],
                          branch_id=r[4], branch_name=r[5], action_type=r[6],
                          action_details=r[7], action_date=r[8], ip_address=r[9]) for r in rows]
    
    @staticmethod
    def get_all(limit=1000):
        """Get all activity logs"""
        return ActivityLogRepository.search(limit=limit)
    
    @staticmethod
    def get_by_id(activity_id):
        """Get activity log by ID"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, user_id, username, user_role, branch_id, branch_name,
                   action_type, action_details, action_date, ip_address
            FROM activity_log WHERE id = ?
        """, (activity_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return ActivityLog(id=row[0], user_id=row[1], username=row[2], user_role=row[3],
                             branch_id=row[4], branch_name=row[5], action_type=row[6],
                             action_details=row[7], action_date=row[8], ip_address=row[9])
        return None
    
    @staticmethod
    def get_by_user(user_id, limit=500):
        """Get activity logs for a specific user"""
        return ActivityLogRepository.search(user_id=user_id, limit=limit)
    
    @staticmethod
    def get_by_action_type(action_type, limit=500):
        """Get activity logs for a specific action type"""
        return ActivityLogRepository.search(action_type=action_type, limit=limit)

