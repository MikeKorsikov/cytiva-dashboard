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

# (company_id, ranking, year, value). Empty: the hand-entered values from 8 Nov 2026 were
# mockup values, not verified, and were removed on 19 Nov 2026. Every rank shows "To collect"
# until it is taken from the Forbes list itself.
CURATED_RANKINGS: tuple[tuple[str, str, int, str], ...] = ()


def load_curated_rankings(conn: sqlite3.Connection, run_id: int) -> int:
    """Store the curated rankings. Returns rows written. Earlier curated rows for this list are
    cleared first, so values removed from CURATED_RANKINGS do not stay in the database."""
    conn.execute(
        "DELETE FROM ranking WHERE ranking = ? AND source_type = 'curated'", (GLOBAL_2000,)
    )
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
