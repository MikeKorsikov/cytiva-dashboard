"""China screen data (Screen 6), from the research sheet "China data".

The sheet's tabs are saved as CSV under data/china/ and loaded here. Every row is checked by
store.upsert: a row needs an https source URL (the first S-ID of its source list), except a
Hypothesis row, which is labelled as such. Evidence labels: a row is Fact when its confidence is
H, otherwise Signal; headline and opportunity rows carry their own label from the sheet.

Amounts are shown in USD. RMB figures are converted at CNY_USD_RATE, an assumption that is
stored with each converted value and flagged on the screen until the annual average is loaded.
"""

from __future__ import annotations

import csv
import re
import sqlite3
from pathlib import Path

from src.ingest import store
from src.ingest.schema import table_by_name

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data" / "china"

# Assumed RMB per USD for every RMB figure. Replace with the PBoC 2025 annual average when loaded.
CNY_USD_RATE = 7.2

# Sheet product codes -> the family names used by the screen 2 step rule (metrics.coverage).
FAMILY_NAMES = {
    "Med": "Media",
    "SU": "Single-use",
    "Res": "Resins",
    "Filt": "Filtration",
    "Fill": "Filling",
    "Gen": "Genomic",
    "Sys": "Systems",
    "Anl": "Analytical",
}


def _rows(name: str) -> list[dict]:
    with (DATA_DIR / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _ids(text: str | None) -> list[str]:
    return re.findall(r"S\d+", text or "")


def _num(text: str | None) -> float | None:
    try:
        return float((text or "").strip().replace(",", ""))
    except ValueError:
        return None


def _clean(raw: dict, table: str, rename: dict[str, str] | None = None) -> dict:
    """Keep only the columns the table defines, renamed where the sheet's name differs."""
    columns = set(table_by_name(table).columns)
    row: dict = {}
    for key, value in raw.items():
        name = (rename or {}).get(key, key)
        if name in columns:
            row[name] = value.strip() if value and value.strip() else None
    return row


def _put(conn, run_id: int, table: str, row: dict, url: str, label: str) -> str:
    row.update(
        {
            "source_url": url,
            "source_type": "document" if url else "curated",
            "published_date": None,
            "evidence_label": label,
        }
    )
    return store.upsert(conn, run_id, table, row)


def _label(confidence: str) -> str:
    return "Fact" if confidence == "H" else "Signal"


def load_china(conn: sqlite3.Connection, run_id: int) -> int:
    """Store the screen 6 rows. Returns the number of rows accepted. Re-runnable: rows are
    upserted by their IDs, so a second run changes nothing."""
    sources = {r["id"]: r for r in _rows("sources.csv")}
    headline = {r["id"]: r for r in _rows("headline.csv")}

    def url_for(source_ids: str | None) -> str:
        for s in _ids(source_ids):
            if s in sources:
                return sources[s]["url"]
        return ""

    accepted = 0

    def count(status: str) -> None:
        nonlocal accepted
        if status != "rejected":
            accepted += 1

    for raw in _rows("sources.csv"):
        if not re.fullmatch(r"S\d+", raw["id"] or ""):
            continue
        row = _clean(raw, "cn_source", {"date": "date_text", "type": "source_kind"})
        count(_put(conn, run_id, "cn_source", row, raw["url"], "Fact"))

    for raw in _rows("companies.csv"):
        row = _clean(raw, "cn_company", {"source_ids": "source_note"})
        count(
            _put(
                conn,
                run_id,
                "cn_company",
                row,
                url_for(raw["source_ids"]),
                _label(raw["confidence"]),
            )
        )

    evidence_by_key: dict[tuple[str, str], dict] = {}
    for raw in _rows("coverage_evidence.csv"):
        row = _clean(raw, "cn_coverage_evidence", {"source_ids": "source_note"})
        status = _put(
            conn,
            run_id,
            "cn_coverage_evidence",
            row,
            url_for(raw["source_ids"]),
            _label(raw["confidence"]),
        )
        count(status)
        if status != "rejected":
            evidence_by_key.setdefault((raw["company_id"], raw["family"]), raw)

    for raw in _rows("coverage_grid.csv"):
        evidence = evidence_by_key.get((raw["company_id"], raw["family"]))
        if evidence is None:
            continue  # a grid mark without evidence is not shown
        row = _clean(raw, "cn_coverage")
        row["evidence_id"] = evidence["evidence_id"]
        count(
            _put(
                conn,
                run_id,
                "cn_coverage",
                row,
                url_for(evidence["source_ids"]),
                _label(evidence["confidence"]),
            )
        )

    for raw in _rows("financials.csv"):
        row = _clean(raw, "cn_financial", {"source_ids": "source_note"})
        for key in ("revenue_yoy_pct", "gross_margin_pct", "rd_to_revenue_pct"):
            row[key] = _num(raw[key])
        row["net_profit_rmb_m"] = _num(raw["net_profit_rmb_m"])
        rmb = _num(raw["revenue_rmb_m"])
        row["revenue_rmb_m"] = rmb
        if raw["company_id"] == "C00":
            # Danaher's China sales in USD are derived from the headline (H-03), not from RMB.
            row["revenue_usd_m"] = _num(headline["H-03"]["value"]) * 1000
            row["cny_usd_rate"] = None
        elif rmb is not None:
            row["revenue_usd_m"] = round(rmb / CNY_USD_RATE, 1)
            row["cny_usd_rate"] = CNY_USD_RATE
        count(
            _put(
                conn,
                run_id,
                "cn_financial",
                row,
                url_for(raw["source_ids"]),
                _label(raw["confidence"]),
            )
        )

    for raw in _rows("vendors.csv"):
        row = _clean(raw, "cn_vendor", {"source_ids": "source_note"})
        count(
            _put(
                conn,
                run_id,
                "cn_vendor",
                row,
                url_for(raw["source_ids"]),
                _label(raw["confidence"]),
            )
        )

    for raw in _rows("opportunities.csv"):
        row = _clean(
            raw, "cn_opportunity", {"source_ids": "source_note", "label": "evidence_label"}
        )
        count(
            _put(
                conn,
                run_id,
                "cn_opportunity",
                row,
                url_for(raw["source_ids"]),
                raw["label"],
            )
        )

    for raw in _rows("implications.csv"):
        row = _clean(raw, "cn_implication")
        count(_put(conn, run_id, "cn_implication", row, "", "Hypothesis"))

    for raw in headline.values():
        row = _clean(
            raw,
            "cn_headline",
            {"value": "value_text", "source_ids": "source_note"},
        )
        row["value_num"] = _num(raw["value"])
        count(
            _put(
                conn,
                run_id,
                "cn_headline",
                row,
                url_for(raw["source_ids"]),
                raw["evidence_label"],
            )
        )

    conn.commit()
    return accepted
