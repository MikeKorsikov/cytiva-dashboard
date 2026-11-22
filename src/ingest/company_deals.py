"""Deals reported by the companies themselves (evidence label Fact), entered by hand.

Each row comes from a company release, an exchange filing or a company's own news page, and
carries that page's URL. The date is the date the source gives for the announcement or the
completion, as stated in the note beside each row. A deal that is in news headlines and here
is counted once: the news row is removed on the next run (see deals.revalidate_stored).

Only deals the sources state are listed. Values the sources do not give are left empty; they
are never estimated. Other 2021 to 2026 deals that the 10-K describes only as totals are not
listed here.
"""

from __future__ import annotations

import re
import sqlite3

from src.ingest import store
from src.ingest.sheet_headers import DATA_ROOT, read_tab

MA_FILE = DATA_ROOT / "overview" / "sheet" / "t2_ma.csv"
SOURCES_FILE = DATA_ROOT / "overview" / "sheet" / "sources.csv"
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def sheet_deals() -> list[dict]:
    """The M&A rows of the sheet's T2 tab, with the URL of their first source. Deal talk (not a
    deal) and the count rows are not deals and are not returned."""
    urls = {r["id"]: r["url"] for r in read_tab(SOURCES_FILE).rows["source"]}
    deals = []
    for r in read_tab(MA_FILE).rows["ma"]:
        if not re.fullmatch(r"MA-\d+", r["id"]) or r["type"] != "M&A":
            continue
        ids = [i.strip() for i in re.split(r"[,;]", r["source_ids"]) if i.strip()]
        completed = r["completed"] if DATE.fullmatch(r["completed"]) else None
        # A completed deal cites its completion source (the last ID); otherwise the announcement.
        source_id = ids[-1] if completed else ids[0]
        if source_id not in urls:
            raise ValueError(f"{r['id']}: source {source_id!r} is not in the Overview Sources tab")
        deals.append(
            {
                "id": r["id"],
                "acquirer": r["buyer"],
                "headline": f"{r['buyer']} to acquire {r['target']}",
                "announced": r["announced"],
                "completed": completed,
                "value_text": r["value"],
                # Every row is an announced deal (the tile counts announced deals). Completion is
                # kept in completed_date; a blank or pending completion leaves it empty.
                "status": "announced",
                "source_url": urls[source_id],
            }
        )
    return deals


# Danaher FY2025 Form 10-K (acquisitions, three years to 31 Dec 2025). Source of the values below.
DANAHER_10K_URL = (
    "https://www.sec.gov/Archives/edgar/data/313616/000031361626000062/dhr-20251231.htm"
)

# Statements from the 10-K that are not single dated deals. Stored as sourced notes for the
# Overview M&A tile; not counted as deals.
DANAHER_10K_NOTES: tuple[str, ...] = (
    "FY2025 10-K: no acquisitions in 2025.",
    "FY2024 10-K: three businesses acquired for $558 million in cash, net of cash acquired, "
    "complementing Life Sciences ($305 million goodwill). The 10-K does not name or date them, "
    "so they are not counted as individual deals.",
    "Abcam (acquired 6 Dec 2023): cash purchase price of approximately $5.6 billion; about "
    "$3.9 billion of goodwill; now part of Life Sciences.",
)


def load_company_deals(conn: sqlite3.Connection, run_id: int) -> int:
    """Store the company-reported deals from the sheet, and the 10-K notes. Returns rows written.
    Earlier company-reported deals are cleared first (news deals have source_type news)."""
    conn.execute("DELETE FROM deal WHERE source_type = 'document' AND evidence_label = 'Fact'")
    written = 0
    for d in sheet_deals():
        row = {
            "acquirer": d["acquirer"],
            "announced_date": d["announced"],
            "category": "M&A",
            "headline": d["headline"],
            "value_usd": None,  # the sheet gives values as text; they are not converted here
            "value_text": d["value_text"],
            "completed_date": d["completed"],
            "status": d["status"],
            "source_url": d["source_url"],
            "source_type": "document",  # company release or filing
            "published_date": d["announced"],
            "evidence_label": "Fact",
        }
        if store.upsert(conn, run_id, "deal", row) != "rejected":
            written += 1
    for text in DANAHER_10K_NOTES:
        conn.execute(
            "INSERT OR REPLACE INTO screen_notes (tab, label, text, source_url, source_type, "
            "loaded_at, evidence_label, verification_status) VALUES (?, ?, ?, ?, 'document', ?, "
            "'Signal', 'passed')",
            ("Overview M&A", "Danaher FY2025 10-K", text, DANAHER_10K_URL, store.now_iso()),
        )
    conn.commit()
    return written
