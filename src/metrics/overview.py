"""Data for the Overview screen, read from the app database.

Pure functions: each takes a read-only connection and returns plain Python values, so the
Streamlit page only renders them. Missing values are None (shown as "n/d" or "to collect").
"""

from __future__ import annotations

import sqlite3
import statistics
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from src.ingest.prices import LISTED_PEERS, summarise
from src.metrics.deals import sheet_m_and_a_12m

# Peer order on the screen, by company_id as stored in the database.
NEWS_COMPANIES: tuple[str, ...] = (
    "Danaher",
    "Cytiva",
    "Thermo Fisher",
    "Sartorius",
    "Repligen",
    "Avantor",
    "Merck KGaA",
)
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


def attention_items(conn: sqlite3.Connection) -> list[dict]:
    """The attention items from the sheet (AT-nn), in sheet order."""
    try:
        rows = conn.execute("SELECT * FROM ov_attention ORDER BY id").fetchall()
    except sqlite3.OperationalError:
        return []
    return [dict(r) for r in rows]


def share_prices(conn: sqlite3.Connection) -> list[dict]:
    """Latest close in USD, 12-month change, and position in the 52-week range, per listed peer."""
    names = {peer.ticker: peer.company for peer in LISTED_PEERS}
    result = []
    for peer in LISTED_PEERS:
        rows = conn.execute(
            "SELECT price_date, close_usd FROM share_price_daily WHERE ticker = ? "
            "ORDER BY price_date",
            (peer.ticker,),
        ).fetchall()
        series = pd.Series(
            [r["close_usd"] for r in rows], index=[r["price_date"] for r in rows], dtype=float
        )
        stats = summarise(series)
        result.append(
            {
                "company": names[peer.ticker],
                "ticker": peer.ticker,
                "as_of": rows[-1]["price_date"] if rows else None,
                "last_close_usd": stats["last_close_usd"],
                "change_12m_pct": stats["change_12m_pct"],
                "position_in_range": stats["position_in_range"],
            }
        )
    return _in_peer_order(result, "company")


def latest_news(conn: sqlite3.Connection, per_company: int = 1) -> list[dict]:
    """Most recent headlines per company, newest first, for the competitor news column."""
    result = []
    for company in NEWS_COMPANIES:
        rows = conn.execute(
            "SELECT item_date, tag, headline, url, summary, evidence_label FROM news_item "
            "WHERE company_id = ? ORDER BY item_date DESC LIMIT ?",
            (company, per_company),
        ).fetchall()
        if not rows:
            result.append({"company": company, "headline": None})
        for r in rows:
            result.append(
                {
                    "company": company,
                    "date": r["item_date"],
                    "tag": r["tag"],
                    "headline": r["headline"],
                    "url": r["url"],
                    "publisher": r["summary"],
                    "evidence_label": r["evidence_label"],
                }
            )
    return _in_peer_order(result, "company")


RANKING_COMPANIES: tuple[str, ...] = (
    "Danaher",
    "Merck KGaA",  # group rank, as for Danaher
    "Thermo Fisher",
    "Sartorius",
    "Repligen",
    "Avantor",
)


def sheet_news(conn: sqlite3.Connection) -> list[dict]:
    """One seed news item per company from the sheet (T4), in PEER_ORDER. Used only where the
    news feed has no item for the company."""
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
    """Deal counts per buyer. M&A in the last 12 months counts the sheet's verified deals only.
    The 5-year counts and the licensing and collaboration counts are None (to collect): the sheet
    has no history for them yet. Feed deals are never counted (see feed_deal_signals)."""
    has_sheet = conn.execute(
        "SELECT COUNT(*) FROM deal WHERE source_type = 'document' AND evidence_label = 'Fact'"
    ).fetchone()[0]
    result = []
    for buyer in DEAL_BUYERS:
        row: dict = {"company": buyer}
        row["M&A 12m"] = sheet_m_and_a_12m(conn, buyer, as_of) if has_sheet else None
        row["M&A 5y"] = None
        for category in ("Licensing", "Collaboration"):
            row[f"{category} 12m"] = None
            row[f"{category} 5y"] = None
        result.append(row)
    return _in_peer_order(result, "company")


def feed_deal_signals(conn: sqlite3.Connection, as_of: date, limit: int = 8) -> dict:
    """Unverified M&A signals from the feed for the peers, last 12 months, newest first. Not
    counted. Returns the rows shown and the number not shown."""
    one_year = (as_of - timedelta(days=365)).isoformat()
    marks = ",".join("?" * len(DEAL_BUYERS))
    rows = conn.execute(
        f"SELECT acquirer, announced_date, headline, source_url FROM deal "
        f"WHERE source_type = 'news' AND category = 'M&A' AND status = 'announced' "
        f"AND acquirer IN ({marks}) AND announced_date BETWEEN ? AND ? "
        "ORDER BY announced_date DESC, acquirer",
        (*DEAL_BUYERS, one_year, as_of.isoformat()),
    ).fetchall()
    shown = [dict(r) for r in rows[:limit]]
    return {"shown": shown, "more": max(0, len(rows) - limit)}


PEER_METRICSPEER_METRICS: tuple[str, ...] = (
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


def news_for_screen(conn: sqlite3.Connection) -> list[dict]:
    """The news column: the feed's latest item per company. Where the feed has none, the sheet's
    seed item for that company, marked seed=True."""
    seeds = {r["company"]: r for r in sheet_news(conn)}
    result = []
    for item in latest_news(conn):
        if item.get("headline") is None and item["company"] in seeds:
            result.append({**seeds[item["company"]], "seed": True})
        else:
            result.append({**item, "seed": False})
    return result
