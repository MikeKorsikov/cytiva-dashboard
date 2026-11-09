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


def load_company_deals(conn: sqlite3.Connection, run_id: int) -> int:
    """Store the company-reported deals. Returns rows written."""
    written = 0
    for company_id, day, category, headline, url in COMPANY_DEALS:
        row = {
            "acquirer": company_id,
            "announced_date": day,
            "category": category,
            "headline": headline,
            "value_usd": None,
            "status": "announced",
            "source_url": url,
            "source_type": "document",  # company release or filing
            "published_date": day,
            "evidence_label": "Fact",
        }
        if store.upsert(conn, run_id, "deal", row) != "rejected":
            written += 1
    return written
