from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Branch(Base):
    __tablename__ = "branches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    branch_id: Mapped[int | None] = mapped_column(ForeignKey("branches.id", ondelete="SET NULL"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    branch = relationship("Branch")

    __table_args__ = (
        CheckConstraint("role IN ('admin', 'employee')", name="ck_users_role"),
    )


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    tile_size: Mapped[str] = mapped_column(String(80), nullable=False)
    area_per_box: Mapped[float] = mapped_column(Float, nullable=False)
    pieces_per_box: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("name", "tile_size", name="uq_products_name_size"),
    )


class Inventory(Base):
    __tablename__ = "inventory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    grade: Mapped[str] = mapped_column(String(80), nullable=False)
    boxes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    loose_pieces: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rate_per_sqm: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    rate_per_box: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    rate_per_piece: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    branch = relationship("Branch")
    product = relationship("Product")

    __table_args__ = (
        UniqueConstraint("branch_id", "product_id", "grade", name="uq_inventory_branch_product_grade"),
    )


class Accessory(Base):
    __tablename__ = "accessories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    company: Mapped[str] = mapped_column(String(160), nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("category", "company", name="uq_accessories_category_company"),
    )


class AccessoryInventory(Base):
    __tablename__ = "accessories_inventory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id", ondelete="CASCADE"), nullable=False)
    accessory_id: Mapped[int] = mapped_column(ForeignKey("accessories.id", ondelete="CASCADE"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    branch = relationship("Branch")
    accessory = relationship("Accessory")

    __table_args__ = (
        UniqueConstraint("branch_id", "accessory_id", name="uq_accessory_inventory_branch_accessory"),
    )


class SanitaryProduct(Base):
    __tablename__ = "sanitary_products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_name: Mapped[str] = mapped_column(String(160), nullable=False)
    product_category: Mapped[str] = mapped_column(String(160), nullable=False)
    color: Mapped[str] = mapped_column(String(80), nullable=False)
    purchase_price: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    sale_price: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    sku: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("company_name", "product_category", "color", name="uq_sanitary_company_category_color"),
    )


class SanitaryInventory(Base):
    __tablename__ = "sanitary_inventory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id", ondelete="CASCADE"), nullable=False)
    sanitary_product_id: Mapped[int] = mapped_column(ForeignKey("sanitary_products.id", ondelete="CASCADE"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    branch = relationship("Branch")
    sanitary_product = relationship("SanitaryProduct")

    __table_args__ = (
        UniqueConstraint("branch_id", "sanitary_product_id", name="uq_sanitary_inventory_branch_product"),
    )


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    invoice_number: Mapped[str] = mapped_column(String(40), nullable=False)
    customer_name: Mapped[str] = mapped_column(String(160), nullable=False)
    customer_contact: Mapped[str | None] = mapped_column(String(80))
    invoice_date: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    subtotal: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    discount: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    grand_total: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    paid_amount: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    balance: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    branch = relationship("Branch")
    user = relationship("User")
    items = relationship("InvoiceItem", cascade="all, delete-orphan", back_populates="invoice")

    __table_args__ = (
        UniqueConstraint("branch_id", "invoice_number", name="uq_invoices_branch_number"),
    )


class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"))
    accessory_id: Mapped[int | None] = mapped_column(ForeignKey("accessories.id", ondelete="RESTRICT"))
    sanitary_product_id: Mapped[int | None] = mapped_column(ForeignKey("sanitary_products.id", ondelete="RESTRICT"))
    item_type: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    tile_size: Mapped[str | None] = mapped_column(String(80))
    grade: Mapped[str | None] = mapped_column(String(80))
    boxes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    loose_pieces: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rate_per_sqm: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    rate_per_box: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    rate_per_piece: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    line_total: Mapped[float] = mapped_column(Float, nullable=False)

    invoice = relationship("Invoice", back_populates="items")
    product = relationship("Product")
    accessory = relationship("Accessory")
    sanitary_product = relationship("SanitaryProduct")

    __table_args__ = (
        CheckConstraint("item_type IN ('tile', 'accessory', 'sanitary')", name="ck_invoice_items_type"),
    )


class StockTransaction(Base):
    __tablename__ = "stock_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    grade: Mapped[str] = mapped_column(String(80), nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(10), nullable=False)
    boxes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    loose_pieces: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    transaction_date: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class SanitaryStockTransaction(Base):
    __tablename__ = "sanitary_stock_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id", ondelete="CASCADE"), nullable=False)
    sanitary_product_id: Mapped[int] = mapped_column(ForeignKey("sanitary_products.id", ondelete="RESTRICT"), nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(10), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    transaction_date: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class ActivityLog(Base):
    __tablename__ = "activity_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    username: Mapped[str] = mapped_column(String(80), nullable=False)
    user_role: Mapped[str] = mapped_column(String(20), nullable=False)
    branch_id: Mapped[int | None] = mapped_column(ForeignKey("branches.id", ondelete="SET NULL"))
    branch_name: Mapped[str | None] = mapped_column(String(120))
    action_type: Mapped[str] = mapped_column(String(80), nullable=False)
    action_details: Mapped[str | None] = mapped_column(Text)
    action_date: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(80))
