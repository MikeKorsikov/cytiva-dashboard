"""China screen data (Screen 6) from the live China tabs, loaded into the app database.

Read from data/china/sheet/ (exports of the research sheet, read only), by header name:
Headline, Companies, Coverage grid, Coverage evidence, Financials, Vendors, Opportunities,
Implications, Sources. Rows whose ID is not a sheet ID (notes, blank rows) go to screen_notes.

Cytiva's China row is derived from the register (Sites tab, Country = China: ST42 to ST45), not
copied from the sheet's Coverage grid, which is reference only. Step 8 for Cytiva China comes
from Coverage evidence row CE-35 (Shanghai Fast Trak centre, S43).

Amounts are USD. RMB is converted at CNY_USD_RATE, an assumption stored with each converted value.
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from src.domain.china import CNY_USD_RATE, FAMILY_NAMES
from src.ingest import store
from src.ingest.coverage import is_producing, site_evidence
from src.ingest.sheet_headers import read_sheet

REPO_ROOT = Path(__file__).resolve().parents[2]
SHEET_DIR = REPO_ROOT / "data" / "china" / "sheet"
REGISTER_DIR = REPO_ROOT / "data" / "coverage" / "sheet"
CHINA_SHEET_URL = (
    "https://docs.google.com/spreadsheets/d/1wEndgjfRVTKSpNWlNFHdgZp_PWvnLnrca6UCHxzvvXI"
)

# Register family name -> sheet code (for Cytiva's China row).
CODE_OF_FAMILY = {name: code for code, name in FAMILY_NAMES.items()}
CONFIDENCE_RANK = {"H": 0, "M": 1, "L": 2}
ID_PATTERN = {
    "sources": re.compile(r"S\d+"),
    "companies": re.compile(r"C\d\d"),
    "evidence": re.compile(r"CE-\d+"),
    "financials": re.compile(r"F-\d\d[a-z]?"),
    "vendors": re.compile(r"V\d\d"),
    "opportunities": re.compile(r"O-\d\d"),
    "implications": re.compile(r"I-\d\d"),
    "headline": re.compile(r"H-\d\d"),
}


def _read(path: Path) -> list[dict]:
    return read_sheet(path)


def _num(text: str | None) -> float | None:
    """A sheet number: '5,232.9' -> 5232.9; 'n/d', '' and text -> None."""
    try:
        return float((text or "").strip().replace(",", ""))
    except ValueError:
        return None


def _first_source(text: str | None) -> str | None:
    found = re.findall(r"S\d+", text or "")
    return found[0] if found else None


def load_china(conn: sqlite3.Connection, run_id: int, report: list[str] | None = None) -> int:
    """Store the screen 6 rows. Returns the number of rows accepted. Re-runnable: rows are
    upserted by their sheet IDs. Unparseable values and differences from the sheet's grid are
    appended to `report`."""
    report = report if report is not None else []
    accepted = 0

    def put(table: str, row: dict, url: str, label: str | None = None) -> None:
        nonlocal accepted
        row.update(
            {
                "source_url": url,
                "source_type": "document",
                "published_date": None,
                "evidence_label": label or ("Fact" if row.get("confidence") == "H" else "Signal"),
            }
        )
        if store.upsert(conn, run_id, table, row) != "rejected":
            accepted += 1
        else:
            report.append(f"{table} {next(iter(row.values()))}: rejected (no https source)")

    sources = {r["ID"]: r for r in _read(SHEET_DIR / "sources.csv")}

    def url_of(text: str | None) -> str:
        sid = _first_source(text)
        if sid in sources:
            return sources[sid]["URL"]
        return CHINA_SHEET_URL

    for sid, src in sources.items():
        put(
            "cn_source",
            {
                "id": sid,
                "title": src["Title"],
                "publisher": src["Publisher"],
                "date_text": src["Date"],
                "source_kind": src["Type"],
                "notes": None,
                "confidence": "H",
            },
            src["URL"],
            label="Fact",
        )

    def is_row(raw: dict, pattern: re.Pattern) -> bool:
        first = (next(iter(raw.values())) or "").strip()
        if pattern.fullmatch(first):
            return True
        if first:
            put(
                "screen_notes",
                {
                    "tab": "China",
                    "label": first,
                    "text": raw.get("Note", "") or next((v for v in raw.values() if v), ""),
                },
                CHINA_SHEET_URL,
                label="Signal",
            )
        return False

    # Companies (T1 Companies)
    for raw in _read(SHEET_DIR / "companies.csv"):
        if not is_row(raw, ID_PATTERN["companies"]):
            continue
        conf = raw["Confidence"]
        put(
            "cn_company",
            {
                "company_id": raw["ID"],
                "name_en": raw["Company (EN)"],
                "name_cn": raw["Company (CN)"],
                "listing": raw["Listed?"],
                "exchange_code": raw["Exchange code"],
                "ownership_status": raw["Ownership / status"],
                "main_business": raw["Main business"],
                "products_checked": None,
                "source_note": raw["Source IDs"],
                "confidence": conf,
            },
            url_of(raw["Source IDs"]),
        )

    # Coverage evidence (T1 Coverage evidence): one row per evidence ID
    evidence_rows = []
    for raw in _read(SHEET_DIR / "coverage_evidence.csv"):
        if not is_row(raw, ID_PATTERN["evidence"]):
            continue
        evidence_rows.append(raw)
        put(
            "cn_coverage_evidence",
            {
                "evidence_id": raw["Evidence ID"],
                "company_id": raw["Company ID"],
                "family": raw["Family"],
                "status": raw["Status"],
                "evidence": raw["Evidence (quote)"],
                "source_note": raw["Source IDs"],
                "source_date": raw["Source date"],
                "confidence": raw["Confidence"],
            },
            url_of(raw["Source IDs"]),
        )

    # Cells: challengers from the grid, backed by their best evidence row
    best_evidence: dict[tuple[str, str], dict] = {}
    for raw in evidence_rows:
        key = (raw["Company ID"], raw["Family"])
        current = best_evidence.get(key)
        if (
            current is None
            or CONFIDENCE_RANK[raw["Confidence"][:1]] < CONFIDENCE_RANK[current["Confidence"][:1]]
        ):
            best_evidence[key] = raw

    grid = _read(SHEET_DIR / "coverage_grid.csv")
    family_columns = {
        "Med (media)": "Med",
        "SU (single-use)": "SU",
        "Res (resins)": "Res",
        "Filt (filtration)": "Filt",
        "Fill (filling)": "Fill",
        "Gen (genomic)": "Gen",
        "Sys (systems; bioreactors)": "Sys",
        "Anl (analytical)": "Anl",
    }
    cells: dict[tuple[str, str], dict] = {}
    for raw in grid:
        company = raw["ID"]
        if not re.fullmatch(r"C(0[1-9]|1\d)", company or ""):
            continue  # C00 is derived from the register; notes are skipped
        for column, code in family_columns.items():
            status = raw[column].strip()
            if not status:
                continue  # no evidence: not stored, shown as ?
            evidence = best_evidence.get((company, code))
            if evidence is None:
                report.append(f"grid {company} {code} {status}: no evidence row")
                continue
            cells[(company, code)] = {
                "status": status,
                "evidence_id": evidence["Evidence ID"],
                "confidence": evidence["Confidence"],
                "url": url_of(evidence["Source IDs"]),
            }
    # Cytiva's China row, from the register (Country = China)
    register = [
        r
        for r in _read(REGISTER_DIR / "register_sites.csv")
        if r["Country"] == "China" and re.fullmatch(r"ST\d+", r["Site ID"] or "")
    ]
    stage_name = {
        "Single-use and bioreactors": "Single-use",
        "Chromatography resins": "Resins",
        "Filtration": "Filtration",
        "Fill-finish": "Filling",
        "Genomic medicine": "Genomic",
        "Process hardware": "Systems",
        "Cell culture media": "Media",
        "Discovery and analytics": "Analytical",
    }
    cyt_sites = []
    for r in register:
        stages = r["Value-chain stages made here"]
        evidenced, hypothesis = site_evidence(stages, r["Stage evidence"])
        named = {f for stage, f in stage_name.items() if stage.lower() in stages.lower()}
        cyt_sites.append(
            {
                "id": r["Site ID"],
                "named": named,
                "evidenced": evidenced,
                "producing": is_producing(stages),
                "confidence": r["Confidence (H/M/L)"],
                "url": (r.get("Source URL") or "").strip() or sources["S19"]["URL"],
            }
        )
    for code, family in FAMILY_NAMES.items():
        named = [s for s in cyt_sites if family in s["named"]]
        made = [s for s in named if family in s["evidenced"] and s["producing"]]
        partial = [s for s in named if family in s["evidenced"] and not s["producing"]]
        if made:
            best = min(made, key=lambda s: CONFIDENCE_RANK[s["confidence"]])
            cells[("C00", code)] = {
                "status": "Made",
                "evidence_id": best["id"],
                "confidence": best["confidence"],
                "url": best["url"],
            }
        elif partial or named:
            pool = partial or named
            best = min(pool, key=lambda s: CONFIDENCE_RANK[s["confidence"]])
            cells[("C00", code)] = {
                "status": "Partial",
                "evidence_id": best["id"],
                "confidence": best["confidence"] if partial else "L",
                "url": best["url"],
            }
        else:
            cells[("C00", code)] = {
                "status": "Not made",
                "evidence_id": None,
                "confidence": "M",
                "url": sources["S19"]["URL"],
            }
    # Differences from the sheet's grid for Cytiva (reference; not stored)
    for raw in grid:
        if raw["ID"] != "C00":
            continue
        for column, code in family_columns.items():
            sheet_status = raw[column].strip() or "?"
            derived = cells[("C00", code)]["status"]
            if sheet_status != derived:
                report.append(f"grid C00 {code}: sheet {sheet_status}, register {derived}")
    # Step 8 for Cytiva China: CE-35 (Shanghai Fast Trak centre)
    ce35 = next((r for r in evidence_rows if r["Evidence ID"] == "CE-35"), None)
    if ce35 is not None:
        cells[("C00", "Service")] = {
            "status": ce35["Status"],
            "evidence_id": "CE-35",
            "confidence": ce35["Confidence"],
            "url": url_of(ce35["Source IDs"]),
        }
    for (company, code), cell in cells.items():
        put(
            "cn_coverage",
            {
                "company_id": company,
                "family": code,
                "status": cell["status"],
                "evidence_id": cell["evidence_id"],
                "confidence": cell["confidence"],
            },
            cell["url"],
        )

    # Financials (T2 Financials). Revenue in RMB converted at CNY_USD_RATE, except Danaher China
    # (derived in H-03, already in USD).
    headline_values = {r["ID"]: r for r in _read(SHEET_DIR / "headline.csv")}
    for raw in _read(SHEET_DIR / "financials.csv"):
        if not re.fullmatch(r"F-\d\d[a-z]?", raw["ID"] or ""):
            continue
        rmb = _num(raw["Revenue (RMB m)"])
        if raw["Company ID"] == "C00":
            usd = _num(headline_values["H-03"]["Value"]) * 1000
            rate = None
        elif rmb is not None:
            usd = round(rmb / CNY_USD_RATE, 1)
            rate = CNY_USD_RATE
        else:
            usd, rate = None, None
        put(
            "cn_financial",
            {
                "id": raw["ID"],
                "company_id": raw["Company ID"],
                "company": raw["Company"],
                "code": raw["Code"],
                "period": raw["Period"],
                "revenue_rmb_m": rmb,
                "revenue_usd_m": usd,
                "cny_usd_rate": rate,
                "revenue_yoy_pct": _num(raw["Revenue YoY %"]),
                "gross_margin_pct": _num(raw["Gross margin %"]),
                "rd_to_revenue_pct": _num(raw["R&D / revenue %"]),
                "net_profit_rmb_m": _num(raw["Net profit attrib. (RMB m)"]),
                "basis": raw["Basis"],
                "source_note": raw["Source IDs"],
                "confidence": raw["Confidence"],
                "note": raw["Notes"] or None,
            },
            url_of(raw["Source IDs"]),
        )

    # Vendors (T3 Vendors). A vendor marked Removed is not stored.
    for raw in _read(SHEET_DIR / "vendors.csv"):
        if not is_row(raw, ID_PATTERN["vendors"]):
            continue
        if raw["Relationship type"].strip() == "Removed":
            report.append(f"{raw['ID']}: removed in the sheet; not stored")
            continue
        put(
            "cn_vendor",
            {
                "id": raw["ID"],
                "vendor_en": raw["Vendor (EN)"],
                "vendor_cn": raw["Vendor (CN)"],
                "code": raw["Code"],
                "supplies": raw["Supplies"],
                "to_danaher_company": raw["To (Danaher company)"],
                "relationship": raw["Relationship type"],
                "evidence": raw["Evidence (quote)"],
                "source_note": raw["Source IDs"],
                "confidence": raw["Confidence"],
            },
            url_of(raw["Source IDs"]),
        )

    # Opportunities (T4 Opportunities)
    for raw in _read(SHEET_DIR / "opportunities.csv"):
        if not is_row(raw, ID_PATTERN["opportunities"]):
            continue
        put(
            "cn_opportunity",
            {
                "id": raw["ID"],
                "opportunity": raw["Opportunity"],
                "why": raw["Why (evidence summary)"],
                "product_lines": raw["Product lines"],
                "evidence_label": raw["Label"],
                "evidence": raw["Evidence (quote)"],
                "source_note": raw["Source IDs"],
                "source_date": raw["Source date"],
                "confidence": raw["Confidence"],
            },
            url_of(raw["Source IDs"]),
            label=raw["Label"],
        )

    # Implications (T5 Implications): hypotheses, no source URL by design
    for raw in _read(SHEET_DIR / "implications.csv"):
        if not is_row(raw, ID_PATTERN["implications"]):
            continue
        put(
            "cn_implication",
            {
                "id": raw["ID"],
                "hypothesis": raw["Hypothesis (not a finding)"],
                "based_on": raw["Based on"],
                "confirm_or_refute": raw["What would confirm or refute it"],
                "area": raw["Area"],
                "confidence": raw["Confidence"],
            },
            CHINA_SHEET_URL,
            label="Hypothesis",
        )

    # Headline figures (H Headline figures). Show on tile is kept with the row.
    for raw in _read(SHEET_DIR / "headline.csv"):
        if not is_row(raw, ID_PATTERN["headline"]):
            continue
        value = raw["Value"]
        put(
            "cn_headline",
            {
                "id": raw["ID"],
                "metric": raw["Metric"],
                "value_text": value,
                "value_num": _num(value),
                "unit": raw["Unit"],
                "period": raw["Period"],
                "show_on_tile": raw["Show on tile?"],
                "evidence": raw["Evidence (quote)"],
                "source_note": raw["Source IDs"],
                "confidence": raw["Confidence"],
            },
            url_of(raw["Source IDs"]),
        )

    conn.commit()
    return accepted
