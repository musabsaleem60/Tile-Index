from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class BranchOut(ORMModel):
    id: int
    name: str
    code: str
    created_at: datetime | None = None


class UserOut(ORMModel):
    id: int
    username: str
    role: str
    branch_id: int | None = None
    is_active: bool
    created_at: datetime | None = None


class ProductIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    tile_size: str = Field(min_length=1, max_length=80)
    area_per_box: float = Field(gt=0)
    pieces_per_box: int = Field(gt=0)


class ProductOut(ProductIn, ORMModel):
    id: int
    created_at: datetime | None = None


class AccessoryIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    category: str = Field(min_length=1, max_length=80)
    company: str = Field(min_length=1, max_length=160)
    unit_price: float = Field(ge=0)


class AccessoryOut(AccessoryIn, ORMModel):
    id: int
    created_at: datetime | None = None


class SanitaryProductIn(BaseModel):
    company_name: str = Field(min_length=1, max_length=160)
    product_category: str = Field(min_length=1, max_length=160)
    color: str = Field(min_length=1, max_length=80)
    purchase_price: float = Field(ge=0)
    sale_price: float = Field(ge=0)
    sku: str = Field(min_length=1, max_length=160)


class SanitaryProductOut(SanitaryProductIn, ORMModel):
    id: int
    created_at: datetime | None = None


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=8, max_length=128)
    role: str
    branch_id: int | None = None
    is_active: bool = True


class UserUpdate(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    role: str
    branch_id: int | None = None
    is_active: bool = True


class StockInRequest(BaseModel):
    branch_id: int
    product_id: int
    grade: str
    boxes: int = Field(ge=0)
    loose_pieces: int = Field(ge=0)
    rate_per_sqm: float = Field(ge=0)
    rate_per_box: float = Field(ge=0)
    rate_per_piece: float = Field(ge=0)
    notes: str | None = None


class SimpleQuantityRequest(BaseModel):
    branch_id: int
    quantity: int = Field(gt=0)
    notes: str | None = None


class InventoryOut(ORMModel):
    id: int
    branch_id: int
    product_id: int
    grade: str
    boxes: int
    loose_pieces: int
    rate_per_sqm: float
    rate_per_box: float
    rate_per_piece: float
    updated_at: datetime | None = None


class AccessoryInventoryOut(ORMModel):
    id: int
    branch_id: int
    accessory_id: int
    quantity: int
    updated_at: datetime | None = None


class SanitaryInventoryOut(ORMModel):
    id: int
    branch_id: int
    sanitary_product_id: int
    quantity: int
    updated_at: datetime | None = None


class InvoiceItemIn(BaseModel):
    item_type: str
    product_id: int | None = None
    accessory_id: int | None = None
    sanitary_product_id: int | None = None
    grade: str | None = None
    boxes: int = Field(default=0, ge=0)
    loose_pieces: int = Field(default=0, ge=0)
    quantity: int = Field(default=0, ge=0)


class InvoiceCreate(BaseModel):
    branch_id: int
    customer_name: str = Field(min_length=1, max_length=160)
    customer_contact: str | None = None
    discount: float = Field(default=0, ge=0)
    paid_amount: float = Field(default=0, ge=0)
    items: list[InvoiceItemIn]


class InvoiceItemOut(ORMModel):
    id: int
    product_id: int | None = None
    accessory_id: int | None = None
    sanitary_product_id: int | None = None
    item_type: str
    description: str
    tile_size: str | None = None
    grade: str | None = None
    boxes: int
    loose_pieces: int
    quantity: int
    rate_per_box: float
    rate_per_piece: float
    unit_price: float
    line_total: float


class InvoiceOut(ORMModel):
    id: int
    branch_id: int
    user_id: int | None = None
    invoice_number: str
    customer_name: str
    customer_contact: str | None = None
    invoice_date: datetime
    subtotal: float
    discount: float
    grand_total: float
    paid_amount: float
    balance: float
    items: list[InvoiceItemOut] = []


class UpdateInfo(BaseModel):
    latest_version: str
    download_url: str
    release_notes: str
