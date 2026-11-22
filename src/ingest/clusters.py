"""Customer clusters data (Screen 3), from the research sheet "Screen 3 - Customer clusters data".

The sheet's tabs are exported to data/clusters/sheet/ by scripts/export_seed_sheets.py and read
through their header maps (src/ingest/sheet_headers.py). A header the map does not know, or a
mapped header that is missing, fails the load.

Legacy exception (owner decision, 22 Nov 2026). Three things are not in the sheet yet and are
still read from the old CSVs, marked LEGACY in code, in docs/phase0-screen3-legacy.md:
  - the Tholos Trade Barrier Index 2025 score and its source URL (tbi_2025_score);
  - the applied tariff percentage, its year and the WTO tariff score (tariff_*);
  - the direction (up or down) of each market signal (market_signal.direction).
A test fails as soon as the sheet has the matching column, so the exception cannot linger.

Every row keeps a source URL. The barrier rows take the URL of their first Source ID that the
Data Sources tab gives; a row without a URL is rejected by store.upsert and is not shown.

The barrier index is the average of the three dimensions the screen shows (customs friction,
tariff score, local preference), over the scores present; a blank score is not zero. The sheet's
own average uses different dimensions, so it is kept in sheet_barrier_index for comparison.
"""

from __future__ import annotations

import csv
import re
import sqlite3
from pathlib import Path

from src.ingest import store
from src.ingest.sheet_headers import read_sheet

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data" / "clusters"
SHEET_DIR = DATA_DIR / "sheet"
LEGACY_BARRIER = DATA_DIR / "country_barrier.csv"  # LEGACY: Tholos, tariff, tariff URL
LEGACY_SIGNALS = DATA_DIR / "market_signals.csv"  # LEGACY: direction only
LEGACY_FACTS = DATA_DIR / "clusters.csv"  # LEGACY: scope (cluster, city-wide, capacity) only

NATURE_INDEX_URL = (
    "https://www.nature.com/nature-index/research-leaders/2025/country/biological-sciences/global"
)
LEGACY_FIELDS = (
    "tbi_2025_score, tbi_source_url, tariff_applied_pct, tariff_year, tariff_score_1_5, "
    "tariff_source_url, direction, scope"
)


def _num(text: str | None) -> float | None:
    """A number from a sheet cell: commas and a trailing percent sign are removed. Text is None."""
    text = (text or "").strip().replace(",", "").removesuffix("%")
    try:
        return float(text)
    except ValueError:
        return None


def _int(text: str | None) -> int | None:
    value = _num(text)
    return None if value is None else int(value)


