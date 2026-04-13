"""
Branch model
Represents a branch/location of Tile Index
"""


class Branch:
    """Branch model class"""
    
    def __init__(self, id=None, name=None, code=None, created_at=None):
        self.id = id
        self.name = name
        self.code = code
        self.created_at = created_at
    
    def __repr__(self):
        return f"Branch(id={self.id}, name='{self.name}', code='{self.code}')"
    
    def to_dict(self):
        """Convert branch to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'created_at': self.created_at
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create branch from dictionary"""
        return cls(
            id=data.get('id'),
            name=data.get('name'),
            code=data.get('code'),
            created_at=data.get('created_at')
        )

