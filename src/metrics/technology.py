"""Technology screen metrics: end-of-support register (CD-29) and incidents (CD-30)."""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta


def estate_register(conn: sqlite3.Connection) -> list[dict]:
    """Estate items with their vendor status and source, ordered by product."""
    rows = conn.execute(
        "SELECT product, where_used, vendor_support_status, source_url, evidence_label "
        "FROM estate_item ORDER BY product"
    ).fetchall()
    return [dict(r) for r in rows]


def recent_incidents(conn: sqlite3.Connection, as_of: date, days: int = 30) -> list[dict]:
    """Estate incidents whose date falls in the rolling window ending on `as_of`."""
    start = (as_of - timedelta(days=days)).isoformat()
    rows = conn.execute(
        "SELECT incident_date, vendor, title, cve, estate_link, source_url FROM incident "
        "WHERE incident_date BETWEEN ? AND ? ORDER BY incident_date DESC",
        (start, as_of.isoformat()),
    ).fetchall()
    return [dict(r) for r in rows]


def last_successful_check(conn: sqlite3.Connection) -> str | None:
    """Finish time of the last refresh run that succeeded (the date the sources were read)."""
    row = conn.execute(
        "SELECT MAX(finished_at) AS finished FROM refresh_run WHERE status = 'succeeded'"
    ).fetchone()
    return row["finished"] if row and row["finished"] else None
