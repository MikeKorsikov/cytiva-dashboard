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

import sqlite3

from src.ingest import store

# (company_id, date, category, headline, source URL)
COMPANY_DEALS: tuple[tuple[str, str, str, str, str], ...] = (
    (
        "Danaher",
        "2026-02-17",
        "M&A",
        "Danaher to acquire Masimo Corporation (completed 10 Jun 2026)",
        "https://www.biospace.com/press-releases/danaher-to-acquire-masimo-corporation",
    ),
    (
        "Danaher",
        "2026-09-28",
        "M&A",
        "Leica Biosystems (Danaher) completes acquisition of StatLab Medical Products",
        "https://www.biospace.com/press-releases/leica-biosystems-completes-acquisition-of-statlab-to-bolster-delivery-of-more-precise-timely-diagnostics-for-cancer-patients",
    ),
    (
        "Danaher",
        "2024-08-19",
        "M&A",
        "Danaher acquires Genedata AG",
        "https://www.genedata.com/company/news/details/press-release/genedata-joins-danaher-corporation",
    ),
    (
        "Danaher",
        "2023-12-06",
        "M&A",
        "Danaher completes acquisition of Abcam plc ($24.00 per share)",
        "https://investors.danaher.com/2023-12-06-Danaher-Completes-Acquisition-of-Abcam",
    ),
    (
        "Danaher",
        "2021-08-30",
        "M&A",
        "Danaher completes acquisition of Aldevron",
        "https://investors.danaher.com/2021-08-30-Danaher-Completes-Acquisition-of-Aldevron",
    ),
    (
        "Merck KGaA",
        "2026-06-25",
        "M&A",
        "Merck KGaA agrees to acquire Bio-Techne Corporation",
        "https://www.gettex.de/en/news-overview/newsdetail/eqs-adhoc-merck-kgaa-merck-agrees-to-acquire-bio-techne-corporation/",
    ),
    (
        "Merck KGaA",
        "2026-10-19",
        "M&A",
        "Merck KGaA agrees to acquire Silence Therapeutics",
        "https://www.sec.gov/Archives/edgar/data/0001479615/000119312526424695/d172259dex991.htm",
    ),
    (
        "Merck KGaA",
        "2025-10-15",
        "M&A",
        "MilliporeSigma to acquire chromatography business of JSR Life Sciences",
        "https://www.businesswire.com/news/home/20251015038255/en",
    ),
    (
        "Merck KGaA",
        "2025-07-01",
        "M&A",
        "Merck KGaA completes acquisition of SpringWorks Therapeutics",
        "https://www.businesswire.com/news/home/20250630369209/en",
    ),
    (
        "Thermo Fisher",
        "2025-10-29",
        "M&A",
        "Thermo Fisher to acquire Clario Holdings",
        "https://www.sec.gov/Archives/edgar/data/97745/000009774525000156/tmo-20251029.htm",
    ),
    (
        "Repligen",
        "2026-07-28",
        "M&A",
        "Repligen to acquire BioLife Solutions",
        "https://www.sec.gov/Archives/edgar/data/0000730272/000119312526318853/rgen-ex99_1.htm",
    ),
)


# Danaher FY2025 Form 10-K (acquisitions, three years to 31 Dec 2025). Source of the values below.
DANAHER_10K_URL = (
    "https://www.sec.gov/Archives/edgar/data/313616/000031361626000062/dhr-20251231.htm"
)

# Deal values the 10-K gives, in USD millions, keyed by (acquirer, announced date).
DEAL_VALUE_USD_M: dict[tuple[str, str], float] = {
    ("Danaher", "2023-12-06"): 5600.0,  # Abcam: cash purchase price of approximately $5.6 billion
}

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
    """Store the company-reported deals and the 10-K notes. Returns rows written."""
    written = 0
    for company_id, day, category, headline, url in COMPANY_DEALS:
        value_m = DEAL_VALUE_USD_M.get((company_id, day))
        row = {
            "acquirer": company_id,
            "announced_date": day,
            "category": category,
            "headline": headline,
            "value_usd": value_m * 1_000_000 if value_m else None,
            "status": "announced",
            "source_url": url,
            "source_type": "document",  # company release or filing
            "published_date": day,
            "evidence_label": "Fact",
        }
        if store.upsert(conn, run_id, "deal", row) != "rejected":
            written += 1
    for text in DANAHER_10K_NOTES:
        conn.execute(
            "INSERT OR REPLACE INTO screen_notes (tab, label, text, source_url, source_type, "
            "loaded_at, evidence_label, verification_status) VALUES (?, ?, ?, ?, 'document', ?, "
            "'Fact', 'passed')",
            ("Overview M&A", "Danaher FY2025 10-K", text, DANAHER_10K_URL, store.now_iso()),
        )
    conn.commit()
    return written
