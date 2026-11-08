"""Data for the Overview screen, read from the app database.

Pure functions: each takes a read-only connection and returns plain Python values, so the
Streamlit page only renders them. Missing values are None (shown as "n/d" or "to collect").
"""

from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

import pandas as pd

from src.ingest.prices import LISTED_PEERS, summarise
from src.metrics.fundamentals import free_cash_flow, margin_pct, yoy_growth_pct

# Peer order on the screen, by company_id as stored in the database.
FINANCIAL_COMPANIES: tuple[str, ...] = ("DHR", "TMO", "RGEN", "AVTR")
NEWS_COMPANIES: tuple[str, ...] = (
    "Danaher",
    "Cytiva",
    "Thermo Fisher",
    "Sartorius",
    "Repligen",
    "Avantor",
    "Getinge",
    "Eppendorf",
    "Merck Life Science",
)
DEAL_BUYERS: tuple[str, ...] = (
    "Danaher",
    "Thermo Fisher",
    "Sartorius",
    "Repligen",
    "Avantor",
    "Getinge",
    "Eppendorf",
    "Merck Life Science",
)


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
    return result


def _metric(conn: sqlite3.Connection, company: str, year: int, metric: str) -> float | None:
    row = conn.execute(
        "SELECT value_usd FROM financial_metric WHERE company_id = ? AND fiscal_year = ? "
        "AND metric = ?",
        (company, year, metric),
    ).fetchone()
    return row["value_usd"] if row else None


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
        prior = _metric(conn, company, year - 1, "revenue") if year else None
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
                "growth_pct": yoy_growth_pct(revenue, prior),
                "gross_margin_pct": margin_pct(gross, revenue),
                "net_margin_pct": margin_pct(net, revenue),
                "fcf_usd": fcf,
                "fcf_margin_pct": margin_pct(fcf, revenue),
            }
        )
    return rows


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
    return result


def ma_activity(conn: sqlite3.Connection, as_of: date) -> list[dict]:
    """Announced acquisitions per buyer, last 12 months and last 5 years. None = no data yet."""
    total = conn.execute("SELECT COUNT(*) AS n FROM deal").fetchone()["n"]
    result = []
    for buyer in DEAL_BUYERS:
        if total == 0:
            result.append({"company": buyer, "last_12m": None, "last_5y": None})
            continue
        one_year = date.fromordinal(as_of.toordinal() - 365).isoformat()
        five_years = date.fromordinal(as_of.toordinal() - 365 * 5).isoformat()
        row = conn.execute(
            "SELECT SUM(CASE WHEN announced_date >= ? THEN 1 ELSE 0 END) AS last_12m, "
            "COUNT(*) AS last_5y FROM deal WHERE acquirer = ? AND status = 'announced' "
            "AND announced_date >= ?",
            (one_year, buyer, five_years),
        ).fetchone()
        result.append(
            {
                "company": buyer,
                "last_12m": int(row["last_12m"] or 0),
                "last_5y": int(row["last_5y"]),
            }
        )
    return result
