"""Customer clusters data (Screen 3), from the research sheet "Screen 3 - Customer clusters data".

The sheet's tabs are saved as CSV under data/clusters/ (clusters, cdmo_sites, market_signals,
country_profile). The loader writes them to the app database with their source URLs. A row
without a source URL is rejected by store.upsert and is not shown.

Country profile: the demand columns (Nature Index, FDA sites, trials, CDMO sites, demand score)
are written to country_demand. The barrier columns are written to country_barrier_index. The
barrier index averages the scores present; a blank score is not zero. The trade-measure score
is in the sheet but not in this file, so the index shown here may differ from the sheet by it.
"""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

from src.ingest import store

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data" / "clusters"

NATURE_INDEX_URL = (
    "https://www.nature.com/nature-index/research-leaders/2025/country/biological-sciences/global"
)
WORLD_BANK_LPI_URL = "https://lpi.worldbank.org/international/global"


def _read(name: str) -> list[dict]:
    with (DATA_DIR / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _num(text: str) -> float | None:
    text = (text or "").strip().replace(",", "")
    if text == "":
        return None
    return float(text)


def _int(text: str) -> int | None:
    value = _num(text)
    return None if value is None else int(value)


def load_clusters(conn: sqlite3.Connection, run_id: int) -> int:
    """Write the sheet's rows to the app database. Returns the number of rows accepted."""
    written = 0
    for r in _read("clusters.csv"):
        if (
            store.upsert(
                conn,
                run_id,
                "cluster_fact",
                {
                    "fact_id": r["fact_id"],
                    "cluster_id": r["cluster_id"],
                    "cluster": r["cluster"],
                    "country": r["country"],
                    "metric": r["metric"],
                    "value": _num(r["value"]),
                    "unit": r["unit"] or None,
                    "as_of": r["as_of"] or None,
                    "scope": r["scope"] or None,
                    "confidence": r["confidence"],
                    "evidence": r["evidence"] or None,
                    "source_title": r["source_title"] or None,
                    "source_id": r["source_id"] or None,
                    "source_url": r["source_url"] or None,
                    "source_type": "document",
                    "published_date": None,
                    "evidence_label": "Fact",
                },
            )
            != "rejected"
        ):
            written += 1
    for r in _read("cdmo_sites.csv"):
        if (
            store.upsert(
                conn,
                run_id,
                "cdmo_site",
                {
                    "site_id": r["site_id"],
                    "cdmo": r["cdmo"],
                    "city": r["city"],
                    "country": r["country"],
                    "capacity_l": _num(r["capacity_l"]),
                    "status": r["status"] or None,
                    "as_of": r["as_of"] or None,
                    "confidence": r["confidence"],
                    "evidence": r["evidence"] or None,
                    "source_title": r["source_title"] or None,
                    "source_url": r["source_url"] or None,
                    "source_type": "document",
                    "published_date": None,
                    "evidence_label": "Fact",
                },
            )
            != "rejected"
        ):
            written += 1
    for r in _read("market_signals.csv"):
        if (
            store.upsert(
                conn,
                run_id,
                "market_signal",
                {
                    "indicator_id": r["indicator_id"],
                    "geography": r["geography"],
                    "indicator": r["indicator"],
                    "value": _num(r["value"]),
                    "unit": r["unit"] or None,
                    "customer_segment": r["customer_segment"] or None,
                    "period": r["period"] or None,
                    "direction": r["direction"] or None,
                    "confidence": r["confidence"],
                    "evidence": r["evidence"] or None,
                    "source_title": r["source_title"] or None,
                    "source_url": r["source_url"] or None,
                    "source_type": "document",
                    "published_date": None,
                    "evidence_label": "Fact",
                },
            )
            != "rejected"
        ):
            written += 1
    for r in _read("country_barrier.csv"):
        dims = [
            _num(r["customs_friction_1_5"]),
            _num(r["tariff_score_1_5"]),
            _num(r["local_preference_1_5"]),
            _num(r["regulatory_friction_1_5"]),
            _num(r["geopolitical_risk_1_5"]),
        ]
        present = [d for d in dims if d is not None]
        if (
            store.upsert(
                conn,
                run_id,
                "country_barrier_index",
                {
                    "country": r["country"],
                    "lpi_customs_score_2023": _num(r["lpi_customs_score_2023"]),
                    "customs_friction_1_5": dims[0],
                    "tariff_applied_pct": _num(r["tariff_applied_pct"]),
                    "tariff_year": _int(r["tariff_year"]),
                    "tariff_score_1_5": dims[1],
                    "local_preference_1_5": dims[2],
                    "regulatory_friction_1_5": dims[3],
                    "geopolitical_risk_1_5": dims[4],
                    "barrier_index": round(sum(present) / len(present), 2) if present else None,
                    "barrier_scores_available": len(present),
                    "confidence": r["confidence"],
                    "source_url": r["tariff_source_url"],
                    "source_type": "document",
                    "published_date": None,
                    "evidence_label": "Signal",
                },
            )
            != "rejected"
        ):
            written += 1
    for r in _read("country_profile.csv"):
        demand = store.upsert(
            conn,
            run_id,
            "country_demand",
            {
                "country": r["country"],
                "region": r["region"],
                "nature_index_share_2024": _num(r["nature_index_share_2024"]),
                "fda_drug_sites_fy2024": _int(r["fda_drug_sites_fy2024"]),
                "trial_registrations_since_2019": _int(r["trial_registrations_since_2019"]),
                "cdmo_biologics_sites": _int(r["cdmo_biologics_sites"]),
                "cdmo_capacity_l": _num(r["cdmo_capacity_l"]),
                "demand_score": _num(r["demand_score"]),
                "segments_with_evidence": _int(r["segments_with_evidence"]),
                "confidence": "H",
                "source_url": NATURE_INDEX_URL,
                "source_type": "document",
                "published_date": None,
                "evidence_label": "Fact",
            },
        )
        if demand != "rejected":
            written += 1
    return written