def _legacy_by_key(path: Path, key: str) -> dict[str, dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        return {r[key]: r for r in csv.DictReader(handle)}


def _urls() -> dict[str, str]:
    """Source ID -> URL, from the Data Sources tab."""
    return {
        r["source_id"]: r["url"]
        for r in read_sheet(SHEET_DIR / "data_sources.csv")
        if re.fullmatch(r"S\d+", r["source_id"] or "")
    }


def load_clusters(conn: sqlite3.Connection, run_id: int) -> int:
    """Write the sheet's rows to the app database. Returns the number of rows accepted."""
    written = 0
    urls = _urls()
    # LEGACY: scope of each fact (not in the sheet tab yet).
    scope = {k: r["scope"] or None for k, r in _legacy_by_key(LEGACY_FACTS, "fact_id").items()}
    for r in read_sheet(SHEET_DIR / "clusters.csv"):
        if not re.fullmatch(r"F\d+", r["fact_id"] or ""):
            continue  # notes under the table
        if _num(r["value"]) is None:
            continue  # a placeholder without a figure is not stored
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
                    "scope": scope.get(r["fact_id"]),  # LEGACY
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

    for r in read_sheet(SHEET_DIR / "cdmo_sites.csv"):
        if not re.fullmatch(r"CD\d+", r["site_id"] or ""):
            continue
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

    # LEGACY: direction of each signal (not in the sheet yet).
    direction = {
        k: r["direction"] or None for k, r in _legacy_by_key(LEGACY_SIGNALS, "indicator_id").items()
    }
    for r in read_sheet(SHEET_DIR / "market_signals.csv"):
        if not re.fullmatch(r"M\d+", r["indicator_id"] or ""):
            continue
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
                    "direction": direction.get(r["indicator_id"]),  # LEGACY
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

    # LEGACY: Tholos index, applied tariff and tariff score per country.
    legacy = _legacy_by_key(LEGACY_BARRIER, "country")
    for r in read_sheet(SHEET_DIR / "country_barriers.csv"):
        if not r["iso3"]:
            continue  # notes under the table
        old = legacy.get(r["country"], {})
        customs = _num(r["customs_friction_1_5"])
        tariff_score = _num(old.get("tariff_score_1_5"))  # LEGACY
        local = _num(r["local_preference_1_5"])
        present = [v for v in (customs, tariff_score, local) if v is not None]
        sheet_urls = [urls[s] for s in re.findall(r"S\d+", r["source_ids"] or "") if s in urls]
        url = next((u for u in sheet_urls if u.startswith("https://")), None)
        url = url or old.get("tariff_source_url") or None
        if (
            store.upsert(
                conn,
                run_id,
                "country_barrier_index",
                {
                    "country": r["country"],
                    "lpi_customs_score_2023": _num(r["lpi_customs_score_2023"]),
                    "customs_friction_1_5": customs,
                    "tariff_applied_pct": _num(old.get("tariff_applied_pct")),  # LEGACY
                    "tariff_year": _int(old.get("tariff_year")),  # LEGACY
                    "tariff_score_1_5": tariff_score,  # LEGACY
                    "local_preference_1_5": local,
                    "regulatory_friction_1_5": _num(r["regulatory_friction_1_5"]),
                    "geopolitical_risk_1_5": _num(r["geopolitical_risk_1_5"]),
                    "tbi_2025_score": _num(old.get("tbi_2025_score")),  # LEGACY
                    "barrier_index": round(sum(present) / len(present), 2) if present else None,
                    "barrier_scores_available": len(present),
                    "sheet_barrier_index": _num(r["sheet_barrier_index"]),
                    "sheet_scores_available": _int(r["sheet_scores_available"]),
                    "display_on_tile": r["display_on_tile"] or None,
                    "source_ids": r["source_ids"] or None,
                    "legacy_fields": LEGACY_FIELDS,
                    "confidence": r["confidence"],
                    "source_url": url,
                    "source_type": "document",
                    "published_date": None,
                    "evidence_label": "Signal",
                },
            )
            != "rejected"
        ):
            written += 1

    # Demand by country. The Nature Index column is 2025 in the sheet. Not read by a metric yet.
    nature_url = urls.get("S24", NATURE_INDEX_URL)
    for r in read_sheet(SHEET_DIR / "demand_by_country.csv"):
        if not r["region"]:
            continue  # notes under the table
        if (
            store.upsert(
                conn,
                run_id,
                "country_demand",
                {
                    "country": r["country"],
                    "region": r["region"],
                    "nature_index_share_2025": _num(r["nature_index_share_2025"]),
                    "fda_drug_sites_fy2024": _int(r["fda_drug_sites_fy2024"]),
                    "trial_registrations_since_2019": _int(r["trial_registrations_since_2019"]),
                    "cdmo_biologics_sites": _int(r["cdmo_biologics_sites"]),
                    "cdmo_capacity_l": _num(r["cdmo_capacity_l"]),
                    "demand_score": _num(r["demand_score"]),
                    "segments_with_evidence": _int(r["segments_with_evidence"]),
                    "confidence": "H",
                    "source_url": nature_url,
                    "source_type": "document",
                    "published_date": None,
                    "evidence_label": "Fact",
                },
            )
            != "rejected"
        ):
            written += 1

    # Read through their header maps so a change fails the load; not stored yet.
    read_sheet(SHEET_DIR / "demand_by_region.csv")
    read_sheet(SHEET_DIR / "research_institutions.csv")
    return written
