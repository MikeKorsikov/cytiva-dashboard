"""Share prices for listed peers, from Yahoo Finance via yfinance, converted to USD.

Decisions (CLAUDE.md, CD-13): yfinance is unofficial and can break, so all calls go through
this module. Raw history is cached per ticker per day. Every value is stored in USD with
the local close, the currency and the FX rate date. Eppendorf (private) and the Merck KGaA
group (excluded) have no share price and are not listed here.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd
import yfinance as yf

from src.ingest import store
from src.ingest.checks import check_range

REPO_ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = REPO_ROOT / "data" / "cache" / "prices"
PERIOD = "1y"
SOURCE_URL = "https://finance.yahoo.com/quote/{ticker}/history"


class PriceError(RuntimeError):
    """Raised when share prices cannot be loaded. The message says what to check."""


@dataclass(frozen=True)
class ListedPeer:
    company: str
    ticker: str  # Yahoo Finance symbol
    currency: str  # ISO code of the trading currency


LISTED_PEERS: tuple[ListedPeer, ...] = (
    ListedPeer("Danaher", "DHR", "USD"),
    ListedPeer("Thermo Fisher", "TMO", "USD"),
    ListedPeer("Sartorius", "SRT3.DE", "EUR"),
    ListedPeer("Repligen", "RGEN", "USD"),
    ListedPeer("Avantor", "AVTR", "USD"),
    ListedPeer("Getinge", "GETI-B.ST", "SEK"),
)


def fetch_history(ticker: str, period: str = PERIOD, *, use_cache: bool = True) -> pd.DataFrame:
    """Daily history for one ticker. Cached for the current day."""
    cache_file = CACHE_DIR / f"{ticker.replace('=', '_').replace('/', '_')}.csv"
    if use_cache and cache_file.exists():
        modified = date.fromtimestamp(cache_file.stat().st_mtime)
        if modified == date.today():
            return pd.read_csv(cache_file, index_col=0, parse_dates=True)
    try:
        history = yf.Ticker(ticker).history(period=period, auto_adjust=False)
    except Exception as exc:  # yfinance raises a variety of network and parsing errors
        raise PriceError(f"Yahoo Finance request failed for {ticker}: {exc}") from exc
    if history is None or history.empty or "Close" not in history.columns:
        raise PriceError(
            f"Yahoo Finance returned no prices for {ticker}. "
            "Check the ticker symbol, or try again later (the API is unofficial)."
        )
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    history.to_csv(cache_file)
    return history


def fx_to_usd(currency: str, period: str = PERIOD) -> pd.Series:
    """USD value of one unit of `currency`, by day. USD returns a series of 1.0."""
    if currency == "USD":
        return pd.Series(dtype=float)
    fx = fetch_history(f"{currency}USD=X", period)
    series = fx["Close"].copy()
    series.index = pd.to_datetime(series.index).tz_localize(None).normalize()
    return series


def to_usd(local_close: pd.Series, fx_rates: pd.Series | None) -> pd.Series:
    """Convert a local price series to USD using the FX rate on the same day.

    Days with no FX rate use the most recent earlier rate (forward fill).
    """
    if fx_rates is None or fx_rates.empty:
        return local_close.copy()
    rates = fx_rates.reindex(local_close.index, method="ffill")
    return local_close * rates


def summarise(usd_close: pd.Series) -> dict[str, float | None]:
    """Last close, 12-month change, 52-week high and low, and position in that range."""
    series = usd_close.dropna()
    if series.empty:
        return {
            "last_close_usd": None,
            "change_12m_pct": None,
            "high_52w": None,
            "low_52w": None,
            "position_in_range": None,
        }
    last = float(series.iloc[-1])
    first = float(series.iloc[0])
    high = float(series.max())
    low = float(series.min())
    position = (last - low) / (high - low) if high > low else None
    return {
        "last_close_usd": last,
        "change_12m_pct": (last / first - 1) * 100 if first else None,
        "high_52w": high,
        "low_52w": low,
        "position_in_range": position,
    }


def load_share_prices(conn: sqlite3.Connection, run_id: int) -> int:
    """Load one year of daily USD prices for each listed peer. Returns rows written."""
    written = 0
    for peer in LISTED_PEERS:
        history = fetch_history(peer.ticker)
        local = history["Close"].copy()
        local.index = pd.to_datetime(local.index).tz_localize(None).normalize()
        usd = to_usd(local, fx_to_usd(peer.currency))
        for day, close_usd in usd.dropna().items():
            close_local = float(local.loc[day])
            problems = check_range("close_usd", float(close_usd), 0.0001, 1_000_000.0)
            row = {
                "ticker": peer.ticker,
                "price_date": day.date().isoformat(),
                "close_usd": float(close_usd),
                "close_local": close_local,
                "currency": peer.currency,
                "source_url": SOURCE_URL.format(ticker=peer.ticker),
                "source_type": "API",
                "published_date": day.date().isoformat(),
                "evidence_label": "Fact",
            }
            status = store.upsert(conn, run_id, "share_price_daily", row, extra_problems=problems)
            if status != "rejected":
                written += 1
    return written
