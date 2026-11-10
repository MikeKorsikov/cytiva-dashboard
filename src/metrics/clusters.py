"""Customer clusters (Screen 3): the numbers the screen shows, read from the app database.

A cluster here is a high-density biotech hub (companies, plants, sites, universities together),
not a legal entity. Every value comes from a stored row with its source URL. Nothing is
estimated. Where the sheet has no figure, the screen shows "to collect".
"""

from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass, field

from src.ingest import coverage as coverage_ingest
from src.metrics import coverage as coverage_metrics

# Density counts: units that count organisations, sites or plants (not people, jobs, capacity).
DENSITY_UNITS = ("enterprises", "companies", "sites", "plants", "organisations")

# Approximate city-centre positions for the map (reference, not from the sheet).
HUB_POSITION: dict[str, tuple[float, float]] = {
    "KR-SONGDO": (37.39, 126.64),
    "US-BOSTON": (42.37, -71.10),
    "US-RTP": (35.90, -78.87),
    "SG": (1.35, 103.82),
    "IE": (53.35, -6.26),
    "CH-BASEL": (47.56, 7.59),
    "CN-SUZHOU": (31.30, 120.62),
    "IN-HYD": (17.45, 78.38),
    "CN-BEIJING": (39.72, 116.40),
    "CN-SHANGHAI": (31.20, 121.59),
    "DK-SE-MEDICON": (55.68, 12.57),
    "UK-GOLDEN": (51.51, -0.13),
    "DE-MUNICH": (48.14, 11.58),
    "BE-FLANDERS": (51.05, 3.72),
    "JP-SHONAN": (35.34, 139.47),
}

# Screen-2 region for each country in the sheet (for the local-supply colour and the map tint).
COUNTRY_REGION = {
    "United States": coverage_ingest.NA,
    "South Korea": coverage_ingest.HG,
    "Singapore": coverage_ingest.HG,
    "China": coverage_ingest.HG,
    "India": coverage_ingest.HG,
    "Brazil": coverage_ingest.HG,
    "Ireland": coverage_ingest.WE,
    "Switzerland": coverage_ingest.WE,
    "Denmark": coverage_ingest.WE,
    "United Kingdom": coverage_ingest.WE,
    "Germany": coverage_ingest.WE,
    "Belgium": coverage_ingest.WE,
    "Japan": coverage_ingest.JP,
    "Australia": coverage_ingest.JP,
}

# ISO3 for the map tint, by screen-2 region.
MAP_ISO3 = {
    coverage_ingest.NA: ["USA"],
    coverage_ingest.WE: ["IRL", "CHE", "DNK", "GBR", "DEU", "BEL", "FRA", "ESP"],
    coverage_ingest.HG: ["CHN", "IND", "KOR", "SGP", "BRA"],
    coverage_ingest.JP: ["JPN", "AUS"],
}


@dataclass
class ScreenData:
    facts: list[dict] = field(default_factory=list)
    signals: list[dict] = field(default_factory=list)
    countries: list[dict] = field(default_factory=list)
    local_steps: dict[str, int] = field(
        default_factory=dict
    )  # Cytiva manufacturing steps by region


def _rows(conn: sqlite3.Connection, sql: str) -> list[dict]:
    cur = conn.execute(sql)
    names = [d[0] for d in cur.description]
    return [dict(zip(names, row, strict=True)) for row in cur.fetchall()]


def _local_steps(conn: sqlite3.Connection) -> dict[str, int]:
    """Cytiva's manufacturing steps made in each region (screen 2 rule). Service is not counted."""
    cells = coverage_metrics.footprint_cells(conn)
    steps = coverage_metrics.step_cells(cells)
    out = {}
    for region in (coverage_ingest.NA, coverage_ingest.WE, coverage_ingest.HG, coverage_ingest.JP):
        out[region] = sum(
            1
            for (company, reg, step), cell in steps.items()
            if company == "Cytiva"
            and reg == region
            and not step.startswith("8.")
            and cell["status"] == "Made"
        )
    return out


