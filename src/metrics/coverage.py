"""Competitor coverage screen (screen 2): footprint matrix by company, region and product family."""

from __future__ import annotations

import sqlite3


def footprint_cells(conn: sqlite3.Connection) -> dict[tuple[str, str, str], dict]:
    """Stored cells keyed by (company, region, product family). A missing key is 'to collect'."""
    rows = conn.execute(
        "SELECT company_id, region_id, product_family, status, source_url FROM footprint"
    ).fetchall()
    return {
        (r["company_id"], r["region_id"], r["product_family"]): {
            "status": r["status"],
            "source_url": r["source_url"],
        }
        for r in rows
    }
