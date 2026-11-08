"""SQLite access for the app database: schema creation, upserts and the change log."""

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from src.ingest.checks import check_quote, check_source, verdict
from src.ingest.schema import (
    CHANGE_COLUMNS,
    CHANGE_TABLE,
    COMMON_COLUMNS,
    RUN_COLUMNS,
    RUN_TABLE,
    TABLES,
    table_by_name,
)


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _create_table_sql(name: str, columns: dict[str, str], key: tuple[str, ...] | None) -> str:
    cols = [f"{col} {typ}" for col, typ in columns.items()]
    if key:
        cols.append(f"PRIMARY KEY ({', '.join(key)})")
    return f"CREATE TABLE IF NOT EXISTS {name} ({', '.join(cols)})"


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_schema(conn: sqlite3.Connection) -> None:
    """Create every table if it does not exist. Safe to run on each refresh."""
    for table in TABLES:
        columns = {**table.columns, **COMMON_COLUMNS}
        conn.execute(_create_table_sql(table.name, columns, table.key))
    conn.execute(_create_table_sql(RUN_TABLE, RUN_COLUMNS, None))
    conn.execute(_create_table_sql(CHANGE_TABLE, CHANGE_COLUMNS, None))
    conn.commit()


def start_run(conn: sqlite3.Connection, trigger: str) -> int:
    cur = conn.execute(
        f"INSERT INTO {RUN_TABLE} (trigger, started_at, status) VALUES (?, ?, 'running')",
        (trigger, now_iso()),
    )
    conn.commit()
    return int(cur.lastrowid)


def finish_run(
    conn: sqlite3.Connection,
    run_id: int,
    status: str,
    rows_written: int,
    rows_unverified: int,
    error: str | None = None,
) -> None:
    conn.execute(
        f"UPDATE {RUN_TABLE} SET finished_at = ?, status = ?, rows_written = ?, "
        "rows_unverified = ?, error = ? WHERE run_id = ?",
        (now_iso(), status, rows_written, rows_unverified, error, run_id),
    )
    conn.commit()


def upsert(
    conn: sqlite3.Connection,
    run_id: int,
    table_name: str,
    row: dict,
    *,
    source_text: str | None = None,
    quote_columns: tuple[str, ...] = (),
    extra_problems: list[str] | None = None,
) -> str:
    """Insert or update one record after running the source check and quote checks.

    `quote_columns` lists the numeric columns that must appear in `source_text`.
    Returns "passed", "unverified" or "rejected". A record without a valid source is
    rejected and not written (CLAUDE.md, AI-populated data, check 1). Other failures are
    stored as "unverified". Every insert or change is written to the change log.
    """
    table = table_by_name(table_name)
    source_problems = check_source(
        row.get("source_url"), row.get("source_type", ""), row.get("evidence_label", "")
    )
    if source_problems:
        return "rejected"

    problems: list[str] = list(extra_problems or [])
    for column in quote_columns:
        problems += check_quote(str(row.get(column, "")), source_text)
    result = verdict(problems)

    values = {col: row.get(col) for col in table.columns}
    values.update(
        {
            "source_url": row.get("source_url"),
            "source_type": row.get("source_type"),
            "published_date": row.get("published_date"),
            "loaded_at": now_iso(),
            "evidence_label": row.get("evidence_label"),
            "is_sample": int(bool(row.get("is_sample", False))),
            "verification_status": "passed" if result.passed else "unverified",
            "check_notes": "; ".join(result.notes) or None,
        }
    )

    key_values = {k: row[k] for k in table.key}
    where = " AND ".join(f"{k} = ?" for k in table.key)
    existing = conn.execute(
        f"SELECT * FROM {table.name} WHERE {where}", tuple(key_values.values())
    ).fetchone()

    if existing is None:
        cols = ", ".join(values)
        marks = ", ".join("?" for _ in values)
        conn.execute(f"INSERT INTO {table.name} ({cols}) VALUES ({marks})", tuple(values.values()))
        _log_change(conn, run_id, table.name, key_values, "insert", None, values)
    else:
        old = {k: existing[k] for k in values}
        if _differs(old, values):
            sets = ", ".join(f"{k} = ?" for k in values)
            conn.execute(
                f"UPDATE {table.name} SET {sets} WHERE {where}",
                (*values.values(), *key_values.values()),
            )
            _log_change(conn, run_id, table.name, key_values, "update", old, values)

    conn.commit()
    return "passed" if result.passed else "unverified"


def _differs(old: dict, new: dict) -> bool:
    ignore = {"loaded_at"}
    return any(old.get(k) != v for k, v in new.items() if k not in ignore)


def _log_change(
    conn: sqlite3.Connection,
    run_id: int,
    table_name: str,
    key_values: dict,
    action: str,
    old: dict | None,
    new: dict,
) -> None:
    conn.execute(
        f"INSERT INTO {CHANGE_TABLE} "
        "(run_id, table_name, row_key, action, old_values, new_values, changed_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            run_id,
            table_name,
            json.dumps(key_values, sort_keys=True, default=str),
            action,
            json.dumps(old, default=str) if old is not None else None,
            json.dumps(new, default=str),
            now_iso(),
        ),
    )
