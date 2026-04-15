
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.init_db import init_database
from services.invoice_service import InvoiceService
from services.accessory_service import AccessoryService
from services.inventory_service import InventoryService
from repositories.product_repository import ProductRepository
from repositories.branch_repository import BranchRepository
from utils.grade_constants import GRADE_1

def test_accessory_billing():
    # 1. Initialize DB
    init_database()
    
    # 2. Setup test data
    branches = BranchRepository.get_all()
    if not branches:
        print("No branches found")
        return
    branch = branches[0]
    
    products = ProductRepository.get_all()
    if not products:
        print("No products found")
        return
    product = products[0]
    
    accessories = AccessoryService.get_all_accessories()
    if not accessories:
        print("No accessories found")
        return
    accessory = accessories[0]
    
    # 3. Add stock for both
    print(f"Adding stock for {product.name} and {accessory.name} at {branch.name}...")
    InventoryService.add_stock(branch.id, product.id, GRADE_1, 100, 0, 1000, 2000, 200, user_id=1)
    AccessoryService.set_stock(branch.id, accessory.id, 50)
    
    # 4. Create Invoice with both
    print("Creating invoice with tile and accessory...")
    items_data = [
        {
            'product_id': product.id,
            'grade': GRADE_1,
            'boxes': 5,
            'loose_pieces': 10
        },
        {
            'accessory_id': accessory.id,
            'quantity': 2
        }
    ]
    
    try:
        invoice = InvoiceService.create_invoice(
            branch.id,
            "Test Customer",
            "123456789",
            items_data,
            discount=100,
            paid_amount=500,
            user_id=1
        )
        print(f"Invoice created: {invoice.invoice_number}")
        print(f"Grand Total: {invoice.grand_total}")
        print(f"Items count: {len(invoice.items)}")
        
        for item in invoice.items:
            if item.product_id:
                print(f"Tile Item: Product {item.product_id}, boxes: {item.boxes}")
            else:
                print(f"Accessory Item: Accessory {item.accessory_id}, quantity: {item.boxes}")
                
        # 5. Check stock deduction
        inv = InventoryService.get_inventory(branch.id, product.id, GRADE_1)
        acc_inv = AccessoryService.get_inventory(branch.id, accessory.id)
        
        print(f"Remaining tile stock: {inv.boxes} boxes")
        print(f"Remaining accessory stock: {acc_inv.quantity}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_accessory_billing()
