"""Find and optionally clamp invoice overpayment residue.

Dry-run by default. With --commit, only invoices where paid_amount exceeds
grand_total by less than Rs. 1 are clamped to paid_amount == grand_total.
Real overpayments are always reported and left untouched.
"""

from __future__ import annotations

import argparse
import os
from decimal import Decimal

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session


RESIDUE_THRESHOLD = Decimal("1")


def money(value) -> Decimal:
    return Decimal(str(value or 0))


def main() -> int:
    parser = argparse.ArgumentParser(description="Dry-run or clamp invoice overpayment residue.")
    parser.add_argument("--commit", action="store_true", help="Apply only floating-point residue fixes.")
    args = parser.parse_args()

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is required")
    engine = create_engine(database_url)

    with Session(engine) as db:
        rows = db.execute(
            text(
                """
                SELECT id, invoice_number, customer_name, grand_total, paid_amount, balance
                FROM invoices
                WHERE paid_amount > grand_total
                ORDER BY id
                """
            )
        ).mappings().all()

        residue_rows = []
        real_rows = []
        for row in rows:
            difference = money(row["paid_amount"]) - money(row["grand_total"])
            result = dict(row)
            result["difference"] = difference
            if difference < RESIDUE_THRESHOLD:
                residue_rows.append(result)
            else:
                real_rows.append(result)

        print(f"mode={'COMMIT' if args.commit else 'DRY RUN'}")
        print(f"overpaid invoices found: {len(rows)}")
        print(f"floating-point residue fixes: {len(residue_rows)}")
        for row in residue_rows:
            print(
                "RESIDUE "
                f"{row['invoice_number']} | customer={row['customer_name']} | "
                f"paid={row['paid_amount']} | total={row['grand_total']} | "
                f"difference={row['difference']} | would_set paid_amount={row['grand_total']}, balance=0"
            )

        print(f"real overpayments requiring manual decision: {len(real_rows)}")
        for row in real_rows:
            print(
                "MANUAL "
                f"{row['invoice_number']} | customer={row['customer_name']} | "
                f"paid={row['paid_amount']} | total={row['grand_total']} | "
                f"difference={row['difference']} | untouched"
            )

        if args.commit and residue_rows:
            for row in residue_rows:
                db.execute(
                    text(
                        """
                        UPDATE invoices
                        SET paid_amount = grand_total,
                            balance = 0
                        WHERE id = :invoice_id
                        """
                    ),
                    {"invoice_id": row["id"]},
                )
            db.commit()
            print(f"committed residue fixes: {len(residue_rows)}")
        elif args.commit:
            print("committed residue fixes: 0")
        else:
            print("no changes written")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