def load(conn: sqlite3.Connection) -> ScreenData | None:
    """All screen data, or None when the tables are not loaded yet."""
    try:
        facts = _rows(conn, "SELECT * FROM cluster_fact ORDER BY fact_id")
        signals = _rows(conn, "SELECT * FROM market_signal ORDER BY indicator_id")
        countries = _rows(
            conn, "SELECT * FROM country_barrier_index ORDER BY barrier_index DESC, country"
        )
        local = _local_steps(conn)
    except sqlite3.OperationalError:
        return None
    if not facts:
        return None
    return ScreenData(facts=facts, signals=signals, countries=countries, local_steps=local)


def hub_region(country: str) -> str | None:
    return COUNTRY_REGION.get(country)


def local_colour(region: str | None, local_steps: dict[str, int]) -> tuple[str, str]:
    """MVP legend: green mostly local (5 to 7 of 7 steps), amber partly local (1 to 4), red
    imported (0)."""
    if region is None or region not in local_steps:
        return "#9AA5B1", "not assessed"
    n = local_steps[region]
    if n >= 5:
        return "#2E9E5B", "mostly local"
    if n >= 1:
        return "#E0A44A", "partly local"
    return "#C2412D", "imported"


def density_rows(data: ScreenData) -> list[dict]:
    """One row per hub, ranked by its density count. A hub with a cluster-scope count uses that;
    city-wide counts are used only where no cluster-scope count exists, and are marked as such."""
    by_hub: dict[str, dict] = {}
    for f in data.facts:
        unit = (f["unit"] or "").strip()
        if f["value"] is None or not any(unit.startswith(u) for u in DENSITY_UNITS):
            continue
        scope = f["scope"] or "n/a"
        if scope not in ("cluster", "city-wide"):
            continue
        hub = f["cluster_id"]
        current = by_hub.get(hub)
        rank = (scope == "cluster", f["value"])
        if current is None or rank > current["_rank"]:
            by_hub[hub] = {
                "_rank": rank,
                "hub_id": hub,
                "hub": f["cluster"],
                "country": f["country"],
                "count": f["value"],
                "type": unit.split(" (")[0],
                "scope": scope,
                "as_of": f["as_of"],
                "confidence": f["confidence"],
                "source_title": f["source_title"],
                "source_url": f["source_url"],
            }
    rows = sorted(by_hub.values(), key=lambda r: r["count"], reverse=True)
    for r in rows:
        r.pop("_rank")
    return rows


def all_hubs(data: ScreenData) -> list[dict]:
    """Every hub in the sheet, with its position and density count (None where not in the sheet)."""
    counts = {r["hub_id"]: r for r in density_rows(data)}
    names = {}
    for f in data.facts:
        names.setdefault(f["cluster_id"], (f["cluster"], f["country"]))
    out = []
    for hub_id, (name, country) in names.items():
        c = counts.get(hub_id)
        out.append(
            {
                "hub_id": hub_id,
                "hub": name,
                "country": country,
                "region": hub_region(country),
                "count": c["count"] if c else None,
                "type": c["type"] if c else None,
                "scope": c["scope"] if c else None,
                "source_url": c["source_url"] if c else None,
                "position": HUB_POSITION.get(hub_id),
            }
        )
    return out


def bubble_size(count: float | None) -> float:
    """Marker size, square-root scaled; a hub with no count gets a small fixed marker."""
    if count is None:
        return 7
    return max(10, min(46, 4.2 * math.sqrt(count)))


def directional_signals(data: ScreenData) -> list[dict]:
    """Signals that state a change: up (green arrow) or down (red arrow)."""
    return [s for s in data.signals if s["direction"] in ("up", "down")]


def kpis(data: ScreenData) -> dict:
    hubs = all_hubs(data)
    counted = [h for h in hubs if h["count"] is not None]
    densest = max(counted, key=lambda h: h["count"]) if counted else None
    return {
        "hubs": len(hubs),
        "hubs_with_count": len(counted),
        "densest": densest,
        "tariff_countries": len(data.countries),
    }
