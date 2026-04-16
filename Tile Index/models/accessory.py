"""
Accessory model
Represents accessories like grouts and bonds
"""


class Accessory:
    """Accessory model class"""
    
    # Category constants
    CATEGORY_GROUT = 'Grout'
    CATEGORY_BOND = 'Bond'
    CATEGORY_FLOOR_WASTE = 'Floor Waste'
    CATEGORY_SPACER = 'Spacer'
    VALID_CATEGORIES = [CATEGORY_GROUT, CATEGORY_BOND, CATEGORY_FLOOR_WASTE, CATEGORY_SPACER]
    
    def __init__(self, id=None, name=None, category=None, company=None,
                 unit_price=0, created_at=None):
        self.id = id
        self.name = name
        self.category = category  # 'Grout' or 'Bond'
        self.company = company
        self.unit_price = unit_price
        self.created_at = created_at
    
    def __repr__(self):
        return f"Accessory(id={self.id}, name='{self.name}', category='{self.category}', company='{self.company}', price={self.unit_price})"
    
    def to_dict(self):
        """Convert accessory to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'company': self.company,
            'unit_price': self.unit_price,
            'created_at': self.created_at
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create accessory from dictionary"""
        return cls(
            id=data.get('id'),
            name=data.get('name'),
            category=data.get('category'),
            company=data.get('company'),
            unit_price=data.get('unit_price', 0),
            created_at=data.get('created_at')
        )


class AccessoryInventory:
    """Accessory inventory model class - tracks stock per branch"""
    
    def __init__(self, id=None, branch_id=None, accessory_id=None,
                 quantity=0, updated_at=None):
        self.id = id
        self.branch_id = branch_id
        self.accessory_id = accessory_id
        self.quantity = quantity
        self.updated_at = updated_at
    
    def __repr__(self):
        return f"AccessoryInventory(id={self.id}, branch={self.branch_id}, accessory={self.accessory_id}, qty={self.quantity})"
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'branch_id': self.branch_id,
            'accessory_id': self.accessory_id,
            'quantity': self.quantity,
            'updated_at': self.updated_at
        }
