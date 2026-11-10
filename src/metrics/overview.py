"""Data for the Overview screen, read from the app database.

Pure functions: each takes a read-only connection and returns plain Python values, so the
Streamlit page only renders them. Missing values are None (shown as "n/d" or "to collect").
"""

from __future__ import annotations

import sqlite3
import statistics
from datetime import date
from pathlib import Path

import pandas as pd

from src.ingest.prices import LISTED_PEERS, summarise
from src.metrics.deals import CATEGORIES, deal_counts
from src.metrics.fundamentals import free_cash_flow, margin_pct, yoy_growth_pct

# Peer order on the screen, by company_id as stored in the database.
FINANCIAL_COMPANIES: tuple[str, ...] = (
    "DHR",
    "TMO",
    "RGEN",
    "AVTR",
    "Sartorius",
    "Merck KGaA",
)
NEWS_COMPANIES: tuple[str, ...] = (
    "Danaher",
    "Cytiva",
    "Thermo Fisher",
    "Sartorius",
    "Repligen",
    "Avantor",
    "Merck KGaA",
)
# Hypotheses from the BRD, to test internally. Labelled Hypothesis on the page, never as findings.
IMPLICATIONS: tuple[str, ...] = (
    "Can Finance forecast from order lines across both ERPs?",
    "Can sales to one customer group be combined across Danaher companies?",
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


def _metric(
    conn: sqlite3.Connection, company: str, year: int, metric: str, *, local: bool = False
) -> float | None:
    column = "value_local" if local else "value_usd"
    row = conn.execute(
        f"SELECT {column} AS v FROM financial_metric WHERE company_id = ? AND fiscal_year = ? "
        "AND metric = ?",
        (company, year, metric),
    ).fetchone()
    return row["v"] if row else None


def financial_table(conn: sqlite3.Connection) -> list[dict]:
    """FY metrics for the US peers: revenue, growth, gross, net and FCF margins (USD)."""
    rows = []
    for company in FINANCIAL_COMPANIES:
        name_row = conn.execute(
            "SELECT name FROM company WHERE company_id = ?", (company,)
        ).fetchone()
        year_row = conn.execute(
            "SELECT MAX(fiscal_year) AS y FROM financial_metric "
            "WHERE company_id = ? AND metric = 'revenue'",
            (company,),
        ).fetchone()
        year = year_row["y"]
        revenue = _metric(conn, company, year, "revenue") if year else None
        # Growth is measured in the reporting currency, so currency moves do not show as growth.
        revenue_local = _metric(conn, company, year, "revenue", local=True) if year else None
        prior_local = _metric(conn, company, year - 1, "revenue", local=True) if year else None
        gross = _metric(conn, company, year, "gross_profit") if year else None
        net = _metric(conn, company, year, "net_income") if year else None
        ocf = _metric(conn, company, year, "operating_cash_flow") if year else None
        capex = _metric(conn, company, year, "capex") if year else None
        fcf = free_cash_flow(ocf, capex)
        rows.append(
            {
                "company": name_row["name"] if name_row else company,
                "fiscal_year": year,
                "revenue_usd": revenue,
                "growth_pct": yoy_growth_pct(revenue_local, prior_local),
                "gross_margin_pct": margin_pct(gross, revenue),
                "net_margin_pct": margin_pct(net, revenue),
                "fcf_usd": fcf,
                "fcf_margin_pct": margin_pct(fcf, revenue),
            }
        )
    return _in_peer_order(rows, "company")


def latest_news(conn: sqlite3.Connection, per_company: int = 1) -> list[dict]:
    """Most recent headlines per company, newest first, for the competitor news column."""
    result = []
    for company in NEWS_COMPANIES:
        rows = conn.execute(
            "SELECT item_date, tag, headline, url, summary FROM news_item "
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
