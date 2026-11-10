# ruff: noqa: E501  (source URLs are long; one per row)
"""Announced layoffs by company and year, 2024 to 2026 (Overview tile).

Mark rules, applied to each cell:
- Yes (tick): a company filing, release or report states job cuts or severance for that year.
- No (cross): none found in the sources searched. This is not proof that no cuts happened.
- Unknown (to collect): the source is undated, or it does not say whether cuts were made.

Each cell carries the source that supports it. Source confidence is in the note.
Research log: docs/layoffs_research.md.
"""

from __future__ import annotations

import sqlite3

from src.ingest import store

FY2025_10K = {
    "Thermo Fisher": "https://www.sec.gov/Archives/edgar/data/97745/000009774526000018/tmo-20251231.htm",
    "Avantor": "https://www.sec.gov/Archives/edgar/data/1722482/000162828026007118/avtr-20251231.htm",
    "Repligen": "https://www.sec.gov/Archives/edgar/data/730272/000119312526076528/rgen-20251231.htm",
    "Danaher": "https://www.sec.gov/Archives/edgar/data/313616/000031361626000062/dhr-20251231.htm",
}

# (company, year, mark, source URL, note)
LAYOFFS: tuple[tuple[str, int, str, str, str], ...] = (
    (
        "Thermo Fisher",
        2026,
        "Yes",
        "https://www.fiercepharma.com/manufacturing/thermo-fisher-trims-massachusetts-headcount-franklin-site-closure",
        "Franklin, MA site phased out by end 2026; WARN lists 103 roles, company says capped at 80.",
    ),
    (
        "Thermo Fisher",
        2025,
        "Yes",
        "https://www.fiercepharma.com/manufacturing/thermo-fisher-outlines-85-layoffs-carlsbad-ca-cdmos-cost-cutting-crusade-marches",
        "About 85 layoffs at Carlsbad, CA; also cuts in Massachusetts. FY2025 10-K: severance about 5% of workforce.",
    ),
    (
        "Thermo Fisher",
        2024,
        "Yes",
        FY2025_10K["Thermo Fisher"],
        "FY2025 10-K: severance tied to facility consolidations and cost reductions, about 2% of workforce in 2024.",
    ),
    (
        "Avantor",
        2026,
        "Yes",
        "https://www.layofftracker.us/layoffs/company/avantor-fluid-handling/2026",
        "Avantor Fluid Handling, Morrisville, NC: 54 employees (third-party tracker, WARN-based; not verified against the filing).",
    ),
    (
        "Avantor",
        2025,
        "Unknown",
        FY2025_10K["Avantor"],
        "FY2025 10-K: 2024 programme severance reversed by $5.3m; no new material charges stated. Cuts not stated.",
    ),
    (
        "Avantor",
        2024,
        "Yes",
        FY2025_10K["Avantor"],
        "FY2025 10-K: 2024 multi-year cost programme, $82.8m charges, of which $64.3m employee severance.",
    ),
    (
        "Repligen",
        2026,
        "Yes",
        "https://www.sec.gov/Archives/edgar/data/0000730272/000162828026068562/rgen-20260930.htm",
        "Q3 2026 10-Q: restructuring to simplify the global manufacturing footprint; severance $3.3m in H1. Headcount not disclosed.",
    ),
    (
        "Repligen",
        2025,
        "Unknown",
        FY2025_10K["Repligen"],
        "Q1 2025 charges were mainly facility-related (severance $12k). Headcount not stated.",
    ),
    (
        "Repligen",
        2024,
        "Unknown",
        FY2025_10K["Repligen"],
        "No 2024 headcount detail found in the sources searched.",
    ),
    (
        "Sartorius",
        2026,
        "No",
        "https://www.aerzteblatt.de/news/sartorius-stellt-mehr-personal-ein-a49d263f-d8ee-40ca-8ca9-ee6014b36860",
        "No 2026 cuts found. Sartorius reports hiring again (2025 coverage).",
    ),
    (
        "Sartorius",
        2025,
        "No",
        "https://www.aerzteblatt.de/news/sartorius-stellt-mehr-personal-ein-a49d263f-d8ee-40ca-8ca9-ee6014b36860",
        "No 2025 cuts found. Hiring again, per 2025 coverage.",
    ),
    (
        "Sartorius",
        2024,
        "Unknown",
        "https://in.marketscreener.com/quote/stock/SARTORIUS-AG-436559/news/Hiring-freeze-and-voluntary-redundancies-at-laboratory-supplier-Sartorius-43240015",
        "Voluntary redundancy programme at HQ (about 200 roles, not confirmed by the company). Article undated in the sources.",
    ),
    (
        "Danaher",
        2026,
        "No",
        FY2025_10K["Danaher"],
        "None found in news searched. FY2025 10-K read only in part; to be checked.",
    ),
    (
        "Danaher",
        2025,
        "No",
        FY2025_10K["Danaher"],
        "None found in news searched. FY2025 10-K read only in part; to be checked.",
    ),
    (
        "Danaher",
        2024,
        "No",
        FY2025_10K["Danaher"],
        "None found in news searched. FY2025 10-K read only in part; to be checked.",
    ),
    (
        "Merck KGaA",
        2026,
        "No",
        "https://reports.emdgroup.com/en/annualreport/2025/consolidated-financial-statements/cash-flow-statement.html",
        "None found in news searched. Latest reports for Merck KGaA's own cuts found date from 2012–2013.",
    ),
    (
        "Merck KGaA",
        2025,
        "No",
        "https://reports.emdgroup.com/en/annualreport/2025/consolidated-financial-statements/cash-flow-statement.html",
        "None found in news searched. Latest reports for Merck KGaA's own cuts found date from 2012–2013.",
    ),
    (
        "Merck KGaA",
        2024,
        "No",
        "https://reports.emdgroup.com/en/annualreport/2025/consolidated-financial-statements/cash-flow-statement.html",
        "None found in news searched. Latest reports for Merck KGaA's own cuts found date from 2012–2013.",
    ),
)


def load_layoffs(conn: sqlite3.Connection, run_id: int) -> int:
    """Store the layoff marks. Returns rows written."""
    written = 0
    for company, year, mark, url, note in LAYOFFS:
        row = {
            "company_id": company,
            "year": year,
            "announced": mark,
            "note": note,
            "source_url": url,
            "source_type": "document",
            "published_date": None,
            "evidence_label": "Signal",
        }
        if store.upsert(conn, run_id, "layoff_year", row) != "rejected":
            written += 1
    return written
