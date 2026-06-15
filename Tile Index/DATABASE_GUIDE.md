# Tile Index Database Access Guide

This guide explains how to access the database and provides a visualization of its structure (ER Diagram).

## 1. Database Location
The database file for the **Tile Index** project is located at:
`e:\Projects\Tile Index\Tile Index\data\tile_index.db`

---

## 2. Using DB Browser for SQLite
Since you have **DB Browser for SQLite** installed, follow these steps to view the data and structure:

1.  **Open DB Browser for SQLite**.
2.  Click **Open Database** (or go to `File` > `Open Database`).
3.  Navigate to the path: `e:\Projects\Tile Index\Tile Index\data\`.
4.  Select `tile_index.db` and click **Open**.
5.  **Database Structure Tab**: Here you can see all tables (Branches, Products, Invoices, etc.) and their column definitions.
6.  **Browse Data Tab**: Select a table from the dropdown to see the actual records (e.g., look at `PRODUCTS` to see your tile inventory).
7.  **Execute SQL Tab**: You can run custom queries here (e.g., `SELECT * FROM INVOICES WHERE grand_total > 5000`).

---

## 3. Database ER Diagram
Here is the Entity-Relationship (ER) diagram showing how the tables are connected.

```mermaid
erDiagram
    BRANCHES ||--o{ USERS : "has"
    BRANCHES ||--o{ INVOICES : "issues"
    BRANCHES ||--o{ INVENTORY : "stores"
    BRANCHES ||--o{ ACCESSORIES_INVENTORY : "stores"
    BRANCHES ||--o{ STOCK_TRANSACTIONS : "logs"

    PRODUCTS ||--o{ INVENTORY : "stocked as"
    PRODUCTS ||--o{ STOCK_TRANSACTIONS : "moved in"
    PRODUCTS ||--o{ INVOICE_ITEMS : "sold as"

    USERS ||--o{ INVOICES : "creates"
    USERS ||--o{ STOCK_TRANSACTIONS : "performs"
    USERS ||--o{ ACTIVITY_LOG : "logs"

    INVOICES ||--|{ INVOICE_ITEMS : "contains"

    ACCESSORIES ||--o{ ACCESSORIES_INVENTORY : "stocked as"
    ACCESSORIES ||--o{ INVOICE_ITEMS : "sold as"

    BRANCHES {
        int id PK
        string name
        string code
    }

    PRODUCTS {
        int id PK
        string name
        string tile_size
        float area_per_box
    }

    INVOICES {
        int id PK
        int branch_id FK
        string invoice_number
        float grand_total
        timestamp invoice_date
    }

    USERS {
        int id PK
        string username
        string role
        int branch_id FK
    }

    INVENTORY {
        int id PK
        int branch_id FK
        int product_id FK
        string grade
        int boxes
    }

    ACCESSORIES {
        int id PK
        string name
        string category
        string company
        float unit_price
    }

    INVOICE_ITEMS {
        int id PK
        int invoice_id FK
        int product_id FK
        int accessory_id FK
        float line_total
    }
```

---

## 4. Quick Access via Python
If you want to quickly see the structure without opening DB Browser, you can run the following command in your terminal:

```powershell
python check_db_structure.py
```

This script will output a text-based version of the table schemas directly to your console.
