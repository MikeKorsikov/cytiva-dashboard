"""Demand drivers (Screen 4): the numbers the screen shows, read from the app database.

Every value comes from a stored row with its source URL. Nothing is estimated. Where the sheet
has no figure, the screen shows "to collect".
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field


def _rows(conn: sqlite3.Connection, sql: str) -> list[dict]:
    cur = conn.execute(sql)
    names = [d[0] for d in cur.description]
    return [dict(zip(names, row, strict=True)) for row in cur.fetchall()]


NOT_AVAILABLE = {"", "NA", "n/d"}


def _num(text: str | None) -> float | None:
    """A number from the sheet's text ("2,217", "17%", "$1.2"), or None when not available."""
    if text is None or str(text).strip() in NOT_AVAILABLE:
        return None
    return float(str(text).replace(",", "").replace("%", "").replace("$", ""))


@dataclass
class DemandData:
    burden: list[dict] = field(default_factory=list)
    pipeline: list[dict] = field(default_factory=list)
    approvals: list[dict] = field(default_factory=list)
    expiries: list[dict] = field(default_factory=list)
    policy: list[dict] = field(default_factory=list)
    top_drugs: list[dict] = field(default_factory=list)
    labels: dict = field(default_factory=dict)  # the demand README display labels, by label
    capacity: list[dict] = field(default_factory=list)
    product_use: list[dict] = field(default_factory=list)
    implications: list[dict] = field(default_factory=list)


def load(conn: sqlite3.Connection) -> DemandData | None:
    """All screen data, or None when the tables are not loaded yet."""
    try:
        data = DemandData(
            labels={
                r["label"]: r["text"]
                for r in _rows(
                    conn,
                    "SELECT label, text FROM screen_notes WHERE tab = 'Demand README'",
                )
            },
            burden=_rows(conn, "SELECT * FROM demand_burden"),
            pipeline=_rows(conn, "SELECT * FROM demand_pipeline"),
            approvals=_rows(conn, "SELECT * FROM demand_approval"),
            expiries=_rows(conn, "SELECT * FROM demand_expiry"),
            policy=_rows(conn, "SELECT * FROM demand_policy"),
            top_drugs=_rows(conn, "SELECT * FROM demand_top_drug"),
            capacity=_rows(conn, "SELECT * FROM demand_capacity"),
            product_use=_rows(conn, "SELECT * FROM demand_product_use"),
            implications=_rows(conn, "SELECT * FROM demand_implication ORDER BY id"),
        )
    except sqlite3.OperationalError:
        return None
    if not data.burden and not data.top_drugs:
        return None
    return data


# Approximate country centres for the map (reference, not from the sheet).
COUNTRY_CENTRE: dict[str, tuple[float, float]] = {
    "China": (35.0, 103.0),
    "India": (21.0, 79.0),
    "United States": (39.5, -98.0),
    "Pakistan": (30.4, 69.3),
    "Indonesia": (-2.5, 118.0),
    "Brazil": (-10.0, -52.0),
    "Bangladesh": (23.7, 90.4),
    "Mexico": (23.6, -102.5),
    "Egypt": (26.8, 30.8),
    "Japan": (36.2, 138.3),
    "Nigeria": (9.1, 8.7),
    "Türkiye": (39.0, 35.2),
    "Russia": (61.5, 105.3),
    "Germany": (51.2, 10.4),
    "France": (46.2, 2.2),
    "United Kingdom": (54.0, -2.5),
    "Italy": (42.8, 12.6),
    "Canada": (56.1, -106.3),
    "Spain": (40.4, -3.7),
    "South Korea": (36.5, 127.9),
}


CANCER_CASES_COLUMN = "new_cancer_cases_2024"  # the year is the column's (B-12)


def map_points(data: DemandData) -> list[dict]:
    """Countries with a cancer-case figure for the map: lat, lon, cases, region and the year."""
    out = []
    year = CANCER_CASES_COLUMN[-4:]
    for r in data.burden:
        cases = _num(r[CANCER_CASES_COLUMN])
        pos = COUNTRY_CENTRE.get(r["country"])
        if cases is None or pos is None:
            continue
        out.append(
            {
                "country": r["country"],
                "year": year,
                "lat": pos[0],
                "lon": pos[1],
                "cases": cases,
                "region": r["map_region"],
            }
        )
    return out


def top_burden(data: DemandData, n: int = 10) -> list[dict]:
    """Top countries by new cancer cases in 2024 (GLOBOCAN 2024), as the sheet's T2 ranks them.
    Diabetes (IDF 2024) is shown beside it, not used for the ranking. DALYs are not collected."""
    ranked = [r for r in data.burden if _num(r["new_cancer_cases_2024"]) is not None]
    ranked.sort(key=lambda r: _num(r["new_cancer_cases_2024"]), reverse=True)
    return ranked[:n]


COMPARABLE_METRIC = "Therapies in development"


def pipeline_totals(data: DemandData) -> dict:
    """Gene, cell and RNA therapies in development (the comparable counts), and their total."""
    by_type = {r["medicine_type"]: r for r in data.pipeline}
    total = next((r for r in data.pipeline if r["medicine_type"].startswith("Gene, cell")), None)
    return {
        "total": total,
        "rows": [r for r in data.pipeline if r["metric"].startswith(COMPARABLE_METRIC)],
        "by_type": by_type,
    }


def other_pipeline(data: DemandData) -> list[dict]:
    """Pipeline counts that measure something else (late-stage antibodies, clinical trials,
    drugs in R&D). Shown beside the comparable counts, not in the same bars."""
    return [r for r in data.pipeline if not r["metric"].startswith(COMPARABLE_METRIC)]


def mab_sales_top15(data: DemandData) -> float:
    """Sum of FY2025 sales of the mAbs in the top-15 list (sheet headline: 99.8 bn)."""
    return round(
        sum(_num(r["sales_fy2025_usd_bn"]) for r in data.top_drugs if r["type"] == "mAb"), 2
    )


def pledges_total(data: DemandData) -> float:
    """Sum of listed US pledges (sheet headline: 286.8 bn; pledges, not spend)."""
    return round(
        sum(_num(r["pledge_or_capacity"]) for r in data.capacity if r["kind"] == "Pledge"), 2
    )


def fda_biologics_2025(data: DemandData) -> dict:
    """FDA biologics approved in 2025: CDER biologics plus CBER gene and cell therapies.
    Rows are matched on period 2025, so the 2026 year-to-date rows are not counted."""
    cder = next(
        (
            r
            for r in data.approvals
            if r["regulator"] == "FDA CDER"
            and r["period"] == "2025"
            and r["metric"].startswith("Of which biologics")
        ),
        None,
    )
    cber = next(
        (
            r
            for r in data.approvals
            if r["regulator"] == "FDA CBER"
            and r["period"] == "2025"
            and r["metric"].startswith("Of which gene")
        ),
        None,
    )
    period = (cder or cber or {}).get("period")
    cder_n = int(_num(cder["value"])) if cder else None
    cber_n = int(_num(cber["value"])) if cber else None
    total = cder_n + cber_n if cder_n is not None and cber_n is not None else None
    return {"cder": cder_n, "cber": cber_n, "total": total, "period": period}


def bioprocess_flag(text: str | None) -> str:
    """Yes, Partly or No from the sheet's free text (for the colour of the table)."""
    t = (text or "").strip().lower()
    if t.startswith("yes"):
        return "Yes"
    if t.startswith("partly"):
        return "Partly"
    if t.startswith("no"):
        return "No"
    return "to collect"
