import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.api.returns import search_returns
from app.models.base import Base
from app.models.entities import Branch, Invoice, InvoiceReturn, User
from app.schemas.common import ReturnSettlementIn
from app.services.returns import add_settlement, get_return


def test_return_search_filters_and_branch_access():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        first = Branch(name="Tile Index - Korangi", code="TIK")
        second = Branch(name="DHA", code="DHA")
        employee = User(username="employee", password_hash="x", role="employee", branch=first, is_active=True)
        db.add_all([first, second, employee])
        db.flush()
        invoice = Invoice(
            branch_id=first.id, user_id=employee.id, invoice_number="TIK-0042",
            customer_name="Return Customer", subtotal=100, grand_total=100,
            paid_amount=100, balance=0, status="active",
        )
        db.add(invoice)
        db.flush()
        first_return = InvoiceReturn(
            return_number="RET-0042", invoice_id=invoice.id, branch_id=first.id,
            user_id=employee.id, return_date=datetime(2026, 9, 25, 10, tzinfo=timezone.utc),
            reason="test return", returned_value=100, exchange_value=40,
            difference_amount=60, status="completed",
        )
        db.add(first_return)
        other_invoice = Invoice(
            branch_id=second.id, user_id=employee.id, invoice_number="DHA-0007",
            customer_name="Other Customer", subtotal=50, grand_total=50,
            paid_amount=50, balance=0, status="active",
        )
        db.add(other_invoice)
        db.flush()
        db.add(InvoiceReturn(
            return_number="RET-0007", invoice_id=other_invoice.id, branch_id=second.id,
            user_id=employee.id, return_date=datetime(2026, 9, 24, 10, tzinfo=timezone.utc),
            reason="other return", returned_value=50, exchange_value=50,
            difference_amount=0, status="completed",
        ))
        db.commit()

        rows = search_returns(
            branch_id=None, date_from=None, date_to=None, return_number="0042",
            invoice_number="TIK", db=db, current_user=employee,
        )
        assert len(rows) == 1
        assert rows[0]["return_number"] == "RET-0042"
        assert rows[0]["invoice_number"] == "TIK-0042"
        assert rows[0]["customer_name"] == "Return Customer"
        assert rows[0]["settlement_status"] == "Outstanding"

        add_settlement(db, first_return.id, ReturnSettlementIn(
            amount=60, direction="refund_to_customer",
            settlement_date=datetime(2026, 9, 25, 12, tzinfo=timezone.utc), method="cash",
        ), employee)
        db.commit()
        db.expire_all()
        settled = get_return(db, first_return.id)
        assert settled["outstanding_amount"] == 0

        all_branch_employee = User(username="all", password_hash="x", role="employee", branch_id=None, is_active=True)
        db.add(all_branch_employee)
        db.commit()
        all_rows = search_returns(
            branch_id=None, date_from=None, date_to=None, return_number=None,
            invoice_number=None, db=db, current_user=all_branch_employee,
        )
        assert {row["return_number"] for row in all_rows} == {"RET-0042", "RET-0007"}
