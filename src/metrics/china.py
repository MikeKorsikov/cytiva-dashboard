"""China screen (screen 6): read-only view of the China tables for the screen.

Coverage steps reuse the screen 2 rule (metrics.coverage.step_cells) with China's families.
Amounts are USD; RMB figures are converted at ingest.china.CNY_USD_RATE (an assumption, flagged).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field

from src.ingest.china import CNY_USD_RATE, FAMILY_NAMES
from src.metrics.coverage import step_cells

# Grid column order, as in the MVP: sheet codes.
FAMILY_ORDER = ["Med", "SU", "Res", "Filt", "Fill", "Gen", "Sys", "Anl"]
CHINA_REGION = "China"


@dataclass
class ChinaData:
    headline: dict[str, dict]
    companies: list[dict]
    coverage: dict[tuple[str, str], dict]  # (company_id, sheet family code) -> cell
    steps: dict[tuple[str, str, str], dict]  # (company_id, China, step) -> cell
    evidence: list[dict]
    financials: list[dict]
    vendors: list[dict]
    opportunities: list[dict]
    implications: list[dict]
    fx_rate: float = CNY_USD_RATE
    sources: dict[str, dict] = field(default_factory=dict)


def _select(conn: sqlite3.Connection, sql: str) -> list[dict]:
    cursor = conn.execute(sql)
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row, strict=True)) for row in cursor.fetchall()]


def load(conn: sqlite3.Connection) -> ChinaData | None:
    """All China rows, or None when the database predates screen 6 (shown as to collect)."""
    try:
        headline = {r["id"]: r for r in _select(conn, "SELECT * FROM cn_headline")}
        companies = _select(conn, "SELECT * FROM cn_company ORDER BY company_id")
        grid = _select(conn, "SELECT * FROM cn_coverage")
        evidence = _select(conn, "SELECT * FROM cn_coverage_evidence ORDER BY evidence_id")
        financials = _select(conn, "SELECT * FROM cn_financial ORDER BY id")
        vendors = _select(conn, "SELECT * FROM cn_vendor ORDER BY id")
        opportunities = _select(conn, "SELECT * FROM cn_opportunity ORDER BY id")
        implications = _select(conn, "SELECT * FROM cn_implication ORDER BY id")
        sources = {r["id"]: r for r in _select(conn, "SELECT * FROM cn_source")}
    except sqlite3.OperationalError:
        return None
    if not companies:
        return None

    coverage = {(r["company_id"], r["family"]): r for r in grid}
    # The step rule works on screen 2 family names; China's families are mapped onto them.
    cells = {
        (r["company_id"], CHINA_REGION, FAMILY_NAMES[r["family"]]): {
            "status": r["status"],
            "source_url": r["source_url"],
        }
        for r in grid
        if r["family"] in FAMILY_NAMES
    }
    steps = step_cells(cells)  # step 8 (service) has no China row, so it stays to collect
    return ChinaData(
        headline=headline,
        companies=companies,
        coverage=coverage,
        steps=steps,
        evidence=evidence,
        financials=financials,
        vendors=vendors,
        opportunities=opportunities,
        implications=implications,
        sources=sources,
    )


def tiles(data: ChinaData) -> list[dict]:
    """The two headline cards: China share of Danaher sales (H-01) and China growth (H-04)."""
    out = []
    for hid, title in (("H-01", "China share of Danaher sales"), ("H-04", "China sales growth")):
        row = data.headline.get(hid)
        if row:
            out.append({"title": title, **row})
    return out


def danaher_china_usd_m(data: ChinaData) -> float | None:
    """Danaher's China sales in USD million, derived as H-01 x H-02 (headline H-03)."""
    row = data.headline.get("H-03")
    if not row or row["value_num"] is None:
        return None
    return row["value_num"] * 1000


def financial_rows(data: ChinaData) -> list[dict]:
    """Financials with the revenue converted to USD million. RMB rows keep the rate used."""
    out = []
    for r in data.financials:
        usd = r["revenue_usd_m"]
        if r["company_id"] == "C00":
            usd = danaher_china_usd_m(data)
        out.append({**r, "revenue_usd_m_shown": usd})
    return out


def coverage_summary(data: ChinaData) -> dict[str, int]:
    """Counts of Made and Partial family cells, for the grid header."""
    made = sum(1 for c in data.coverage.values() if c["status"] == "Made")
    partial = sum(1 for c in data.coverage.values() if c["status"] == "Partial")
    return {"made": made, "partial": partial}
