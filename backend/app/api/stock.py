from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.entities import Accessory, AccessoryInventory, Branch, Inventory, Product, TileRate, User
from app.services.accessory_labels import accessory_display_label


router = APIRouter(prefix="/stock", tags=["stock"])


@router.get("/overview")
def stock_overview(
    item_type: str = Query("all", pattern="^(all|tiles|accessories)$"),
    q: str | None = None,
    branch_id: int | None = None,
    grade: str | None = None,
    category: str | None = None,
    include_zero: bool = False,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    branches = db.scalars(select(Branch).order_by(Branch.name)).all()
    search_text = (q or "").strip().lower()
    return {
        "branches": [
            {"id": branch.id, "name": branch.name, "code": branch.code}
            for branch in branches
        ],
        "tiles": _tile_rows(db, branches, search_text, branch_id, grade, include_zero)
        if item_type in ("all", "tiles")
        else [],
        "accessories": _accessory_rows(db, branches, search_text, branch_id, category, include_zero)
        if item_type in ("all", "accessories")
        else [],
    }


@router.get("/item")
def stock_item(
    item_type: str = Query(pattern="^(tile|accessory)$"),
    product_id: int | None = None,
    accessory_id: int | None = None,
    grade: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    branches = db.scalars(select(Branch).order_by(Branch.name)).all()
    if item_type == "tile":
        if product_id is None or not grade:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="product_id and grade are required for tile stock",
            )
        product = db.get(Product, product_id)
        if not product or not product.active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
        return {
            "branches": _branch_rows(branches),
            "item": _tile_item_row(db, branches, product, grade),
        }

    if accessory_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="accessory_id is required for accessory stock",
        )
    accessory = db.get(Accessory, accessory_id)
    if not accessory or not accessory.active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Accessory not found")
    return {
        "branches": _branch_rows(branches),
        "item": _accessory_item_row(db, branches, accessory),
    }


def _branch_rows(branches):
    return [
        {"id": branch.id, "name": branch.name, "code": branch.code}
        for branch in branches
    ]


def _tile_item_row(db: Session, branches, product: Product, grade: str):
    inventory_rows = db.scalars(
        select(Inventory).where(
            Inventory.product_id == product.id,
            Inventory.grade == grade,
        )
    ).all()
    inventory_by_branch = {inv.branch_id: inv for inv in inventory_rows}
    branch_rows = []
    total_boxes = 0
    total_loose = 0
    for branch in branches:
        inv = inventory_by_branch.get(branch.id)
        boxes = int(inv.boxes if inv else 0)
        loose = int(inv.loose_pieces if inv else 0)
        pieces = boxes * int(product.pieces_per_box or 0) + loose
        total_boxes += boxes
        total_loose += loose
        branch_rows.append({
            "branch_id": branch.id,
            "branch_name": branch.name,
            "boxes": boxes,
            "loose_pieces": loose,
            "total_pieces": pieces,
            "rate_per_sqm": float(inv.rate_per_sqm if inv else 0),
            "rate_per_box": float(inv.rate_per_box if inv else 0),
            "rate_per_piece": float(inv.rate_per_piece if inv else 0),
        })

    return {
        "kind": "tile",
        "product_id": product.id,
        "product": product.name,
        "size": product.tile_size,
        "grade": grade,
        "pieces_per_box": product.pieces_per_box,
        "total_boxes": total_boxes,
        "total_loose_pieces": total_loose,
        "total_pieces": total_boxes * int(product.pieces_per_box or 0) + total_loose,
        "branches": branch_rows,
    }


def _accessory_item_row(db: Session, branches, accessory: Accessory):
    inventory_rows = db.scalars(
        select(AccessoryInventory).where(AccessoryInventory.accessory_id == accessory.id)
    ).all()
    inventory_by_branch = {inv.branch_id: inv for inv in inventory_rows}
    branch_rows = []
    total_quantity = 0
    for branch in branches:
        inv = inventory_by_branch.get(branch.id)
        quantity = int(inv.quantity if inv else 0)
        total_quantity += quantity
        branch_rows.append({
            "branch_id": branch.id,
            "branch_name": branch.name,
            "quantity": quantity,
        })

    return {
        "kind": "accessory",
        "accessory_id": accessory.id,
        "product": accessory_display_label(accessory),
        "category": accessory.category,
        "unit_price": float(accessory.unit_price or 0),
        "total_quantity": total_quantity,
        "branches": branch_rows,
    }


