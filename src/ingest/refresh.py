"""Refresh job: populates the app database. Run from the repo root:

    uv run python -m src.ingest.refresh --trigger manual
    uv run python -m src.ingest.refresh --trigger scheduled

Each source loader is a function (conn, run_id) -> rows_written. Loaders are added
per source in later PRs. With no loaders registered, the job still creates the schema
and records a run, which is what the CI and scheduled workflow check.
"""

import argparse
import sqlite3
import sys
from collections.abc import Callable
from pathlib import Path

from src.ingest import store
from src.ingest.prices import load_share_prices

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = REPO_ROOT / "data" / "app.db"

Loader = Callable[[sqlite3.Connection, int], int]
LOADERS: list[Loader] = [load_share_prices]


def run(db_path: Path, trigger: str) -> int:
    """Run all loaders in one recorded run. Returns the number of rows written."""
    conn = store.connect(db_path)
    try:
        store.create_schema(conn)
        run_id = store.start_run(conn, trigger)
        rows_written = 0
        try:
            for loader in LOADERS:
                rows_written += loader(conn, run_id)
        except Exception as exc:
            store.finish_run(conn, run_id, "failed", rows_written, 0, error=str(exc))
            raise
        unverified = conn.execute(
            "SELECT COUNT(*) FROM change_log WHERE run_id = ? AND new_values LIKE '%unverified%'",
            (run_id,),
        ).fetchone()[0]
        store.finish_run(conn, run_id, "succeeded", rows_written, unverified)
        return rows_written
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Refresh the app database.")
    parser.add_argument("--trigger", choices=("scheduled", "manual"), default="manual")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    args = parser.parse_args(argv)
    rows = run(args.db, args.trigger)
    print(f"Refresh finished: {rows} rows written to {args.db}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
