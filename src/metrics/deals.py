"""Deal counts by category for the Overview screen (tile 2).

Counts are lower bounds while the deal history is still building up (see src/ingest/deals.py).
"""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta

CATEGORIES = ("M&A", "Licensing", "Collaboration")


def deal_counts(conn: sqlite3.Connection, acquirer: str, as_of: date) -> dict[str, dict[str, int]]:
    """Announced deals by `acquirer` per category, in the last 12 months and the last 5 years."""
    one_year = (as_of - timedelta(days=365)).isoformat()
    five_years = (as_of - timedelta(days=365 * 5)).isoformat()
    rows = conn.execute(
        """
        SELECT category,
               SUM(CASE WHEN announced_date >= ? THEN 1 ELSE 0 END) AS last_12m,
               COUNT(*) AS last_5y
        FROM deal
        WHERE acquirer = ? AND status = 'announced'
          AND announced_date BETWEEN ? AND ?
        GROUP BY category
        """,
        (one_year, acquirer, five_years, as_of.isoformat()),
    ).fetchall()
    counts = {c: {"last_12m": 0, "last_5y": 0} for c in CATEGORIES}
    for r in rows:
        counts[r["category"]] = {"last_12m": int(r["last_12m"] or 0), "last_5y": int(r["last_5y"])}
    return counts
