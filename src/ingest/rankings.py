"""Curated rankings for the Overview page (internal, entered by hand).

Values are entered manually from the published list and stored with their source page and the
date entered. Nothing is fetched from the source at refresh time. Each value should be checked
against the source page when entered; the entry date is kept with it.
"""

from __future__ import annotations

import sqlite3

from src.ingest import store

GLOBAL_2000 = "Forbes Global 2000"
GLOBAL_2000_URL = "https://www.forbes.com/lists/global2000/"
ENTERED_ON = "2026-11-08"

# (company_id, ranking, year, value). Only companies with a rank are listed; others show n/d.
CURATED_RANKINGS: tuple[tuple[str, str, int, str], ...] = (
    ("Thermo Fisher", GLOBAL_2000, 2026, "155"),
    ("Thermo Fisher", GLOBAL_2000, 2025, "148"),
    ("Danaher", GLOBAL_2000, 2026, "267"),
    ("Danaher", GLOBAL_2000, 2025, "241"),
    ("Merck KGaA", GLOBAL_2000, 2026, "345"),  # group rank, shown as for Danaher group
    ("Merck KGaA", GLOBAL_2000, 2025, "339"),
)


def load_curated_rankings(conn: sqlite3.Connection, run_id: int) -> int:
    """Store the curated rankings. Returns rows written."""
    written = 0
    for company_id, ranking, year, value in CURATED_RANKINGS:
        row = {
            "company_id": company_id,
            "ranking": ranking,
            "year": year,
            "value": value,
            "source_url": GLOBAL_2000_URL,
            "source_type": "curated",
            "published_date": ENTERED_ON,
            "evidence_label": "Fact",
        }
        if store.upsert(conn, run_id, "ranking", row) != "rejected":
            written += 1
    return written
