"""Streamlit app: Overview screen (MVP screen 1).

Run from the repo root:

    uv run streamlit run src/app/streamlit_app.py

The page reads the app database (data/app.db), which the refresh job populates. Missing values
show as "n/d" (not disclosed or not yet loaded). The page never writes to the database.
"""

from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

import streamlit as st

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.metrics import overview  # noqa: E402

# Database path: APP_DB_PATH if set (for viewing a separate refresh), else the repo database.
DB_PATH = Path(os.environ.get("APP_DB_PATH", REPO_ROOT / "data" / "app.db"))


def _fmt(value: float | None, pattern: str) -> str:
    return "n/d" if value is None else pattern.format(value)


def render(conn) -> None:
    st.subheader("Share prices (USD)")
    prices = overview.share_prices(conn)
    cols = st.columns(len(prices))
    for col, p in zip(cols, prices, strict=True):
        col.metric(
            label=f"{p['company']} ({p['ticker']})",
            value=_fmt(p["last_close_usd"], "${:,.2f}"),
            delta=_fmt(p["change_12m_pct"], "{:+.1f}% 12m"),
        )
        position = None if p["position_in_range"] is None else p["position_in_range"] * 100
        col.caption(f"As of {p['as_of'] or 'n/d'} · 52w position {_fmt(position, '{:.0f}%')}")

    st.subheader("Peer financials (latest fiscal year, USD)")
    st.dataframe(
        [
            {
                "Company": r["company"],
                "FY": r["fiscal_year"] or "n/d",
                "Revenue ($m)": _fmt(r["revenue_usd"] and r["revenue_usd"] / 1e6, "{:,.0f}"),
                "Growth": _fmt(r["growth_pct"], "{:+.1f}%"),
                "Gross margin": _fmt(r["gross_margin_pct"], "{:.1f}%"),
                "Net margin": _fmt(r["net_margin_pct"], "{:.1f}%"),
                "FCF ($m)": _fmt(r["fcf_usd"] and r["fcf_usd"] / 1e6, "{:,.0f}"),
                "FCF margin": _fmt(r["fcf_margin_pct"], "{:.1f}%"),
            }
            for r in overview.financial_table(conn)
        ],
        hide_index=True,
        use_container_width=True,
    )
    st.caption(
        "Sartorius and Getinge: annual-report extraction not yet loaded. "
        "Eppendorf: private, to collect. Thermo Fisher gross margin from its 10-K income statement."
    )

    st.subheader("M&A activity (announced deals)")
    ma = overview.ma_activity(conn, date.today())
    st.dataframe(
        [
            {
                "Buyer": r["company"],
                "Last 12 months": _fmt(r["last_12m"], "{:d}"),
                "Last 5 years": _fmt(r["last_5y"], "{:d}"),
            }
            for r in ma
        ],
        hide_index=True,
        use_container_width=True,
    )
    st.caption("Counts build up over time from news and GDELT; earlier years may be incomplete.")

    st.subheader("Competitor news (latest)")
    for item in overview.latest_news(conn):
        if item.get("headline") is None:
            st.write(f"**{item['company']}**: no headlines loaded yet")
            continue
        st.markdown(
            f"**{item['company']}** · {item['tag']} · {item['date']}  \n"
            f"[{item['headline']}]({item['url']})"
            + (f" · {item['publisher']}" if item.get("publisher") else "")
        )


def main() -> None:
    st.set_page_config(page_title="Danaher / Cytiva Competitive Monitor", layout="wide")
    st.title("Danaher / Cytiva Competitive Monitor")
    st.caption("Outside-in · public data only · Overview (screen 1 of 6)")
    if not DB_PATH.exists():
        st.info(
            "No data yet. Run the refresh first: "
            "uv run python -m src.ingest.refresh --trigger manual"
        )
        return
    conn = overview.connect_readonly(DB_PATH)
    try:
        render(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
