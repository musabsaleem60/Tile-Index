"""
Branch Repository
Data access layer for branches
"""

from database.init_db import get_connection
from models.branch import Branch
from desktop_client.remote_state import is_api_authenticated
from desktop_client.session import api_client, get_cached, set_cached


class BranchRepository:
    """Repository for branch operations"""
    
    @staticmethod
    def get_all():
        """Get all branches"""
        if is_api_authenticated():
            cached = get_cached("branches")
            if cached is not None:
                return cached
            rows = api_client.get("/catalog/branches")
            return set_cached("branches", [Branch(id=r["id"], name=r["name"], code=r["code"], created_at=r.get("created_at")) for r in rows])

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, code, created_at FROM branches ORDER BY name")
        rows = cursor.fetchall()
        conn.close()
        
        return [Branch(id=r[0], name=r[1], code=r[2], created_at=r[3]) for r in rows]
    
    @staticmethod
    def get_by_id(branch_id):
        """Get branch by ID"""
        if is_api_authenticated():
            for branch in BranchRepository.get_all():
                if branch.id == branch_id:
                    return branch
            return None

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, code, created_at FROM branches WHERE id = ?", (branch_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return Branch(id=row[0], name=row[1], code=row[2], created_at=row[3])
        return None
    
    @staticmethod
    def get_by_code(code):
        """Get branch by code"""
        if is_api_authenticated():
            for branch in BranchRepository.get_all():
                if branch.code == code:
                    return branch
            return None

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, code, created_at FROM branches WHERE code = ?", (code,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return Branch(id=row[0], name=row[1], code=row[2], created_at=row[3])
        return None

