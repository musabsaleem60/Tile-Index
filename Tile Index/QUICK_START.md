# Quick Start Guide - Tile Index System

## First Time Setup

1. **Ensure Python 3.8+ is installed**
   - Check by running: `python --version`

2. **Run the application**
   ```bash
   python main.py
   ```

3. **The database will be automatically created** on first run in the `data/` folder

## Getting Started

### Step 1: Add Products
1. Click **"Inventory Management"** from main menu
2. Enter product details:
   - Product Name (e.g., "Ceramic Tile")
   - Tile Size (e.g., "8x12")
   - Area per Box (e.g., 1.4)
   - Pieces per Box (e.g., 23)
3. Click **"Add Product"**

### Step 2: Add Stock
1. In **Inventory Management**:
   - Select a **Branch** (e.g., "Tile Index – Korangi")
   - Select a **Product** from the list
   - Choose **Grade** (G1, G2, or G3)
   - Enter stock quantities:
     - Boxes: 10
     - Loose Pieces: 5
   - Enter pricing:
     - Rate per m²: 500
     - Rate per Box: 700
     - Rate per Piece: 30
2. Click **"Add Stock"**

### Step 3: Create an Invoice
1. Click **"Invoice & Billing"** from main menu
2. Select **Branch** and enter **Customer Name**
3. Add items:
   - Select **Product** and **Grade**
   - Enter quantities (e.g., 2 boxes + 3 pieces)
   - Click **"Add to Invoice"**
4. Adjust **Discount** and **Paid Amount** if needed
5. Click **"Generate Invoice"**
6. Invoice will open automatically for viewing/printing

### Step 4: Search Invoices
1. Click **"Search Invoices"** from main menu
2. Enter search criteria (branch, invoice number, customer, date range)
3. Click **"Search"**
4. Double-click an invoice to view/print it

### Step 5: View Reports
1. Click **"Reports"** from main menu
2. Select **Branch** and **Report Type**
3. For daily sales, select a **Date**
4. Click **"Generate Report"**

## Important Notes

- **Stock is automatically deducted** when you generate an invoice
- **Invoice numbers are auto-generated** per branch (e.g., TIK-0001, TIK-0002)
- **Mixed quantities** are supported (boxes + loose pieces)
- **Stock conversion** happens automatically (excess pieces become boxes)
- **Negative stock is prevented** - system will show error if insufficient stock

## Keyboard Shortcuts

- **Tab**: Move between fields
- **Enter**: Submit forms (where applicable)
- **Double-click**: View invoice (in search results)

## Troubleshooting

**Database Error on Startup**
- Ensure you have write permissions in the project folder
- Check if `data/` folder can be created

**No Products Showing**
- Add products first in Inventory Management

**Cannot Add Stock**
- Ensure branch and product are selected
- Check that all rate fields have valid numbers

**Invoice Generation Fails**
- Check that stock is available for selected product and grade
- Ensure at least one item is added to invoice
- Verify customer name is entered

---

**Need Help?** Refer to the main README.md for detailed documentation.

