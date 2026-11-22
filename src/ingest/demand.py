"""Demand drivers (Screen 4), from the research sheet "Screen 4 - Demand drivers data".

Each tab is exported to data/demand/sheet/ by scripts/export_seed_sheets.py and read through its
header map (src/ingest/sheet_headers.py). A tab with more than one table is read by section, so
a changed or missing header fails the load.

Every stored row carries its source URL, looked up from the Sources tab. A row without one is
rejected by store.upsert and not shown. The demand tables are cleared and reloaded on each run,
so the database holds what the sheet holds, and rows removed from the sheet do not linger.

Not stored: the pipeline-by-region table (read and checked, not shown), the T2 ranking (the screen
ranks from T1; a test checks the two agree), and the Sources tab itself (used for URLs only).
Summary rows, mockup checks and notes go to screen_notes, not to the screen.
"""

from __future__ import annotations

import csv
import re
import sqlite3
from pathlib import Path

from src.ingest import store
from src.ingest.sheet_headers import DEMAND_T2, DEMAND_T2_HEADER, read_tab

REPO_ROOT = Path(__file__).resolve().parents[2]
SHEET_DIR = REPO_ROOT / "data" / "demand" / "sheet"

TABLES = (
    "demand_burden",
    "demand_pipeline",
    "demand_approval",
    "demand_expiry",
    "demand_policy",
    "demand_top_drug",
    "demand_capacity",
    "demand_product_use",
)

# Tab title for each export: the screen_notes tab name of its notes.
TAB_NAMES = {
    "t1_disease_burden.csv": "T1 Disease burden",
    "t3_pipeline_by_type.csv": "T3 Pipeline by type",
    "t4_approvals_expiries.csv": "T4 Approvals & expiries",
    "t5_policy_funding.csv": "T5 Policy & funding",
    "t6_biggest_drugs.csv": "T6 Biggest drugs",
    "t7_capacity_pledges.csv": "T7 Capacity pledges",
    "t8_products_used.csv": "T8 Products used",
    "sources.csv": "Sources",
}

# Values the sheet uses for "not available". Stored as None, so the screen shows "to collect".
NOT_AVAILABLE = {"", "NA", "n/d"}


def _clean(text: str | None) -> str | None:
    if text is None or text.strip() in NOT_AVAILABLE:
        return None
    return text.strip()


def _label(confidence: str) -> str:
    """Signal for L confidence, Fact otherwise (as for the other screens)."""
    return "Signal" if confidence == "L" else "Fact"


def _url(urls: dict[str, str], source_id: str) -> str:
    """The URL of a Source ID from the Sources tab. An unknown ID fails the load."""
    if not source_id:
        return ""
    if source_id not in urls:
        raise ValueError(f"source {source_id} is not in the Sources tab")
    return urls[source_id]


def _note(conn: sqlite3.Connection, tab: str, text: str) -> None:
    """A non-data row of a tab: kept in screen_notes, not displayed."""
    conn.execute(
        "INSERT OR REPLACE INTO screen_notes (tab, label, text, source_url, source_type, "
        "loaded_at, evidence_label, verification_status) VALUES (?, ?, ?, '', 'curated', ?, "
        "'Fact', 'passed')",
        (tab, text[:80], text, store.now_iso()),
    )


def _note_cells(conn: sqlite3.Connection, tab: str, cells: list[str]) -> None:
    values = [v for v in cells if v]
    if values:
        _note(conn, tab, " | ".join(values))


def _store(
    conn: sqlite3.Connection,
    run_id: int,
    table: str,
    fields: dict[str, str],
    url: str,
    label: str,
) -> bool:
    row = {k: (v if v != "" else None) for k, v in fields.items()}
    row.update(
        {
            "source_url": url or "",
            "source_type": "document",
            "published_date": None,
            "evidence_label": label,
        }
    )
    return store.upsert(conn, run_id, table, row) != "rejected"


def check_t2_header(path: Path = SHEET_DIR / "t2_top10_countries.csv") -> list[str]:
    """T2 ranking (by new cancer cases 2024) as the sheet gives it. Fails if its header row changed.

    Read for tests only: the screen ranks from T1 and must agree with this list."""
    with path.open(encoding="utf-8", newline="") as handle:
        table = list(csv.reader(handle))
    if tuple(table[1][:3]) != DEMAND_T2_HEADER:
        raise ValueError(f"{DEMAND_T2}: header row changed; expected {DEMAND_T2_HEADER}")
    return [row[0] for row in table[2:12]]  # the ranking block: ten rows under the header


