"""Create a compressed, complete row snapshot of the configured database."""

import argparse
import gzip
import json
import os
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import MetaData, create_engine, inspect, select


def json_value(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, bytes):
        return {"__bytes_hex__": value.hex()}
    return value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is not set")

    engine = create_engine(database_url)
    metadata = MetaData()
    metadata.reflect(bind=engine)
    table_names = sorted(inspect(engine).get_table_names())
    payload = {
        "format": "tile-index-full-row-snapshot-v1",
        "created_at": datetime.now().astimezone().isoformat(),
        "tables": {},
    }
    with engine.connect() as connection:
        for table_name in table_names:
            table = metadata.tables[table_name]
            rows = connection.execute(select(table)).mappings().all()
            payload["tables"][table_name] = {
                "columns": [column.name for column in table.columns],
                "row_count": len(rows),
                "rows": [
                    {key: json_value(value) for key, value in row.items()}
                    for row in rows
                ],
            }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(args.output, "wt", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=True)
    engine.dispose()
    print(json.dumps({
        "path": str(args.output.resolve()),
        "size_bytes": args.output.stat().st_size,
        "tables": len(table_names),
        "total_rows": sum(table["row_count"] for table in payload["tables"].values()),
    }))


if __name__ == "__main__":
    main()
