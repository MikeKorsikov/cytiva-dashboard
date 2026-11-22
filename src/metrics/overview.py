"""Data for the Overview screen, read from the app database.

Pure functions: each takes a read-only connection and returns plain Python values, so the
Streamlit page only renders them. Missing values are None (shown as "n/d" or "to collect").
"""

from __future__ import annotations

import sqlite3
import statistics
from datetime import date
from pathlib import Path

from src.metrics.deals import CATEGORIES, deal_counts

# Peer order on the screen, by company_id as stored in the database.
DEAL_BUYERS: tuple[str, ...] = (
    "Danaher",
    "Thermo Fisher",
    "Sartorius",
    "Repligen",
    "Avantor",
    "Merck KGaA",
)


# Order on every Overview tile: largest to smallest by FY2025 revenue in USD (the one size
# measure all tiles share). Cytiva is part of Danaher and has no revenue of its own; it comes last.
PEER_ORDER: tuple[str, ...] = (
    "Thermo Fisher",
    "Merck KGaA",
    "Danaher",
    "Avantor",
    "Sartorius",
    "Repligen",
    "Cytiva",
)


def _in_peer_order(rows: list[dict], key: str) -> list[dict]:
    """Rows sorted by PEER_ORDER; any company not in the order goes last, in its own order."""
    rank = {name: i for i, name in enumerate(PEER_ORDER)}
    return sorted(rows, key=lambda r: rank.get(r[key], len(PEER_ORDER)))


def layoff_marks(conn: sqlite3.Connection) -> list[dict]:
    """Layoff mark per company for 2026, 2025 and 2024, in PEER_ORDER. Missing cells: to collect."""
    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'layoff_year'"
    ).fetchone()
    if not exists:  # the database was not refreshed since this table was added
        return []
    rows = conn.execute(
        "SELECT company_id, year, announced, note, source_url FROM layoff_year"
    ).fetchall()
    by_company: dict[str, dict] = {}
    for r in rows:
        entry = by_company.setdefault(r["company_id"], {"company": r["company_id"], "years": {}})
        entry["years"][int(r["year"])] = {
            "mark": r["announced"],
            "note": r["note"],
            "url": r["source_url"],
        }
    return _in_peer_order(list(by_company.values()), "company")


def connect_readonly(path: Path) -> sqlite3.Connection:
    """Open the app database read-only. The app never writes; the refresh job does."""
    connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def _usd(value_m: float | None) -> float | None:
    """Millions to units, for the screen's $ columns (the sheet's values are in millions)."""
    return None if value_m is None else value_m * 1e6


def peer_financials(conn: sqlite3.Connection) -> list[dict]:
    """Peer financials from the sheet (T1), in PEER_ORDER. USD values from the sheet's USD column.
    Growth is the reported growth in the reporting currency. FCF in USD uses the sheet's own
    revenue conversion (USD revenue over local revenue) for the same row."""
    try:
        rows = conn.execute("SELECT * FROM ov_financial ORDER BY id").fetchall()
    except sqlite3.OperationalError:  # database refreshed before the overview tables existed
        return []
    result = []
    for r in rows:
        rate = (
            r["revenue_usd_m"] / r["revenue_local_m"]
            if r["revenue_usd_m"] and r["revenue_local_m"]
            else None
        )
        fcf_usd_m = (
            r["free_cash_flow_local_m"] * rate
            if rate and r["free_cash_flow_local_m"] is not None
            else None
        )
        result.append(
            {
                "company": r["company"].replace(" (group)", ""),
                "fiscal_year": r["fiscal_year"],
                "revenue_usd": _usd(r["revenue_usd_m"]),
                "growth_pct": r["growth_reported_pct"],
                "gross_margin_pct": r["gross_margin_pct"],
                "net_margin_pct": r["net_margin_pct"],
                "fcf_usd": _usd(fcf_usd_m),
                "fcf_margin_pct": r["fcf_margin_pct"],
                "confidence": r["confidence"],
                "evidence_label": r["evidence_label"],
                "source_url": r["source_url"],
            }
        )
    return _in_peer_order(result, "company")


