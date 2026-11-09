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


def _table_layout(conn: sqlite3.Connection, name: str) -> tuple[list[str], tuple[str, ...]] | None:
    rows = conn.execute(f"PRAGMA table_info({name})").fetchall()
    if not rows:
        return None
    key = tuple(r["name"] for r in sorted((r for r in rows if r["pk"]), key=lambda r: r["pk"]))
    return [r["name"] for r in rows], key


# Columns that every stored record must carry; a migrated row without them is not kept.
_SOURCE_COLUMNS = {
    "source_url",
    "source_type",
    "evidence_label",
    "loaded_at",
    "verification_status",
}


def _default_for(column_type: str) -> str:
    """Value used when a new NOT NULL column is filled for rows loaded under the old layout."""
    upper = column_type.upper()
    if "INT" in upper:
        return "0"
    if "REAL" in upper:
        return "0.0"
    return "''"


def _migrate_table(
    conn: sqlite3.Connection,
    name: str,
    columns: dict[str, str],
    key: tuple[str, ...] | None,
) -> dict | None:
    """Make an existing table match the schema, keeping its rows. Returns a change record if the
    layout was changed, or None. A table that does not exist is created with no change record."""
    layout = _table_layout(conn, name)
    if layout is None:
        conn.execute(_create_table_sql(name, columns, key))
        return None
    old_columns, old_key = layout
    expected_key = key or tuple(c for c, t in columns.items() if "PRIMARY KEY" in t.upper())
    if set(old_columns) == set(columns) and old_key == expected_key:
        return None

    rows_before = conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
    tmp = f"{name}__migrate"
    conn.execute(f"DROP TABLE IF EXISTS {tmp}")
    conn.execute(_create_table_sql(tmp, columns, key))
    # Columns the old table has are copied. A new column with a SQL default takes that default.
    # A new column without one is filled (NOT NULL) or left NULL; a source column is never filled.
    insert_columns: list[str] = []
    select: list[str] = []
    for column, column_type in columns.items():
        if column in old_columns:
            insert_columns.append(column)
            select.append(column)
        elif column in _SOURCE_COLUMNS:
            insert_columns.append(column)
            select.append("NULL")  # a row without its source is dropped, not filled in
        elif "DEFAULT" in column_type.upper():
            continue
        elif "NOT NULL" in column_type.upper():
            insert_columns.append(column)
            select.append(_default_for(column_type))
    # OR IGNORE drops rows that the new key or NOT NULL rules reject; the counts record that.
    conn.execute(
        f"INSERT OR IGNORE INTO {tmp} ({', '.join(insert_columns)}) "
        f"SELECT {', '.join(select)} FROM {name}"
    )
    conn.execute(f"DROP TABLE {name}")
    conn.execute(f"ALTER TABLE {tmp} RENAME TO {name}")
    rows_after = conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
    return {
        "table": name,
        "rows_before": rows_before,
        "rows_after": rows_after,
        "added_columns": sorted(set(columns) - set(old_columns)),
        "removed_columns": sorted(set(old_columns) - set(columns)),
    }


def create_schema(conn: sqlite3.Connection) -> list[dict]:
    """Create each table, or migrate it to the current layout, keeping its rows.

    Returns one record per table whose layout changed, so the refresh can log them. Safe to run
    on each refresh: a table that already matches is left alone."""
    changes = []
    for table in TABLES:
        change = _migrate_table(conn, table.name, {**table.columns, **COMMON_COLUMNS}, table.key)
        if change:
            changes.append(change)
    for name, columns in ((RUN_TABLE, RUN_COLUMNS), (CHANGE_TABLE, CHANGE_COLUMNS)):
        change = _migrate_table(conn, name, columns, None)
        if change:
            changes.append(change)
    conn.commit()
    return changes


def log_migration(conn: sqlite3.Connection, run_id: int, change: dict) -> None:
    """Record a table layout change in the change log."""
    _log_change(conn, run_id, change["table"], {"table": change["table"]}, "migrated", None, change)


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


def log_delete(
    conn: sqlite3.Connection, run_id: int, table_name: str, key_values: dict, old: dict
) -> None:
    """Record a row removed by a rule change, so the removal can be found and reversed."""
    _log_change(conn, run_id, table_name, key_values, "deleted", old, {})
