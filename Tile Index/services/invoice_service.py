"""
Invoice Service
Business logic for invoice generation and management
"""

from repositories.invoice_repository import InvoiceRepository
from repositories.inventory_repository import InventoryRepository
from repositories.product_repository import ProductRepository
from repositories.user_repository import UserRepository
from services.inventory_service import InventoryService
from repositories.accessory_repository import AccessoryRepository
from services.accessory_service import AccessoryService
from repositories.sanitary_repository import SanitaryProductRepository
from services.sanitary_service import SanitaryService
from models.invoice import Invoice
from models.invoice_item import InvoiceItem
from datetime import datetime
from desktop_client.remote_state import is_api_authenticated
from desktop_client.session import api_client


class InvoiceService:
    """Service for invoice operations"""
    
    @staticmethod
    def create_invoice(branch_id, customer_name, customer_contact, items_data, discount=0, paid_amount=0, user_id=None):
        """
        Create a new invoice with items and update inventory
        
        items_data: List of dicts with keys: product_id, grade, boxes, loose_pieces
        """
        if is_api_authenticated():
            api_items = []
            for item in items_data:
                if item.get('product_id'):
                    api_items.append({
                        "item_type": "tile",
                        "product_id": item["product_id"],
                        "grade": item["grade"],
                        "boxes": item.get("boxes", 0),
                        "loose_pieces": item.get("loose_pieces", 0),
                        "quantity": 0,
                    })
                elif item.get('accessory_id'):
                    api_items.append({
                        "item_type": "accessory",
                        "accessory_id": item["accessory_id"],
                        "quantity": item.get("quantity", 0),
                        "boxes": item.get("quantity", 0),
                        "loose_pieces": 0,
                    })
                elif item.get('sanitary_product_id'):
                    api_items.append({
                        "item_type": "sanitary",
                        "sanitary_product_id": item["sanitary_product_id"],
                        "quantity": item.get("quantity", 0),
                        "boxes": item.get("quantity", 0),
                        "loose_pieces": 0,
                    })

            data = api_client.post("/invoices", {
                "branch_id": branch_id,
                "customer_name": customer_name,
                "customer_contact": customer_contact,
                "discount": discount,
                "paid_amount": paid_amount,
                "items": api_items,
            })
            return InvoiceService._invoice_from_api(data)

        # Validate inputs
        if not customer_name or not customer_name.strip():
            raise ValueError("Customer name is required")
        
        if discount < 0:
            raise ValueError("Discount cannot be negative")
        
        if paid_amount < 0:
            raise ValueError("Paid amount cannot be negative")
        
        if not items_data or len(items_data) == 0:
            raise ValueError("Invoice must have at least one item")
        
        # Create invoice object
        invoice = Invoice(
            branch_id=branch_id,
            customer_name=customer_name.strip(),
            customer_contact=customer_contact.strip() if customer_contact else None,
            invoice_date=datetime.now(),
            discount=discount,
            paid_amount=paid_amount
        )
        
        # Store user_id if provided (will be set in repository)
        if user_id:
            invoice.user_id = user_id
        
        # Process items and calculate totals
        subtotal = 0
        
        for item_data in items_data:
            product_id = item_data.get('product_id')
            accessory_id = item_data.get('accessory_id')
            sanitary_product_id = item_data.get('sanitary_product_id')
            
            if product_id:
                grade = item_data['grade']
                boxes = item_data.get('boxes', 0)
                loose_pieces = item_data.get('loose_pieces', 0)
                
                # Validate item
                if boxes < 0 or loose_pieces < 0:
                    raise ValueError("Item quantities cannot be negative")
                
                if boxes == 0 and loose_pieces == 0:
                    continue  # Skip empty items
                
                # Get product
                product = ProductRepository.get_by_id(product_id)
                if not product:
                    raise ValueError(f"Product with ID {product_id} not found")
                
                # Get inventory for rates
                inventory = InventoryRepository.get_by_branch_product_grade(branch_id, product_id, grade)
                if not inventory:
                    raise ValueError(f"No inventory found for this product and grade at this branch")
                
                # Check stock availability
                total_available_pieces = (inventory.boxes * product.pieces_per_box) + inventory.loose_pieces
                total_requested_pieces = (boxes * product.pieces_per_box) + loose_pieces
                
                if total_requested_pieces > total_available_pieces:
                    raise ValueError(f"Insufficient stock for {product.name} ({product.tile_size}) - {grade}. Available: {inventory.boxes} boxes + {inventory.loose_pieces} pieces")
                
                # Calculate line total
                line_total = (boxes * inventory.rate_per_box) + (loose_pieces * inventory.rate_per_piece)
                
                # Create invoice item
                item = InvoiceItem(
                    invoice_id=None,
                    product_id=product_id,
                    tile_size=product.tile_size,
                    grade=grade,
                    boxes=boxes,
                    loose_pieces=loose_pieces,
                    rate_per_sqm=inventory.rate_per_sqm,
                    rate_per_box=inventory.rate_per_box,
                    rate_per_piece=inventory.rate_per_piece,
                    line_total=line_total
                )
            elif accessory_id:
                quantity = item_data.get('quantity', 0)
                if quantity <= 0:
                    continue
                
                # Get accessory
                accessory = AccessoryRepository.get_by_id(accessory_id)
                if not accessory:
                    raise ValueError(f"Accessory with ID {accessory_id} not found")
                
                # Get accessory inventory
                acc_inv = AccessoryService.get_inventory(branch_id, accessory_id)
                if not acc_inv or acc_inv.quantity < quantity:
                    available = acc_inv.quantity if acc_inv else 0
                    raise ValueError(f"Insufficient stock for accessory {accessory.name} ({accessory.company}). Available: {available}")
                
                # Calculate line total
                line_total = quantity * accessory.unit_price
                
                # Create invoice item
                item = InvoiceItem(
                    invoice_id=None,
                    accessory_id=accessory_id,
                    boxes=quantity,  # Reuse boxes as quantity for accessories
                    rate_per_box=accessory.unit_price,  # Reuse rate_per_box as unit_price
                    line_total=line_total
                )
            elif sanitary_product_id:
                quantity = item_data.get('quantity', 0)
                if quantity <= 0:
                    continue

                sanitary_product = SanitaryProductRepository.get_by_id(sanitary_product_id)
                if not sanitary_product:
                    raise ValueError(f"Sanitary product with ID {sanitary_product_id} not found")

                sanitary_inv = SanitaryService.get_inventory(branch_id, sanitary_product_id)
                available = sanitary_inv.quantity if sanitary_inv else 0
                if quantity > available:
                    raise ValueError(
                        f"Insufficient stock for sanitary product {sanitary_product.product_category} "
                        f"({sanitary_product.company_name}, {sanitary_product.color}). Available: {available}"
                    )

                line_total = quantity * sanitary_product.sale_price

                item = InvoiceItem(
                    invoice_id=None,
                    sanitary_product_id=sanitary_product_id,
                    tile_size=sanitary_product.color,
                    grade=sanitary_product.sku,
                    boxes=quantity,
                    rate_per_box=sanitary_product.sale_price,
                    line_total=line_total
                )
            else:
                continue
            
            invoice.items.append(item)
            subtotal += line_total
        
        if len(invoice.items) == 0:
            raise ValueError("Invoice must have at least one valid item")
        
        # Calculate totals
        invoice.subtotal = subtotal
        invoice.grand_total = subtotal - discount
        invoice.balance = invoice.grand_total - paid_amount
        
        # Save invoice (this will generate invoice number)
        invoice = InvoiceRepository.create(invoice)
        
        # Deduct stock from inventory for each item
        for item in invoice.items:
            try:
                if item.product_id:
                    InventoryService.deduct_stock(
                        branch_id,
                        item.product_id,
                        item.grade,
                        item.boxes,
                        item.loose_pieces,
                        user_id=user_id,
                        notes=f"Invoice: {invoice.invoice_number}"
                    )
                elif item.accessory_id:
                    AccessoryService.deduct_stock(
                        branch_id,
                        item.accessory_id,
                        item.boxes  # boxes field used for accessory quantity
                    )
                elif item.sanitary_product_id:
                    SanitaryService.deduct_stock(
                        branch_id,
                        item.sanitary_product_id,
                        item.boxes,
                        user_id=user_id,
                        notes=f"Invoice: {invoice.invoice_number}"
                    )
            except Exception as e:
                # If stock deduction fails, we should rollback the invoice
                # For simplicity, we'll raise an error (in production, use transactions)
                raise ValueError(f"Failed to update inventory for {item.product_id or item.accessory_id}: {str(e)}")
        
        # Log activity
        try:
            if user_id:
                user = UserRepository.get_by_id(user_id)
                if user:
                    ActivityLogService.log_invoice_created(
                        user, branch_id, invoice.invoice_number,
                        invoice.customer_name, invoice.grand_total
                    )
        except:
            pass  # Don't fail if logging fails
        
        return invoice
    
    @staticmethod
    def get_invoice(invoice_id):
        """Get invoice by ID"""
        if is_api_authenticated():
            return InvoiceService._invoice_from_api(api_client.get(f"/invoices/{invoice_id}"))

        return InvoiceRepository.get_by_id(invoice_id)
    
    @staticmethod
    def search_invoices(branch_id=None, invoice_number=None, customer_name=None, date_from=None, date_to=None):
        """Search invoices with filters"""
        if is_api_authenticated():
            path = "/invoices"
            if branch_id:
                path += f"?branch_id={branch_id}"
            invoices = [InvoiceService._invoice_from_api(item) for item in api_client.get(path)]
            if invoice_number:
                invoices = [inv for inv in invoices if invoice_number.lower() in inv.invoice_number.lower()]
            if customer_name:
                invoices = [inv for inv in invoices if customer_name.lower() in inv.customer_name.lower()]
            if date_from:
                invoices = [inv for inv in invoices if str(inv.invoice_date)[:10] >= date_from]
            if date_to:
                invoices = [inv for inv in invoices if str(inv.invoice_date)[:10] <= date_to]
            return invoices

        return InvoiceRepository.search(branch_id, invoice_number, customer_name, date_from, date_to)

    @staticmethod
    def _invoice_from_api(data):
        """Convert API invoice payload to desktop Invoice model."""
        invoice = Invoice(
            id=data.get("id"),
            branch_id=data.get("branch_id"),
            invoice_number=data.get("invoice_number"),
            customer_name=data.get("customer_name"),
            customer_contact=data.get("customer_contact"),
            invoice_date=data.get("invoice_date"),
            subtotal=data.get("subtotal", 0),
            discount=data.get("discount", 0),
            grand_total=data.get("grand_total", 0),
            paid_amount=data.get("paid_amount", 0),
            balance=data.get("balance", 0),
            user_id=data.get("user_id"),
        )
        for item in data.get("items", []):
            invoice.items.append(InvoiceItem(
                id=item.get("id"),
                invoice_id=invoice.id,
                product_id=item.get("product_id"),
                accessory_id=item.get("accessory_id"),
                sanitary_product_id=item.get("sanitary_product_id"),
                tile_size=item.get("tile_size"),
                grade=item.get("grade"),
                boxes=item.get("boxes", item.get("quantity", 0)),
                loose_pieces=item.get("loose_pieces", 0),
                rate_per_sqm=item.get("rate_per_sqm", 0),
                rate_per_box=item.get("rate_per_box", item.get("unit_price", 0)),
                rate_per_piece=item.get("rate_per_piece", 0),
                line_total=item.get("line_total", 0)
            ))
        return invoice

