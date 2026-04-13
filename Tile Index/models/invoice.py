"""
Invoice model
Represents an invoice/bill
"""

from datetime import datetime


class Invoice:
    """Invoice model class"""
    
    def __init__(self, id=None, branch_id=None, invoice_number=None,
                 customer_name=None, customer_contact=None, invoice_date=None,
                 subtotal=0, discount=0, grand_total=0, paid_amount=0,
                 balance=0, created_at=None, user_id=None):
        self.id = id
        self.branch_id = branch_id
        self.invoice_number = invoice_number
        self.customer_name = customer_name
        self.customer_contact = customer_contact
        self.invoice_date = invoice_date if invoice_date else datetime.now()
        self.subtotal = subtotal
        self.discount = discount
        self.grand_total = grand_total
        self.paid_amount = paid_amount
        self.balance = balance
        self.created_at = created_at
        self.user_id = user_id  # User who created the invoice
        self.items = []  # List of InvoiceItem objects
    
    def __repr__(self):
        return f"Invoice(id={self.id}, number='{self.invoice_number}', branch_id={self.branch_id}, total={self.grand_total})"
    
    def to_dict(self):
        """Convert invoice to dictionary"""
        return {
            'id': self.id,
            'branch_id': self.branch_id,
            'invoice_number': self.invoice_number,
            'customer_name': self.customer_name,
            'customer_contact': self.customer_contact,
            'invoice_date': self.invoice_date,
            'subtotal': self.subtotal,
            'discount': self.discount,
            'grand_total': self.grand_total,
            'paid_amount': self.paid_amount,
            'balance': self.balance,
            'created_at': self.created_at
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create invoice from dictionary"""
        return cls(
            id=data.get('id'),
            branch_id=data.get('branch_id'),
            invoice_number=data.get('invoice_number'),
            customer_name=data.get('customer_name'),
            customer_contact=data.get('customer_contact'),
            invoice_date=data.get('invoice_date'),
            subtotal=data.get('subtotal', 0),
            discount=data.get('discount', 0),
            grand_total=data.get('grand_total', 0),
            paid_amount=data.get('paid_amount', 0),
            balance=data.get('balance', 0),
            created_at=data.get('created_at')
        )