def price_rows(conn: sqlite3.Connection) -> list[dict]:
    """The share-price list from the sheet (T3), with its state. Values are empty until the
    price feed runs, so the screen shows awaiting feed."""
    try:
        rows = conn.execute("SELECT * FROM ov_price ORDER BY id").fetchall()
    except sqlite3.OperationalError:
        return []
    return [dict(r) for r in rows]


def attention_items(conn: sqlite3.Connection) -> list[dict]:
    """The attention items from the sheet (AT-nn), in sheet order."""
    try:
        rows = conn.execute("SELECT * FROM ov_attention ORDER BY id").fetchall()
    except sqlite3.OperationalError:
        return []
    return [dict(r) for r in rows]


def latest_news(conn: sqlite3.Connection) -> list[dict]:
    """One news item per company from the sheet (T4), in PEER_ORDER. Until the news feed runs,
    these are the sheet's seed items."""
    try:
        rows = conn.execute("SELECT * FROM ov_news").fetchall()
    except sqlite3.OperationalError:
        return []
    result = [
        {
            "company": r["company"],
            "date": r["item_date"],
            "tag": r["tag"],
            "headline": r["headline"],
            "url": r["source_url"],
            "evidence_label": r["evidence_label"],
        }
        for r in rows
    ]
    return _in_peer_order(result, "company")


def implications(conn: sqlite3.Connection) -> list[dict]:
    """The implication hypotheses from the sheet (T5). Always Hypothesis."""
    try:
        rows = conn.execute("SELECT * FROM ov_implication ORDER BY id").fetchall()
    except sqlite3.OperationalError:
        return []
    return [dict(r) for r in rows]


RANKING_COMPANIES: tuple[str, ...] = (
    "Danaher",
    "Merck KGaA",  # group rank, as for Danaher
    "Thermo Fisher",
    "Sartorius",
    "Repligen",
    "Avantor",
)


def ranking_table(conn: sqlite3.Connection, ranking: str) -> list[dict]:
    """Curated ranks per company for two years. None = not ranked (or not eligible)."""
    result = []
    for company in RANKING_COMPANIES:
        row: dict = {"company": company}
        for year in (2026, 2025):
            found = conn.execute(
                "SELECT value FROM ranking WHERE company_id = ? AND ranking = ? AND year = ?",
                (company, ranking, year),
            ).fetchone()
            row[str(year)] = found["value"] if found else None
        result.append(row)
    return _in_peer_order(result, "company")


def ma_activity(conn: sqlite3.Connection, as_of: date) -> list[dict]:
    """Announced deals per buyer by category (12 months, 5 years). None = no data yet."""
    total = conn.execute("SELECT COUNT(*) AS n FROM deal").fetchone()["n"]
    result = []
    for buyer in DEAL_BUYERS:
        row: dict = {"company": buyer}
        counts = deal_counts(conn, buyer, as_of) if total else None
        for category in CATEGORIES:
            row[f"{category} 12m"] = None if counts is None else counts[category]["last_12m"]
            row[f"{category} 5y"] = None if counts is None else counts[category]["last_5y"]
        result.append(row)
    return _in_peer_order(result, "company")


PEER_METRICS: tuple[str, ...] = (
    "growth_pct",
    "gross_margin_pct",
    "net_margin_pct",
    "fcf_margin_pct",
)
LOWER_IS_BETTER: frozenset[str] = frozenset()
SUBJECT = "Danaher"  # the group is the subject of the screen; medians are over the other peers


def peer_median(rows: list[dict], key: str) -> float | None:
    """Median of a metric across the peers, excluding the subject (Danaher group)."""
    values = [r[key] for r in rows if r["company"] != SUBJECT and r[key] is not None]
    return statistics.median(values) if values else None


def best_worst(rows: list[dict], key: str) -> dict[str, str]:
    """'best' and 'weakest' company for a metric. Needs two values."""
    valued = [(r["company"], r[key]) for r in rows if r[key] is not None]
    if len(valued) < 2:
        return {}
    ordered = sorted(valued, key=lambda pair: pair[1], reverse=key not in LOWER_IS_BETTER)
    return {ordered[0][0]: "best", ordered[-1][0]: "weakest"}
