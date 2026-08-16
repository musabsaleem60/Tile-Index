from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
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


class BranchAlias(Base):
    __tablename__ = "branch_aliases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id", ondelete="CASCADE"), nullable=False)
    alias_name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    source_name: Mapped[str | None] = mapped_column(String(120))
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    branch = relationship("Branch")


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



class DesktopClientStatus(Base):
    __tablename__ = "desktop_client_statuses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    machine_id: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    hostname: Mapped[str | None] = mapped_column(String(160))
    username: Mapped[str | None] = mapped_column(String(80))
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    branch_id: Mapped[int | None] = mapped_column(ForeignKey("branches.id", ondelete="SET NULL"))
    app_version: Mapped[str] = mapped_column(String(40), nullable=False)
    latest_version: Mapped[str | None] = mapped_column(String(40))
    min_desktop_version: Mapped[str | None] = mapped_column(String(40))
    certificate_trusted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    update_available: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    updates_disabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    details: Mapped[dict | None] = mapped_column(JSON)
    first_seen_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", foreign_keys=[user_id])
    branch = relationship("Branch")

class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    item_code: Mapped[str | None] = mapped_column(String(40), unique=True)
    normalized_product_name: Mapped[str | None] = mapped_column(String(160))
    tile_size: Mapped[str] = mapped_column(String(80), nullable=False)
    area_per_box: Mapped[float] = mapped_column(Float, nullable=False)
    pieces_per_box: Mapped[int] = mapped_column(Integer, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("name", "tile_size", name="uq_products_name_size"),
        UniqueConstraint("normalized_product_name", "tile_size", name="uq_products_normalized_name_size"),
    )


class TileSize(Base):
    __tablename__ = "tile_sizes"

    tile_size: Mapped[str] = mapped_column(String(80), primary_key=True)
    pieces_per_box: Mapped[int] = mapped_column(Integer, nullable=False)
    area_per_box: Mapped[float] = mapped_column(Float, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class TileRate(Base):
    __tablename__ = "tile_rates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tile_size: Mapped[str] = mapped_column(ForeignKey("tile_sizes.tile_size", ondelete="RESTRICT"), nullable=False)
    grade: Mapped[str] = mapped_column(String(80), nullable=False)
    rate_per_meter: Mapped[float] = mapped_column(Float, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    size = relationship("TileSize")

    __table_args__ = (
        CheckConstraint("grade IN ('G1 Prime', 'G2 Standard', 'G3 Regular')", name="ck_tile_rates_grade"),
        UniqueConstraint("tile_size", "grade", name="uq_tile_rates_size_grade"),
    )


class ProductRateOverride(Base):
    __tablename__ = "product_rate_overrides"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    grade: Mapped[str] = mapped_column(String(80), nullable=False)
    rate_per_meter: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    product = relationship("Product")
    created_by = relationship("User")

    __table_args__ = (
        CheckConstraint("grade IN ('G1 Prime', 'G2 Standard', 'G3 Regular')", name="ck_product_rate_overrides_grade"),
        UniqueConstraint("product_id", "grade", name="uq_product_rate_overrides_product_grade"),
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
    company: Mapped[str | None] = mapped_column(String(160))
    unit_price: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("accessory_categories.id", ondelete="RESTRICT"))
    product_name: Mapped[str | None] = mapped_column(String(160))
    colour: Mapped[str | None] = mapped_column(String(80))
    size: Mapped[str | None] = mapped_column(String(80))
    weight: Mapped[str | None] = mapped_column(String(80))
    product_type: Mapped[str | None] = mapped_column(String(160))
    normalized_identity: Mapped[str | None] = mapped_column(String(220))
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


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
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    voided_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))
    voided_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    void_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    branch = relationship("Branch")
    user = relationship("User", foreign_keys=[user_id])
    voided_by = relationship("User", foreign_keys=[voided_by_user_id])
    items = relationship("InvoiceItem", cascade="all, delete-orphan", back_populates="invoice")

    __table_args__ = (
        UniqueConstraint("branch_id", "invoice_number", name="uq_invoices_branch_number"),
        CheckConstraint("status IN ('active', 'void')", name="ck_invoices_status"),
    )


