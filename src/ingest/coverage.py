# ruff: noqa: E501  (source URLs are long; one per row)
"""Product families made by region, by company: the Competitor coverage screen (screen 2).

Each row is a cell of the matrix that a public source states. Every other cell is absent from
the database and shows as "to collect": no status is estimated or inferred.

Status values match the footprint table: "Made", "Partial" (partly made, or under build, or
planned, or products not fully confirmed), "Not made" (not used in this matrix; only stated
absence would qualify). Regions follow the Danaher reporting regions used on the screen.

Sources are primary documents. Page numbers are given where the source is a long PDF.
Research log: docs/coverage_research.md.
"""

from __future__ import annotations

import sqlite3

from src.ingest import store

NA = "North America"
WE = "Western Europe"
HG = "High-growth markets"
JP = "Japan, Australia and New Zealand"

COMPANIES = ("Cytiva", "Thermo Fisher", "Sartorius", "Repligen", "Avantor", "Merck KGaA")
FAMILIES = (
    "Media",
    "Single-use",
    "Resins",
    "Filtration",
    "Filling",
    "Genomic",
    "Systems",
    "Analytical",
)

SRC_CYTIVA = "https://www.bioprocessintl.com/facilities-capacity/cytiva-outlines-1-6bn-facility-investment-plans-through-2028"
SRC_REPLIGEN = "https://www.sec.gov/Archives/edgar/data/730272/000119312526076528/rgen-20251231.htm"
SRC_SARTORIUS = (
    "https://www.sartorius.com/download/1796536/fy-2025-download-annual-report-sag-en-data.pdf"
)
SRC_MOLSHEIM = "https://sigmaaldrich.com/US/en/collections/press/investment-to-strengthen-manufacturing-capabilities-in-molsheim-france"
SRC_CORK = (
    "https://sigmaaldrich.com/collections/press/expansion-membrane-filtration-manufacturing-ireland"
)
SRC_DARMSTADT = (
    "https://chemengonline.com/milliporesigma-launches-membrane-manufacturing-facility-in-darmstadt"
)
SRC_JAFFREY = "https://www.emdgroup.com/en/news/ls-expansions-07-12-2020.html"

