"""Demand drivers data (Screen 4), from the research sheet "Screen 4 - Demand drivers data".

The sheet's tabs are saved as CSV under data/demand/ and loaded here with their source URLs.
A row without a source URL is rejected by store.upsert and is not shown. The product-use
matrix (tile 8) is a hypothesis without a source, so it is not loaded: the screen shows it as
to collect until Cytiva product evidence is in.
"""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

from src.ingest import store

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data" / "demand"

# (csv file, table, columns that can hold the row's source URL, in order)
SPECS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("burden_country.csv", "demand_burden", ("cancer_source_url", "diabetes_source_url")),
    ("pipeline_type.csv", "demand_pipeline", ("source_url",)),
    ("approvals.csv", "demand_approval", ("source_url",)),
    ("expiries.csv", "demand_expiry", ("source_url",)),
    ("policy.csv", "demand_policy", ("source_url",)),
    ("top_drugs.csv", "demand_top_drug", ("source_url",)),
    ("capacity.csv", "demand_capacity", ("source_url",)),
    ("product_use.csv", "demand_product_use", ()),
)


def _read(name: str) -> list[dict]:
    with (DATA_DIR / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_demand(conn: sqlite3.Connection, run_id: int) -> int:
    """Write the sheet's rows to the app database. Returns the number of rows accepted."""
    written = 0
    for filename, table, url_columns in SPECS:
        for raw in _read(filename):
            row = {k: (v if v != "" else None) for k, v in raw.items()}
            url = next((raw[c] for c in url_columns if raw.get(c)), None)
            confidence = raw.get("confidence") or ""
            label = raw.get("label") or ("Signal" if confidence == "L" else "Fact")
            if table == "demand_product_use":
                label = "Hypothesis"  # analyst judgement; no source URL by design (empty = none)
            row.update(
                {
                    "source_url": url or "",
                    "source_type": "document",
                    "published_date": None,
                    "evidence_label": label,
                }
            )
            if store.upsert(conn, run_id, table, row) != "rejected":
                written += 1
    return written
