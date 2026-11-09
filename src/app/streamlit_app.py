"""Streamlit app: Overview screen (MVP screen 1), laid out to fit one screen without scrolling.

Run from the repo root:

    uv run streamlit run src/app/streamlit_app.py

The page reads the app database (data/app.db), or the file in APP_DB_PATH if set. Missing
values show as "n/d". The page never writes to the database. Each section shows its evidence
label and source in one short line.
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

CSS = """
<style>
header[data-testid="stHeader"] {display: none;}
footer {visibility: hidden;}
.block-container {
  padding-top: 0.5rem !important; padding-bottom: 0 !important; max-width: 100% !important;
}
div[data-testid="stVerticalBlock"] {gap: 0.35rem !important;}
h1 {font-size: 1.2rem !important; margin: 0 !important; padding: 0 !important;}
h2, h3 {font-size: 0.85rem !important; margin: 0.2rem 0 0.1rem 0 !important; padding: 0 !important;}
div[data-testid="stMetricValue"] {font-size: 1.05rem !important;}
div[data-testid="stMetricLabel"] p {font-size: 0.66rem !important;}
div[data-testid="stMetricDelta"] {font-size: 0.66rem !important;}
div[data-testid="stMetric"] {padding: 0 !important;}
.note {font-size: 0.6rem; color: #6B7A88; margin: 0; line-height: 1.15;}
.sub {font-size: 0.65rem; color: #6B7A88; margin: 0; line-height: 1.15;}
table.c {border-collapse: collapse; width: 100%; font-size: 0.7rem; line-height: 1.1;}
table.c th {
  text-align: left; color: #6B7A88; font-weight: 600;
  border-bottom: 1px solid #E2E7EC; padding: 0 4px;
}
table.c td {padding: 0 4px; border-bottom: 1px solid #EEF1F4; white-space: nowrap;}
table.c td.n, table.c th.n {text-align: right;}
.good {background: #E6F4EC; color: #1E6B45; font-weight: 600;}
.weak {background: #FBEAEA; color: #B23A2C; font-weight: 600;}
.muted {color: #6B7A88;}
.nw {font-size: 0.66rem; line-height: 1.15; margin: 0 0 0.2rem 0;}
.nw a {color: #1B5E9E; text-decoration: none;}
.hyp {font-size: 0.68rem; line-height: 1.2; margin: 0;}
</style>
"""


def _fmt(value: float | None, pattern: str) -> str:
    return "n/d" if value is None else pattern.format(value)


def _table(headers: list[str], rows: list[list[str]], classes: dict | None = None) -> str:
    """Compact HTML table. `classes` maps (row, col) to a CSS class for highlighting."""
    classes = classes or {}
    head = "".join(f'<th class="{"n" if i else ""}">{h}</th>' for i, h in enumerate(headers))
    body = ""
    for r, row in enumerate(rows):
        cells = ""
        for c, value in enumerate(row):
            css = " ".join(filter(None, ["n" if c else "", classes.get((r, c), "")]))
            cells += f'<td class="{css}">{value}</td>'
        body += f"<tr>{cells}</tr>"
    return f'<table class="c"><tr>{head}</tr>{body}</table>'


def _share_prices(conn) -> None:
    prices = overview.share_prices(conn)
    cols = st.columns(len(prices))
    for col, p in zip(cols, prices, strict=True):
        col.metric(
            label=f"{p['company']} ({p['ticker']})",
            value=_fmt(p["last_close_usd"], "${:,.2f}"),
            delta=_fmt(p["change_12m_pct"], "{:+.1f}% 12m"),
        )
    st.markdown(
        "<p class='note'>Fact · Yahoo Finance via yfinance · USD at each day's rate · "
        "as of the last refresh (daily, 10:00 Warsaw). Merck KGaA is the group price.</p>",
        unsafe_allow_html=True,
    )


def _financials(conn) -> None:
    st.subheader("Peer financials (latest FY, USD)")
    rows = overview.financial_table(conn)
    best = {key: overview.best_worst(rows, key) for key in overview.PEER_METRICS}
    columns = [
        ("Company", "company", None),
        ("FY", "fiscal_year", None),
        ("Revenue $m", "revenue_usd", None),
        ("Growth", "growth_pct", "growth_pct"),
        ("Gross", "gross_margin_pct", "gross_margin_pct"),
        ("Net", "net_margin_pct", "net_margin_pct"),
        ("FCF $m", "fcf_usd", None),
        ("FCF %", "fcf_margin_pct", "fcf_margin_pct"),
    ]
    html_rows, classes = [], {}
    for r_index, r in enumerate(rows):
        cells = []
        for c_index, (_, key, highlight) in enumerate(columns):
            value = r[key]
            if key == "revenue_usd" or key == "fcf_usd":
                text = _fmt(value and value / 1e6, "{:,.0f}")
            elif key == "fiscal_year":
                text = str(value or "n/d")
            elif key == "company":
                text = r["company"]
            else:
                pattern = "{:+.1f}%" if key == "growth_pct" else "{:.1f}%"
                text = _fmt(value, pattern)
            cells.append(text)
            if highlight:
                label = best[highlight].get(r["company"])
                if label:
                    classes[(r_index, c_index)] = "good" if label == "best" else "weak"
        html_rows.append(cells)
    median = {key: overview.peer_median(rows, key) for key in overview.PEER_METRICS}
    html_rows.append(
        [
            "Peer median",
            "",
            "",
            _fmt(median["growth_pct"], "{:+.1f}%"),
            _fmt(median["gross_margin_pct"], "{:.1f}%"),
            _fmt(median["net_margin_pct"], "{:.1f}%"),
            "",
            _fmt(median["fcf_margin_pct"], "{:.1f}%"),
        ]
    )
    st.markdown(_table([c[0] for c in columns], html_rows, classes), unsafe_allow_html=True)
    st.markdown(
        "<p class='note'>Fact · SEC EDGAR (DHR, TMO, RGEN, AVTR); Sartorius annual report; "
        "Merck Life Science segment (gross margin only). Growth in reporting currency. "
        "Green best, red weakest. Ratings to collect: S&amp;P, EcoVadis, Fortune 500.</p>",
        unsafe_allow_html=True,
    )


def _rankings(conn) -> None:
    st.subheader("Forbes Global 2000 rank (curated)")
    rows = overview.ranking_table(conn, "Forbes Global 2000")
    html_rows = [[r["company"], r["2026"] or "n/d", r["2025"] or "n/d"] for r in rows]
    st.markdown(_table(["Company", "2026", "2025"], html_rows), unsafe_allow_html=True)
    st.markdown(
        "<p class='note'>Curated from forbes.com/lists/global2000, entered 8 Nov 2026. "
        "n/d = not ranked.</p>",
        unsafe_allow_html=True,
    )


def _deals(conn) -> None:
    st.subheader("Deal activity (announced)")
    ma = overview.ma_activity(conn, date.today())
    headers = ["Buyer", "M&A 12m", "M&A 5y", "Lic 12m", "Lic 5y", "Collab 12m", "Collab 5y"]
    keys = [
        "M&A 12m",
        "M&A 5y",
        "Licensing 12m",
        "Licensing 5y",
        "Collaboration 12m",
        "Collaboration 5y",
    ]
    html_rows = [[r["company"]] + [_fmt(r[k], "{:d}") for k in keys] for r in ma]
    st.markdown(_table(headers, html_rows), unsafe_allow_html=True)
    st.markdown(
        "<p class='note'>Signal · Google News and GDELT headlines where the company is the "
        "subject. Lower bounds; history builds with each refresh.</p>",
        unsafe_allow_html=True,
    )


def _news(conn) -> None:
    st.subheader("Competitor news (latest)")
    for item in overview.latest_news(conn):
        if item.get("headline") is None:
            st.markdown(
                f"<p class='nw'><b>{item['company']}</b> "
                "<span class='muted'>no headlines yet</span></p>",
                unsafe_allow_html=True,
            )
            continue
        headline = item["headline"]
        if len(headline) > 95:
            headline = headline[:92] + "…"
        st.markdown(
            f"<p class='nw'><b>{item['company']}</b> <span class='muted'>· {item['tag']} · "
            f"{item['date']}</span><br><a href='{item['url']}'>{headline}</a></p>",
            unsafe_allow_html=True,
        )
    st.markdown(
        "<p class='note'>Signal · company newsrooms and news search · "
        "headlines and links only.</p>",
        unsafe_allow_html=True,
    )


def _implications() -> None:
    st.subheader("Implications for Finance & IT")
    for text in overview.IMPLICATIONS:
        st.markdown(f"<p class='hyp'><b>Hypothesis:</b> {text}</p>", unsafe_allow_html=True)
    st.markdown(
        "<p class='note'>Hypotheses to test internally, not findings.</p>", unsafe_allow_html=True
    )


def render(conn) -> None:
    # Layout follows the Miro mockup: share prices across the top; financials, rankings and
    # deal activity on the left; competitor news and implications on the right.
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(
        "<h1>Danaher / Cytiva Competitive Monitor</h1>"
        "<p class='note'>Outside-in · public data only · Overview (1 of 6) · "
        "Fact = filings and prices · Signal = news and estimates · Hypothesis = to test</p>",
        unsafe_allow_html=True,
    )
    _share_prices(conn)
    left, right = st.columns([2, 1], gap="small")
    with left:
        _financials(conn)
        _rankings(conn)
        _deals(conn)
    with right:
        _news(conn)
        _implications()


def main() -> None:
    st.set_page_config(page_title="Danaher / Cytiva Competitive Monitor", layout="wide")
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
