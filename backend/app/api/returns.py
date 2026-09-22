from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import ensure_branch_access, get_current_user
from app.db.session import get_db
from app.models.entities import InvoiceReturn, User
from app.schemas.common import InvoiceReturnOut, ReturnSettlementIn
from app.services.returns import add_settlement, get_return


router = APIRouter(prefix="/returns", tags=["returns"])


@router.get("/{return_id}", response_model=InvoiceReturnOut)
def detail(return_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    record = db.get(InvoiceReturn, return_id)
    if not record:
        raise HTTPException(status_code=404, detail="Return not found")
    ensure_branch_access(current_user, record.branch_id)
    return get_return(db, return_id)


@router.post("/{return_id}/settlements", response_model=InvoiceReturnOut)
def settle(
    return_id: int,
    payload: ReturnSettlementIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = db.get(InvoiceReturn, return_id)
    if not record:
        raise HTTPException(status_code=404, detail="Return not found")
    ensure_branch_access(current_user, record.branch_id)
    result = add_settlement(db, return_id, payload, current_user)
    db.commit()
    return result
