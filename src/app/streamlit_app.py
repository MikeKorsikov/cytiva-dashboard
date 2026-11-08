"""Streamlit app: Overview screen (MVP screen 1).

Run from the repo root:

    uv run streamlit run src/app/streamlit_app.py

The page reads the app database (data/app.db), which the refresh job populates, or the file in
APP_DB_PATH if set. Missing values show as "n/d" (not disclosed or not yet loaded). The page
never writes to the database. Each tile shows its evidence label, source and "as of" date.
"""

from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.metrics import overview  # noqa: E402

# Database path: APP_DB_PATH if set (for viewing a separate refresh), else the repo database.
DB_PATH = Path(os.environ.get("APP_DB_PATH", REPO_ROOT / "data" / "app.db"))

GOOD = "background-color: #E6F4EC; color: #1E6B45; font-weight: 600"
WEAK = "background-color: #FBEAEA; color: #B23A2C; font-weight: 600"
PERCENT_COLUMNS = {
    "Growth": "growth_pct",
    "Gross margin": "gross_margin_pct",
    "Net margin": "net_margin_pct",
    "FCF margin": "fcf_margin_pct",
}


def _fmt(value: float | None, pattern: str) -> str:
    return "n/d" if value is None else pattern.format(value)


def _share_prices(conn) -> None:
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
        col.caption(f"As of {p['as_of'] or 'n/d'} · 52w {_fmt(position, '{:.0f}%')}")
    st.caption(
        "Fact · Source: Yahoo Finance via yfinance (listed peers; Eppendorf is private). "
        "Local prices converted to USD at each day's rate. Daily refresh, 10:00 Warsaw time."
    )


def _financials(conn) -> None:
    st.subheader("Peer financials (latest fiscal year)")
    rows = overview.financial_table(conn)
    median_row = {"company": "Peer median (excl. Danaher)", "fiscal_year": None}
    for key in overview.PEER_METRICS:
        median_row[key] = overview.peer_median(rows, key)
    median_row["revenue_usd"] = overview.peer_median(rows, "revenue_usd")
    median_row["fcf_usd"] = None
    all_rows = rows + [median_row]

    frame = pd.DataFrame(
        [
            {
                "Company": r["company"],
                "FY": r["fiscal_year"] if r["fiscal_year"] else "",
                "Revenue ($m)": None if r["revenue_usd"] is None else r["revenue_usd"] / 1e6,
                "Growth": r["growth_pct"],
                "Gross margin": r["gross_margin_pct"],
                "Net margin": r["net_margin_pct"],
                "FCF ($m)": None if r["fcf_usd"] is None else r["fcf_usd"] / 1e6,
                "FCF margin": r["fcf_margin_pct"],
            }
            for r in all_rows
        ]
    )

    # Best and weakest per metric, among companies only (the median row is not ranked).
    styles = pd.DataFrame("", index=frame.index, columns=frame.columns)
    for column, key in PERCENT_COLUMNS.items():
        for company, label in overview.best_worst(rows, key).items():
            index = frame.index[frame["Company"] == company]
            if len(index):
                styles.loc[index[0], column] = GOOD if label == "best" else WEAK

    formats = {
        "Revenue ($m)": "{:,.0f}",
        "FCF ($m)": "{:,.0f}",
        "Growth": "{:+.1f}%",
        "Gross margin": "{:.1f}%",
        "Net margin": "{:.1f}%",
        "FCF margin": "{:.1f}%",
    }
    styled = (
        frame.style.format(formats, na_rep="n/d")
        .apply(lambda _: styles, axis=None)
        .hide(axis="index")
    )
    st.dataframe(styled, use_container_width=True)
    st.caption(
        "Fact · Sources: SEC EDGAR filings (Danaher, Thermo Fisher, Repligen, Avantor); "
        "Sartorius and Getinge annual reports, converted at each year's average rate. "
        "Thermo Fisher gross margin from its 10-K income statement. Growth is in reporting "
        "currency. Green = best, red = weakest among companies."
    )
    st.caption(
        "Ratings to collect (not yet loaded): S&P credit rating, EcoVadis rating, Fortune 500 "
        "rank. Eppendorf: private, no public financials found."
    )


def _rankings(conn) -> None:
    st.subheader("Rankings (Forbes Global 2000, curated)")
    rows = overview.ranking_table(conn, "Forbes Global 2000")
    st.dataframe(
        pd.DataFrame(
            [
                {"Company": r["company"], "2026": r["2026"] or "n/d", "2025": r["2025"] or "n/d"}
                for r in rows
            ]
        ),
        hide_index=True,
        use_container_width=True,
    )
    st.caption(
        "Curated: entered by hand from forbes.com/lists/global2000, entry date 8 Nov 2026. "
        "n/d = not ranked. Eppendorf is private and not eligible."
    )


def _deals(conn) -> None:
    st.subheader("Deal activity (announced, by category)")
    ma = overview.ma_activity(conn, date.today())
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Buyer": r["company"],
                    **{
                        f"{cat} ({label})": r[f"{cat} {key}"]
                        for cat in ("M&A", "Licensing", "Collaboration")
                        for label, key in (("12 months", "12m"), ("5 years", "5y"))
                    },
                }
                for r in ma
            ]
        ).style.format(na_rep="n/d", precision=0),
        use_container_width=True,
        hide_index=True,
    )
    st.caption(
        "Signal · Sources: Google News and GDELT headlines in which the company is the subject. "
        "Counts are lower bounds; earlier years build up with each refresh."
    )


def _news(conn) -> None:
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
    st.caption("Signal · Sources: company newsrooms and news search. Headlines and links only.")


def _implications() -> None:
    st.subheader("Implications for Finance & IT")
    for text in overview.IMPLICATIONS:
        st.markdown(f"- **Hypothesis:** {text}")
    st.caption("Hypotheses to test internally, not findings.")


def render(conn) -> None:
    _share_prices(conn)
    _financials(conn)
    _rankings(conn)
    _deals(conn)
    _news(conn)
    _implications()


def main() -> None:
    st.set_page_config(page_title="Danaher / Cytiva Competitive Monitor", layout="wide")
    st.title("Danaher / Cytiva Competitive Monitor")
    st.caption(
        "Outside-in · public data only · Overview (screen 1 of 6) · "
        "Fact = filings and prices · Signal = news and estimates · Hypothesis = to test"
    )
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