def load_demand(conn: sqlite3.Connection, run_id: int) -> int:
    """Write the sheet's rows to the app database. Returns the number of rows accepted."""
    for table in TABLES:
        conn.execute(f"DELETE FROM {table}")
    conn.execute(
        "DELETE FROM screen_notes WHERE tab IN (" + ",".join("?" * len(TAB_NAMES)) + ")",
        tuple(TAB_NAMES.values()),
    )
    check_t2_header()

    sources = read_tab(SHEET_DIR / "sources.csv")
    urls = {r["source_id"]: r["url"] for r in sources.rows["source"] if r["url"]}
    for r in sources.rows["source"]:
        if not re.fullmatch(r"S\d{2}", r["source_id"]):
            _note_cells(conn, TAB_NAMES["sources.csv"], r["_cells"])
    for cells in sources.loose:
        _note_cells(conn, TAB_NAMES["sources.csv"], cells)

    written = 0

    t1 = read_tab(SHEET_DIR / "t1_disease_burden.csv")
    for r in t1.rows["burden"]:
        if not r["country"]:
            _note_cells(conn, TAB_NAMES["t1_disease_burden.csv"], r["_cells"])
            continue
        url_2022 = _url(urls, r["cancer_2022_source_id"])
        url_2024 = _url(urls, r["cancer_2024_source_id"])
        url_diabetes = _url(urls, r["diabetes_source_id"])
        fields = {
            "country": r["country"],
            "map_region": r["map_region"],
            "new_cancer_cases_2022": _clean(r["new_cancer_cases_2022"]),
            "new_cancer_cases_2024": _clean(r["new_cancer_cases_2024"]),
            "diabetes_adults_2024_m": _clean(r["diabetes_adults_2024_m"]),
            "dalys_2021_m": _clean(r["dalys_2021_m"]),
            "cancer_source_url": url_2022,
            "cancer_2024_source_url": url_2024,
            "diabetes_source_url": url_diabetes,
            "confidence": r["confidence"],
            "note": r["note"],
        }
        url = url_2024 or url_2022 or url_diabetes
        written += _store(conn, run_id, "demand_burden", fields, url, _label(r["confidence"]))
    for cells in t1.loose:
        _note_cells(conn, TAB_NAMES["t1_disease_burden.csv"], cells)

    t3 = read_tab(SHEET_DIR / "t3_pipeline_by_type.csv")
    for r in t3.rows["pipeline"]:
        if not r["medicine_type"]:
            _note_cells(conn, TAB_NAMES["t3_pipeline_by_type.csv"], r["_cells"])
            continue
        fields = {
            "medicine_type": r["medicine_type"],
            "metric": r["metric"],
            "value": r["value"],
            "previous_value": r["previous_value"],
            "change": r["change"],
            "period": r["period"],
            "source_title": r["source_title"],
            "confidence": r["confidence"],
            "evidence": r["evidence"],
        }
        written += _store(
            conn, run_id, "demand_pipeline", fields, r["source_url"], _label(r["confidence"])
        )
    for r in t3.rows["pipeline_region"]:  # read and checked; not shown on the screen
        if not r["region"]:
            _note_cells(conn, TAB_NAMES["t3_pipeline_by_type.csv"], r["_cells"])
    for cells in t3.loose:
        _note_cells(conn, TAB_NAMES["t3_pipeline_by_type.csv"], cells)

    t4 = read_tab(SHEET_DIR / "t4_approvals_expiries.csv")
    for r in t4.rows["approval"]:
        if not r["regulator"]:
            _note_cells(conn, TAB_NAMES["t4_approvals_expiries.csv"], r["_cells"])
            continue
        fields = {
            "regulator": r["regulator"],
            "metric": r["metric"],
            "value": r["value"],
            "period": r["period"],
            "source_title": r["source_title"],
            "confidence": r["confidence"],
            "evidence": r["evidence"],
        }
        written += _store(
            conn, run_id, "demand_approval", fields, r["source_url"], _label(r["confidence"])
        )
    for r in t4.rows["expiry"]:
        if not r["drug"]:
            _note_cells(conn, TAB_NAMES["t4_approvals_expiries.csv"], r["_cells"])
            continue
        fields = {
            "drug": r["drug"],
            "owner": r["owner"],
            "type": r["type"],
            "event": r["event"],
            "year": r["year"],
            "source_title": r["source_title"],
            "confidence": r["confidence"],
            "evidence": r["evidence"],
        }
        # A row with no source URL (Ocrevus, "not found") is rejected, not stored.
        written += _store(
            conn, run_id, "demand_expiry", fields, r["source_url"], _label(r["confidence"])
        )
    for cells in t4.loose:
        _note_cells(conn, TAB_NAMES["t4_approvals_expiries.csv"], cells)

    t5 = read_tab(SHEET_DIR / "t5_policy_funding.csv")
    for r in t5.rows["policy"]:
        if not r["item"]:
            _note_cells(conn, TAB_NAMES["t5_policy_funding.csv"], r["_cells"])
            continue
        fields = {
            "item": r["item"],
            "label": r["label"],
            "what_it_says": r["what_it_says"],
            "effect_on_biologics_demand": r["effect_on_biologics_demand"],
            "date": r["date"],
            "source_title": r["source_title"],
            "confidence": r["confidence"],
            "evidence": r["evidence"],
        }
        written += _store(
            conn, run_id, "demand_policy", fields, r["source_url"], r["label"] or _label("")
        )
    for cells in t5.loose:
        _note_cells(conn, TAB_NAMES["t5_policy_funding.csv"], cells)

    t6 = read_tab(SHEET_DIR / "t6_biggest_drugs.csv")
    for r in t6.rows["top_drug"]:
        if not r["drug"]:
            _note_cells(conn, TAB_NAMES["t6_biggest_drugs.csv"], r["_cells"])
            continue
        fields = {
            "rank": r["rank"],
            "drug": r["drug"],
            "company": r["company"],
            "sales_fy2025_usd_bn": r["sales_fy2025_usd_bn"],
            "type": r["type"],
            "disease_area": r["disease_area"],
            "bioprocess_use": r["bioprocess_use"],
            "source_title": r["source_title"],
            "confidence": r["confidence"],
            "evidence": r["evidence"],
        }
        written += _store(
            conn, run_id, "demand_top_drug", fields, r["source_url"], _label(r["confidence"])
        )
    for cells in t6.loose:  # summary block: totals the screen computes and the tests check
        _note_cells(conn, TAB_NAMES["t6_biggest_drugs.csv"], cells)

    t7 = read_tab(SHEET_DIR / "t7_capacity_pledges.csv")
    for r in t7.rows["pledge"]:
        if not r["company"]:
            _note_cells(conn, TAB_NAMES["t7_capacity_pledges.csv"], r["_cells"])
            continue
        fields = {
            "kind": "Pledge",
            "company": r["company"],
            "pledge_or_capacity": r["pledge_usd_bn"],
            "unit": "USD bn",
            "period": r["period"],
            "includes": r["includes"],
            "biologics_relevance": r["biologics_relevance"],
            "announced": r["announced"],
            "source_title": r["source_title"],
            "confidence": r["confidence"],
            "evidence": r["evidence"],
        }
        written += _store(
            conn, run_id, "demand_capacity", fields, r["source_url"], _label(r["confidence"])
        )
    for r in t7.rows["built"]:
        if not r["company"]:
            _note_cells(conn, TAB_NAMES["t7_capacity_pledges.csv"], r["_cells"])
            continue
        fields = {
            "kind": "Built capacity",
            "company": r["company"],
            "pledge_or_capacity": r["capacity_l"],
            "unit": "L",
            "period": r["status"],
            "announced": r["as_of"],
            "source_title": r["source_title"],
            "confidence": r["confidence"],
            "evidence": r["evidence"],
        }
        written += _store(
            conn, run_id, "demand_capacity", fields, r["source_url"], _label(r["confidence"])
        )
    for cells in t7.loose:  # totals and the industry figure: calculated or reported, not stored
        _note_cells(conn, TAB_NAMES["t7_capacity_pledges.csv"], cells)

    t8 = read_tab(SHEET_DIR / "t8_products_used.csv")
    for r in t8.rows["product"]:
        if not r["medicine_type"]:
            _note_cells(conn, TAB_NAMES["t8_products_used.csv"], r["_cells"])
            continue
        if r["changed_from_mockup"]:
            _note(
                conn,
                TAB_NAMES["t8_products_used.csv"],
                f"{r['medicine_type']}: changed from mockup: {r['changed_from_mockup']}",
            )
        fields = {
            "medicine_type": r["medicine_type"],
            "chromatography_resins": r["chromatography_resins"],
            "filtration": r["filtration"],
            "single_use_bioreactors_bags": r["single_use_bioreactors_bags"],
            "cell_culture_media": r["cell_culture_media"],
            "cell_gene_therapy_tools": r["cell_gene_therapy_tools"],
            "rationale": r["rationale"],
            "confidence": "Hypothesis",
        }
        # Analyst judgement with no source URL by design: stored as Hypothesis, not as fact.
        written += _store(conn, run_id, "demand_product_use", fields, "", "Hypothesis")
    for cells in t8.loose:
        _note_cells(conn, TAB_NAMES["t8_products_used.csv"], cells)

    conn.commit()
    return written
