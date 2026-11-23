"""Summary of one listed peer's share price history (screen 1). No network calls.

Decisions (CLAUDE.md, CD-13): prices are USD. The loader in src/ingest/prices.py fetches them.
"""

from __future__ import annotations

import pandas as pd


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
