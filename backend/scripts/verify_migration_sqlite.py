"""Exercise an Alembic upgrade locally without ever accepting a remote URL."""

import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from sqlalchemy import create_engine


def run_alembic(env: dict[str, str], *args: str) -> None:
    subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        check=True,
        env=env,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--from-revision", default="0011_invoice_returns")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="tile-index-migration-") as directory:
        database_path = Path(directory) / "migration_test.db"
        database_url = f"sqlite:///{database_path.as_posix()}"
        engine = create_engine(database_url)
        if engine.dialect.name != "sqlite":
            raise RuntimeError("Refusing migration verification: target is not SQLite")
        engine.dispose()

        env = os.environ.copy()
        env["DATABASE_URL"] = database_url
        env.setdefault("SECRET_KEY", "local-migration-verification-only")
        run_alembic(env, "upgrade", args.from_revision)
        run_alembic(env, "upgrade", "head")
        run_alembic(env, "downgrade", "-1")

        print(f"SQLite migration verification passed from {args.from_revision} through head and back")


if __name__ == "__main__":
    main()
