"""
Sanitary product models
Represents sanitary products and branch-wise sanitary inventory
"""


class SanitaryProduct:
    """Sanitary product model class"""

    COMPANIES = [
        'Durr Ceramic',
        'Sunny Ceramic',
        'ACL Ceramic',
        'UCI Ceramic',
        'BONZ',
        'ORIENT (Local)',
    ]

    DEFAULT_COLORS = ['White', 'Off-White']
    ORIENT_COLORS = ['White', 'Off-White', 'Blue', 'Grey', 'Pink', 'Black']

    CATEGORIES = [
        '1 Piece Commode',
        '2 Piece Commode',
        'Vanity',
        '1 Piece Basin',
        'Basin Pedestal',
        'Corner Basin Pedestal',
        'WC',
    ]

    def __init__(self, id=None, company_name=None, product_category=None, color=None,
                 purchase_price=0, sale_price=0, sku=None, created_at=None):
        self.id = id
        self.company_name = company_name
        self.product_category = product_category
        self.color = color
        self.purchase_price = purchase_price
        self.sale_price = sale_price
        self.sku = sku
        self.created_at = created_at

    def __repr__(self):
        return (
            f"SanitaryProduct(id={self.id}, company='{self.company_name}', "
            f"category='{self.product_category}', color='{self.color}', sku='{self.sku}')"
        )

    def to_dict(self):
        """Convert sanitary product to dictionary"""
        return {
            'id': self.id,
            'company_name': self.company_name,
            'product_category': self.product_category,
            'color': self.color,
            'purchase_price': self.purchase_price,
            'sale_price': self.sale_price,
            'sku': self.sku,
            'created_at': self.created_at
        }

    @classmethod
    def from_dict(cls, data):
        """Create sanitary product from dictionary"""
        return cls(
            id=data.get('id'),
            company_name=data.get('company_name'),
            product_category=data.get('product_category'),
            color=data.get('color'),
            purchase_price=data.get('purchase_price', 0),
            sale_price=data.get('sale_price', 0),
            sku=data.get('sku'),
            created_at=data.get('created_at')
        )


class SanitaryInventory:
    """Sanitary inventory model class - tracks stock per branch"""

    def __init__(self, id=None, branch_id=None, sanitary_product_id=None,
                 quantity=0, updated_at=None):
        self.id = id
        self.branch_id = branch_id
        self.sanitary_product_id = sanitary_product_id
        self.quantity = quantity
        self.updated_at = updated_at

    def __repr__(self):
        return (
            f"SanitaryInventory(id={self.id}, branch={self.branch_id}, "
            f"sanitary_product={self.sanitary_product_id}, qty={self.quantity})"
        )

    def to_dict(self):
        """Convert sanitary inventory to dictionary"""
        return {
            'id': self.id,
            'branch_id': self.branch_id,
            'sanitary_product_id': self.sanitary_product_id,
            'quantity': self.quantity,
            'updated_at': self.updated_at
        }
