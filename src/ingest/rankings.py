"""Curated rankings for the Overview page, from the sheet's T1 Rankings tab.

The tab is read through its section map (src/ingest/sheet_headers.py). Each value is stored with
its source URL; a value without a URL is rejected by store.upsert. Nothing is fetched at refresh
time. The sheet holds no values yet, so every rank shows "To collect".
"""

from __future__ import annotations

import re
import sqlite3

from src.ingest import store
from src.ingest.sheet_headers import DATA_ROOT, read_tab

RANKINGS_FILE = DATA_ROOT / "overview" / "sheet" / "t1_rankings.csv"
GLOBAL_2000 = "Forbes Global 2000"

# Sheet column -> (ranking name, year). The company rows come from the Company column.
VALUE_COLUMNS: dict[str, tuple[str, int | None]] = {
    "forbes_2026": (GLOBAL_2000, 2026),
    "forbes_2025": (GLOBAL_2000, 2025),
    "sp_rating": ("S&P long-term rating", None),
    "fortune_500": ("Fortune Global 500", None),
    "ecovadis": ("EcoVadis", None),
}
RANKING_NAMES = tuple({name for name, _ in VALUE_COLUMNS.values()})


def load_curated_rankings(conn: sqlite3.Connection, run_id: int) -> int:
    """Store the sheet's ranking values. Returns rows written. Earlier curated rows for these
    rankings are cleared first, so values removed from the sheet do not stay in the database."""
    placeholders = ",".join("?" * len(RANKING_NAMES))
    conn.execute(
        f"DELETE FROM ranking WHERE source_type = 'curated' AND ranking IN ({placeholders})",
        RANKING_NAMES,
    )
    written = 0
    for r in read_tab(RANKINGS_FILE).rows["rankings"]:
        if not re.fullmatch(r"RK-\d+", r["id"]):
            continue
        for field, (ranking, year) in VALUE_COLUMNS.items():
            if not r[field]:
                continue
            row = {
                "company_id": r["company"],
                "ranking": ranking,
                "year": year,
                "value": r[field],
                "source_url": r["source"] if r["source"].startswith("http") else "",
                "source_type": "curated",
                "published_date": None,
                "evidence_label": "Fact",
            }
            if store.upsert(conn, run_id, "ranking", row) != "rejected":
                written += 1
    return written