def _tile_rows(db: Session, branches, search_text: str, branch_id: int | None, grade_filter: str | None, include_zero: bool):
    products = db.scalars(select(Product).where(Product.active.is_(True)).order_by(Product.name, Product.tile_size)).all()
    rates = db.scalars(select(TileRate).where(TileRate.active.is_(True))).all()
    grades_by_size: dict[str, set[str]] = {}
    for rate in rates:
        grades_by_size.setdefault(rate.tile_size, set()).add(rate.grade)

    inventory_rows = db.scalars(select(Inventory)).all()
    inventory_by_key: dict[tuple[int, str, int], Inventory] = {}
    for inv in inventory_rows:
        inventory_by_key[(inv.product_id, inv.grade, inv.branch_id)] = inv

    rows = []
    for product in products:
        if search_text and search_text not in product.name.lower() and search_text not in product.tile_size.lower():
            continue
        grades = sorted(grades_by_size.get(product.tile_size) or {inv.grade for inv in inventory_rows if inv.product_id == product.id})
        if grade_filter:
            grades = [g for g in grades if g == grade_filter]
        for grade in grades:
            branch_rows = []
            total_boxes = 0
            total_loose = 0
            selected_branch_has_stock = branch_id is None
            for branch in branches:
                inv = inventory_by_key.get((product.id, grade, branch.id))
                boxes = int(inv.boxes if inv else 0)
                loose = int(inv.loose_pieces if inv else 0)
                pieces = boxes * int(product.pieces_per_box or 0) + loose
                total_boxes += boxes
                total_loose += loose
                if branch_id == branch.id and pieces > 0:
                    selected_branch_has_stock = True
                branch_rows.append({
                    "branch_id": branch.id,
                    "branch_name": branch.name,
                    "boxes": boxes,
                    "loose_pieces": loose,
                    "total_pieces": pieces,
                    "rate_per_sqm": float(inv.rate_per_sqm if inv else 0),
                    "rate_per_box": float(inv.rate_per_box if inv else 0),
                    "rate_per_piece": float(inv.rate_per_piece if inv else 0),
                })

            total_pieces = total_boxes * int(product.pieces_per_box or 0) + total_loose
            if not include_zero and total_pieces <= 0:
                continue
            if branch_id is not None and not include_zero and not selected_branch_has_stock:
                continue

            rows.append({
                "kind": "tile",
                "product_id": product.id,
                "product": product.name,
                "size": product.tile_size,
                "grade": grade,
                "pieces_per_box": product.pieces_per_box,
                "total_boxes": total_boxes,
                "total_loose_pieces": total_loose,
                "total_pieces": total_pieces,
                "branches": branch_rows,
            })
    return rows


def _accessory_rows(db: Session, branches, search_text: str, branch_id: int | None, category_filter: str | None, include_zero: bool):
    accessories = db.scalars(select(Accessory).where(Accessory.active.is_(True)).order_by(Accessory.category, Accessory.company, Accessory.product_name, Accessory.colour, Accessory.size)).all()
    inventory_rows = db.scalars(select(AccessoryInventory)).all()
    inventory_by_key: dict[tuple[int, int], AccessoryInventory] = {}
    for inv in inventory_rows:
        inventory_by_key[(inv.accessory_id, inv.branch_id)] = inv

    rows = []
    for accessory in accessories:
        label = accessory_display_label(accessory)
        if category_filter and accessory.category != category_filter:
            continue
        if search_text and search_text not in label.lower() and search_text not in (accessory.category or "").lower():
            continue

        branch_rows = []
        total_quantity = 0
        selected_branch_has_stock = branch_id is None
        for branch in branches:
            inv = inventory_by_key.get((accessory.id, branch.id))
            quantity = int(inv.quantity if inv else 0)
            total_quantity += quantity
            if branch_id == branch.id and quantity > 0:
                selected_branch_has_stock = True
            branch_rows.append({
                "branch_id": branch.id,
                "branch_name": branch.name,
                "quantity": quantity,
            })

        if not include_zero and total_quantity <= 0:
            continue
        if branch_id is not None and not include_zero and not selected_branch_has_stock:
            continue

        rows.append({
            "kind": "accessory",
            "accessory_id": accessory.id,
            "product": label,
            "category": accessory.category,
            "unit_price": float(accessory.unit_price or 0),
            "total_quantity": total_quantity,
            "branches": branch_rows,
        })
    return rows