# (company, region, product family, status, source URL, what the source says)
CELLS: tuple[tuple[str, str, str, str, str, str], ...] = (
    # Cytiva: June 2025 investment programme, as reported by BioProcess International
    (
        "Cytiva",
        NA,
        "Resins",
        "Partial",
        SRC_CYTIVA,
        "Muskegon, MI: resins site built, operational by 2028",
    ),
    (
        "Cytiva",
        NA,
        "Filtration",
        "Made",
        SRC_CYTIVA,
        "Fajardo, PR: filtration manufacturing, upgrades and expansion",
    ),
    (
        "Cytiva",
        NA,
        "Media",
        "Made",
        SRC_CYTIVA,
        "Logan, UT: dry powder and liquid media manufacturing",
    ),
    (
        "Cytiva",
        WE,
        "Resins",
        "Made",
        SRC_CYTIVA,
        "Uppsala, SE: chromatography resins, capacity doubled",
    ),
    (
        "Cytiva",
        WE,
        "Filtration",
        "Made",
        SRC_CYTIVA,
        "Ilfracombe, UK: filtration device manufacturing",
    ),
    (
        "Cytiva",
        HG,
        "Filtration",
        "Partial",
        SRC_CYTIVA,
        "South Korea: filtration manufacturing starts in 2026",
    ),
    # Repligen: FY2025 Form 10-K, Item 2 (Properties) and Item 1 (Manufacturing)
    (
        "Repligen",
        NA,
        "Single-use",
        "Made",
        SRC_REPLIGEN,
        "Hopkinton, MA: assembly center for single-use products",
    ),
    (
        "Repligen",
        NA,
        "Resins",
        "Made",
        SRC_REPLIGEN,
        "Waltham, MA: chromatography assembly and manufacturing",
    ),
    (
        "Repligen",
        NA,
        "Filtration",
        "Made",
        SRC_REPLIGEN,
        "Marlborough, MA: XCell ATF, FS TFF, Spectrum HF",
    ),
    (
        "Repligen",
        NA,
        "Analytical",
        "Made",
        SRC_REPLIGEN,
        "Bridgewater, NJ and Marlborough, MA: process analytics",
    ),
    (
        "Repligen",
        WE,
        "Filtration",
        "Made",
        SRC_REPLIGEN,
        "Toulouse FR, Jüri EE, Waterford IE: filtration manufacturing",
    ),
    (
        "Repligen",
        WE,
        "Resins",
        "Made",
        SRC_REPLIGEN,
        "Germany and Netherlands: chromatography manufacturing",
    ),
    ("Repligen", WE, "Analytical", "Made", SRC_REPLIGEN, "Braunschweig, DE: process analytics"),
    # Sartorius: Annual Report 2025, Bioprocess Solutions, pp. 35, 60, 61, 77
    (
        "Sartorius",
        WE,
        "Single-use",
        "Made",
        SRC_SARTORIUS,
        "Aubagne, FR: sterile single-use bags, tubing, connectors (p. 60)",
    ),
    (
        "Sartorius",
        WE,
        "Media",
        "Partial",
        SRC_SARTORIUS,
        "Illkirch, FR: transfection reagents, not cell culture media (p. 61)",
    ),
    (
        "Sartorius",
        HG,
        "Media",
        "Made",
        SRC_SARTORIUS,
        "Beit Haemek, IL: cell culture media (p. 77)",
    ),
    # Merck KGaA (MilliporeSigma Process Solutions): company press releases, 2020 to 2025
    (
        "Merck KGaA",
        WE,
        "Single-use",
        "Made",
        SRC_MOLSHEIM,
        "Molsheim, FR: single-use assemblies, Mobius capacity",
    ),
    (
        "Merck KGaA",
        WE,
        "Filtration",
        "Made",
        SRC_CORK,
        "Cork, IE: membrane manufacturing expansion",
    ),
    (
        "Merck KGaA",
        NA,
        "Filtration",
        "Partial",
        SRC_JAFFREY,
        "Jaffrey, NH: filtration devices (2020 release)",
    ),
    (
        "Avantor",
        "Western Europe",
        "Media",
        "Partial",
        "https://www.roic.ai/quote/AVTR-PA/transcripts/2024-year/4-quarter",
        "Gliwice, Poland: buffer, media and clean-in-place solutions plant, installed (Q4 2024 call)",
    ),
    (
        "Avantor",
        "High-growth markets",
        "Single-use",
        "Partial",
        "https://www.pharmaceuticalprocessingworld.com/avantor-acquires-rim-bio-to-bolster-presence-in-asia/",
        "Changzhou, China: first single-use plant in AMEA, from RIM Bio acquisition (2021)",
    ),
    (
        "Thermo Fisher",
        "North America",
        "Single-use",
        "Partial",
        "https://www.dcatvci.org/top-industry-news/thermo-fisher-to-invest-600-m-to-expand-bioprocessing-materials-capacity/",
        "Logan UT, Millersburg PA, Nashville TN: single-use (2020–22 announcements; current status to confirm)",
    ),
    (
        "Thermo Fisher",
        "Western Europe",
        "Single-use",
        "Partial",
        "https://www.dcatvci.org/top-industry-news/thermo-fisher-to-invest-600-m-to-expand-bioprocessing-materials-capacity/",
        "Cramlington, UK: single-use (2020–22 announcement)",
    ),
    (
        "Thermo Fisher",
        "High-growth markets",
        "Single-use",
        "Partial",
        "https://www.dcatvci.org/top-industry-news/thermo-fisher-to-invest-600-m-to-expand-bioprocessing-materials-capacity/",
        "Singapore and Suzhou, China: single-use (2020–22 announcements)",
    ),
    (
        "Thermo Fisher",
        "North America",
        "Media",
        "Partial",
        "https://www.dcatvci.org/top-industry-news/thermo-fisher-to-invest-600-m-to-expand-bioprocessing-materials-capacity/",
        "Grand Island NY (expansion completed, date not in source) and Miami FL: media",
    ),
    (
        "Thermo Fisher",
        "Western Europe",
        "Media",
        "Partial",
        "https://www.dcatvci.org/top-industry-news/thermo-fisher-to-invest-600-m-to-expand-bioprocessing-materials-capacity/",
        "Inchinnan, Scotland: media (2020–22 announcement)",
    ),
)


def load_coverage(conn: sqlite3.Connection, run_id: int) -> int:
    """Store the sourced footprint cells. Returns rows written."""
    written = 0
    for company, region, family, status, url, _note in CELLS:
        row = {
            "company_id": company,
            "region_id": region,
            "product_family": family,
            "status": status,
            "source_url": url,
            "source_type": "document",
            "published_date": None,
            "evidence_label": "Fact",
        }
        if store.upsert(conn, run_id, "footprint", row) != "rejected":
            written += 1
    return written
