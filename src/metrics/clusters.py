"""Customer clusters (Screen 3): the numbers the screen shows, read from the app database.

Every value here comes from a stored row with its source URL. Nothing is estimated. Where the
sheet has no figure, the screen shows "to collect".
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field

CAPACITY_METRIC = "Biologics production capacity in cluster"


@dataclass
class Clusters:
    cdmo_sites: list[dict] = field(default_factory=list)
    cluster_facts: list[dict] = field(default_factory=list)
    signals: list[dict] = field(default_factory=list)
    countries: list[dict] = field(default_factory=list)


def _rows(conn: sqlite3.Connection, sql: str) -> list[dict]:
    cur = conn.execute(sql)
    names = [d[0] for d in cur.description]
    return [dict(zip(names, row, strict=True)) for row in cur.fetchall()]


def load(conn: sqlite3.Connection) -> Clusters | None:
    """All screen data, or None when the tables are not loaded yet."""
    try:
        cdmo = _rows(conn, "SELECT * FROM cdmo_site ORDER BY country, cdmo, city")
        facts = _rows(conn, "SELECT * FROM cluster_fact ORDER BY cluster, fact_id")
        signals = _rows(conn, "SELECT * FROM market_signal ORDER BY indicator_id")
        countries = _rows(
            conn,
            "SELECT d.*, b.barrier_index, b.barrier_scores_available, b.lpi_customs_score_2023, "
            "b.customs_friction_1_5, b.local_preference_1_5, b.regulatory_friction_1_5, "
            "b.geopolitical_risk_1_5, b.confidence AS barrier_confidence "
            "FROM country_demand d LEFT JOIN country_barrier_index b USING (country) "
            "ORDER BY d.demand_score DESC, d.country",
        )
    except sqlite3.OperationalError:
        return None
    if not cdmo and not facts:
        return None
    return Clusters(cdmo_sites=cdmo, cluster_facts=facts, signals=signals, countries=countries)


def kpis(data: Clusters) -> dict:
    """Headline figures. A figure the sheet does not give is None, not zero."""
    listed = [s for s in data.cdmo_sites if s["capacity_l"] is not None]
    clusters = sorted({f["cluster"] for f in data.cluster_facts})
    capacity = [f for f in data.cluster_facts if f["metric"] == CAPACITY_METRIC and f["value"]]
    largest = max(capacity, key=lambda f: f["value"]) if capacity else None
    return {
        "cdmo_sites": len(data.cdmo_sites),
        "cdmo_sites_with_capacity": len(listed),
        "cdmo_capacity_l": sum(s["capacity_l"] for s in listed) if listed else None,
        "clusters_with_facts": len(clusters),
        "largest_cluster": largest,
    }


def cluster_table(data: Clusters) -> list[dict]:
    """One row per cluster: its headline fact (the first sourced numeric fact), with the source."""
    out: dict[str, dict] = {}
    for f in data.cluster_facts:
        if f["value"] is None or f["cluster"] in out:
            continue
        out[f["cluster"]] = {
            "cluster": f["cluster"],
            "country": f["country"],
            "metric": f["metric"],
            "value": f["value"],
            "unit": f["unit"],
            "as_of": f["as_of"],
            "confidence": f["confidence"],
            "source_title": f["source_title"],
            "source_url": f["source_url"],
        }
    return list(out.values())


def barrier_table(data: Clusters) -> list[dict]:
    """Countries with a barrier index, highest first. The index averages the scores present."""
    rows = [c for c in data.countries if c["barrier_index"] is not None]
    return sorted(rows, key=lambda c: c["barrier_index"], reverse=True)
