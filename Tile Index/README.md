# Tile Index - Inventory & Billing System

A complete desktop inventory management and invoice billing system for Tile Index, a tiles trading company in Pakistan.

## Features

### 🏢 Multi-Branch Support
- 4 hard-coded branches (extensible):
  - Tile Index – Korangi
  - Tile Cera – Korangi
  - Machi Mor
  - DHA
- Each branch maintains independent inventory and generates separate invoices

### 📦 Product Management
- Manage tile products with attributes:
  - Product Name
  - Tile Size (e.g., 8x12)
  - Area per Box (m²)
  - Pieces per Box
- Grade-based pricing (G1, G2, G3)

### 📊 Inventory Management
- Branch-wise and grade-wise stock tracking
- Stock units: Boxes and Loose Pieces
- Stock operations:
  - Stock IN (purchase/opening stock)
  - Stock OUT (sales)
- Automatic conversion between boxes and pieces
- Prevents negative stock
- Low stock warnings

### 🧾 Invoice & Billing
- Pakistani-style invoice format
- Auto-incrementing invoice numbers (branch-wise)
- Support for:
  - Complete boxes
  - Loose tiles
  - Mixed quantities (e.g., 1 box + 5 pieces)
- Automatic calculations:
  - Line totals
  - Subtotal
  - Discount
  - Grand Total
  - Balance
- Customer information tracking
- Invoice search and retrieval

### 📈 Reports
- Daily sales report
- Branch-wise stock report
- Grade-wise inventory summary

## Technology Stack

- **Language**: Python 3.8+
- **GUI Framework**: Tkinter (built-in)
- **Database**: SQLite (built-in)
- **Architecture**: Clean Architecture with MVC pattern

## Installation

1. **Prerequisites**: Python 3.8 or higher installed on Windows

2. **Clone or download** this project to your local machine

3. **No external dependencies required** - uses only Python built-in libraries

## Running the Application

1. Open a terminal/command prompt in the project directory

2. Run the main application:
   ```bash
   python main.py
   ```

3. The application window will open with the main menu

## Project Structure

```
Tile Index/
├── main.py                 # Application entry point
├── requirements.txt        # Dependencies (none required)
├── README.md              # This file
├── database/
│   ├── __init__.py
│   └── init_db.py         # Database initialization
├── models/                # Data models
│   ├── __init__.py
│   ├── branch.py
│   ├── product.py
│   ├── inventory.py
│   ├── invoice.py
│   └── invoice_item.py
├── repositories/          # Data access layer
│   ├── __init__.py
│   ├── branch_repository.py
│   ├── product_repository.py
│   ├── inventory_repository.py
│   └── invoice_repository.py
├── services/              # Business logic layer
│   ├── __init__.py
│   ├── inventory_service.py
│   ├── invoice_service.py
│   └── report_service.py
├── ui/                    # User interface layer
│   ├── __init__.py
│   ├── main_window.py
│   ├── inventory_window.py
│   ├── invoice_window.py
│   └── report_window.py
├── utils/                 # Utilities
│   ├── __init__.py
│   └── validators.py
└── data/                  # Database storage (created automatically)
    └── tile_index.db
```

## Usage Guide

### Setting Up Products

1. Click **"Inventory Management"** from the main menu
2. In the left panel, enter product details:
   - Product Name
   - Tile Size
   - Area per Box (m²)
   - Pieces per Box
3. Click **"Add Product"**

### Adding Stock

1. In **Inventory Management** window:
   - Select a branch from dropdown
   - Select a product from the list
   - Choose grade (G1, G2, or G3)
   - Enter stock quantities (boxes and/or loose pieces)
   - Enter pricing rates:
     - Rate per m²
     - Rate per Box
     - Rate per Piece
2. Click **"Add Stock"**

### Creating an Invoice

1. Click **"Invoice & Billing"** from the main menu
2. Select branch and enter customer details
3. Add items:
   - Select product and grade
   - Enter quantities (boxes and/or pieces)
   - Click **"Add to Invoice"**
4. Adjust discount and paid amount if needed
5. Click **"Generate Invoice"**

### Viewing Reports

1. Click **"Reports"** from the main menu
2. Select branch and report type
3. For daily sales, select a date
4. Click **"Generate Report"**

## Database

The application uses SQLite database stored in `data/tile_index.db`. The database is automatically created and initialized on first run.

### Database Schema

- **branches**: Branch information
- **products**: Product catalog
- **inventory**: Stock levels (branch × product × grade)
- **invoices**: Invoice headers
- **invoice_items**: Invoice line items

## Features & Limitations

### ✅ Implemented Features

- Complete inventory management
- Invoice generation with Pakistani format
- Multi-branch support
- Grade-wise stock tracking
- Mixed quantity sales (boxes + pieces)
- Automatic stock conversion
- Input validation
- Transaction safety
- Basic reporting

### 🔄 Future Extensions

The system is designed to be extensible. Possible enhancements:
- User authentication
- Advanced reporting with charts
- Barcode scanning
- Email/SMS invoice delivery
- Backup and restore functionality
- Multi-currency support
- Purchase order management

## Support

For issues or questions, please refer to the code comments or contact the development team.

## License

This software is proprietary and developed for Tile Index.

---

**Version**: 1.0.0  
**Last Updated**: 2024  
**Platform**: Windows Desktop Application