class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"))
    accessory_id: Mapped[int | None] = mapped_column(ForeignKey("accessories.id", ondelete="RESTRICT"))
    sanitary_product_id: Mapped[int | None] = mapped_column(ForeignKey("sanitary_products.id", ondelete="RESTRICT"))
    source_branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id", ondelete="RESTRICT"), nullable=False)
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
    boxes_from_boxes: Mapped[int | None] = mapped_column(Integer)
    pieces_from_loose: Mapped[int | None] = mapped_column(Integer)

    invoice = relationship("Invoice", back_populates="items")
    product = relationship("Product")
    accessory = relationship("Accessory")
    sanitary_product = relationship("SanitaryProduct")
    source_branch = relationship("Branch")

    __table_args__ = (
        CheckConstraint("item_type IN ('tile', 'accessory', 'sanitary')", name="ck_invoice_items_type"),
    )


class StockTransaction(Base):
    __tablename__ = "stock_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    import_batch_id: Mapped[int | None] = mapped_column(ForeignKey("import_batches.id", ondelete="SET NULL"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"))
    accessory_id: Mapped[int | None] = mapped_column(ForeignKey("accessories.id", ondelete="RESTRICT"))
    sanitary_product_id: Mapped[int | None] = mapped_column(ForeignKey("sanitary_products.id", ondelete="RESTRICT"))
    item_type: Mapped[str] = mapped_column(String(30), default="tile", nullable=False)
    grade: Mapped[str | None] = mapped_column(String(80))
    transaction_type: Mapped[str] = mapped_column(String(10), nullable=False)
    boxes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    loose_pieces: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    transaction_date: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    source_row_number: Mapped[int | None] = mapped_column(Integer)


class ImportBatch(Base):
    __tablename__ = "import_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    import_type: Mapped[str] = mapped_column(String(40), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    exported_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    committed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))
    failed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))
    reverted_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))
    summary_json: Mapped[dict | None] = mapped_column(JSON)
    error_json: Mapped[dict | None] = mapped_column(JSON)

    created_by = relationship("User")

    __table_args__ = (
        CheckConstraint("import_type IN ('tiles')", name="ck_import_batches_type"),
        CheckConstraint("status IN ('dry_run', 'committed', 'failed', 'reverted')", name="ck_import_batches_status"),
    )


class ImportBatchRow(Base):
    __tablename__ = "import_batch_rows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("import_batches.id", ondelete="CASCADE"), nullable=False)
    sheet_name: Mapped[str] = mapped_column(String(120), nullable=False)
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    operation: Mapped[str | None] = mapped_column(String(40))
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"))
    item_code: Mapped[str | None] = mapped_column(String(40))
    branch_id: Mapped[int | None] = mapped_column(ForeignKey("branches.id", ondelete="SET NULL"))
    grade: Mapped[str | None] = mapped_column(String(80))
    message: Mapped[str | None] = mapped_column(Text)
    before_json: Mapped[dict | None] = mapped_column(JSON)
    after_json: Mapped[dict | None] = mapped_column(JSON)
    created_transaction_id: Mapped[int | None] = mapped_column(ForeignKey("stock_transactions.id", ondelete="SET NULL"))
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    batch = relationship("ImportBatch")
    product = relationship("Product", foreign_keys=[product_id])
    branch = relationship("Branch")
    created_transaction = relationship("StockTransaction")

    __table_args__ = (
        CheckConstraint("status IN ('created', 'updated', 'stock_in', 'stock_out', 'skipped', 'warning', 'error', 'blocked', 'merged')", name="ck_import_batch_rows_status"),
    )


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
