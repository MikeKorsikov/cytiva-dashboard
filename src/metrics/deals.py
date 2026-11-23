"""Deal counts by category for the Overview screen (tile 2).

Counts are lower bounds while the deal history is still building up (see src/ingest/deals.py).
"""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from src.domain.confidence import row_label, tile_label

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


def sheet_deals_12m(conn: sqlite3.Connection, acquirer: str, as_of: date) -> list[sqlite3.Row]:
    """The sheet's M&A deals for `acquirer` announced in the last 12 months (company-reported
    rows, source_type document). Feed deals are not here."""
    one_year = (as_of - timedelta(days=365)).isoformat()
    return conn.execute(
        "SELECT confidence, source_type_text, source_url FROM deal WHERE acquirer = ? "
        "AND category = 'M&A' AND status = 'announced' AND source_type = 'document' "
        "AND announced_date BETWEEN ? AND ?",
        (acquirer, one_year, as_of.isoformat()),
    ).fetchall()


def sheet_m_and_a_12m(conn: sqlite3.Connection, acquirer: str, as_of: date) -> int:
    """M&A announced in the last 12 months: the sheet's deals (T2 M&A), each counted once. Their
    badge is set by ma_basis. Feed deals are not counted here."""
    return len(sheet_deals_12m(conn, acquirer, as_of))


def ma_basis(conn: sqlite3.Connection, acquirer: str, as_of: date) -> str | None:
    """The count badge: the weakest badge of the deals the 12-month count is made of, each
    derived by the rule from its confidence and the type of its first source. None if no deal."""
    labels = [
        row_label(r["confidence"], r["source_type_text"])
        for r in sheet_deals_12m(conn, acquirer, as_of)
    ]
    return tile_label(labels)
