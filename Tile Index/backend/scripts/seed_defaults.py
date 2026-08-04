from sqlalchemy import select
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.entities import Accessory, Branch, SanitaryProduct, User


BRANCHES = [
    ("Tile Index - Korangi", "TIK"),
    ("Tile Cera - Korangi", "TCK"),
    ("Machi Mor", "MM"),
    ("DHA", "DHA"),
]

ACCESSORIES = [
    ("Grout", "Grout", "Shabir (White)", 400),
    ("Grout", "Grout", "Shabir (Almond)", 400),
    ("Grout", "Grout", "Strong (White)", 250),
    ("Bond", "Bond", "Shabir", 690),
    ("Bond", "Bond", "Stylo", 550),
    ("Floor Waste", "Floor Waste", "Heritage (Chrome)", 1700),
    ("Spacer", "Spacer", "Wall Spacer (1mm)", 100),
]

SANITARY_COMPANIES = [
    ("Durr Ceramic", ["White", "Off-White"]),
    ("Sunny Ceramic", ["White", "Off-White"]),
    ("ACL Ceramic", ["White", "Off-White"]),
    ("UCI Ceramic", ["White", "Off-White"]),
    ("BONZ", ["White", "Off-White"]),
    ("ORIENT (Local)", ["White", "Off-White", "Blue", "Grey", "Pink", "Black"]),
]

SANITARY_CATEGORIES = [
    "1 Piece Commode",
    "2 Piece Commode",
    "Vanity",
    "1 Piece Basin",
    "Basin Pedestal",
    "Corner Basin Pedestal",
    "WC",
]


def make_sku(company: str, category: str, color: str) -> str:
    raw = f"{company}-{category}-{color}"
    cleaned = "".join(ch if ch.isalnum() else "-" for ch in raw.upper())
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-")


def main():
    db = SessionLocal()
    try:
        for name, code in BRANCHES:
            if not db.scalar(select(Branch).where(Branch.code == code)):
                db.add(Branch(name=name, code=code))

        if not db.scalar(select(User).where(User.username == "musab")):
            db.add(User(
                username="musab",
                password_hash=hash_password("musab123"),
                role="admin",
                is_active=True,
            ))

        for name, category, company, price in ACCESSORIES:
            existing = db.scalar(
                select(Accessory).where(Accessory.category == category, Accessory.company == company)
            )
            if not existing:
                db.add(Accessory(name=name, category=category, company=company, unit_price=price))

        for company, colors in SANITARY_COMPANIES:
            for category in SANITARY_CATEGORIES:
                for color in colors:
                    sku = make_sku(company, category, color)
                    if not db.scalar(select(SanitaryProduct).where(SanitaryProduct.sku == sku)):
                        db.add(SanitaryProduct(
                            company_name=company,
                            product_category=category,
                            color=color,
                            purchase_price=0,
                            sale_price=0,
                            sku=sku,
                        ))

        db.commit()
        print("Default production data seeded.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
