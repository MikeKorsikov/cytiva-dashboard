"""Technology screen metrics: the end-of-support register (CD-29)."""

from __future__ import annotations

import sqlite3


def estate_register(conn: sqlite3.Connection) -> list[dict]:
    """Estate items with their vendor status and source, ordered by product."""
    rows = conn.execute(
        "SELECT product, where_used, vendor_support_status, source_url, evidence_label "
        "FROM estate_item ORDER BY product"
    ).fetchall()
    return [dict(r) for r in rows]
