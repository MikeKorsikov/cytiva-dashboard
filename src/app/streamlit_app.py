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

from src.app.design import CSS as DESIGN_CSS  # noqa: E402
from src.app.shells import (  # noqa: E402
    china_screen,
    clusters_screen,
    coverage_screen,
    demand_screen,
    technology_screen,
)
from src.metrics import overview  # noqa: E402

# Database path: APP_DB_PATH if set (for viewing a separate refresh), else the repo database.
DB_PATH = Path(os.environ.get("APP_DB_PATH", REPO_ROOT / "data" / "app.db"))

CSS = DESIGN_CSS


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
    st.markdown(
        f"<div class='sec'>{'Peer financials (latest FY, USD)'}</div>", unsafe_allow_html=True
    )
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
    st.markdown(
        f"<div class='sec'>{'Forbes Global 2000 rank (curated)'}</div>", unsafe_allow_html=True
    )
    rows = overview.ranking_table(conn, "Forbes Global 2000")
    html_rows = [[r["company"], r["2026"] or "n/d", r["2025"] or "n/d"] for r in rows]
    st.markdown(_table(["Company", "2026", "2025"], html_rows), unsafe_allow_html=True)
    st.markdown(
        "<p class='note'>Curated from forbes.com/lists/global2000, entered 8 Nov 2026. "
        "n/d = not ranked.</p>",
        unsafe_allow_html=True,
    )


def _deals(conn) -> None:
    st.markdown(f"<div class='sec'>{'Deal activity (announced)'}</div>", unsafe_allow_html=True)
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
    st.markdown(f"<div class='sec'>{'Competitor news (latest)'}</div>", unsafe_allow_html=True)
    for item in overview.latest_news(conn):
        if item.get("headline") is None:
            st.markdown(
                f"<p class='nw'><b>{item['company']}</b> "
                "<span class='muted'>no headlines yet</span></p>",
                unsafe_allow_html=True,
            )
            continue
        headline = item["headline"]
        if len(headline) > 70:
            headline = headline[:67] + "…"
        st.markdown(
            f"<p class='nw'><b>{item['company']}</b> "
            f"<span class='muted'>· {item['tag']} · {item['date']}</span><br>"
            f"<a href='{item['url']}'>{headline}</a></p>",
            unsafe_allow_html=True,
        )
    st.markdown(
        "<p class='note'>Signal · company newsrooms and news search · "
        "headlines and links only.</p>",
        unsafe_allow_html=True,
    )


def _implications() -> None:
    st.markdown(f"<div class='sec'>{'Implications for Finance & IT'}</div>", unsafe_allow_html=True)
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
        "<div class='ttl'>Danaher / Cytiva Competitive Monitor</div>"
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


def overview_screen() -> None:
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


def main() -> None:
    st.set_page_config(page_title="Danaher / Cytiva Competitive Monitor", layout="wide")
    pages = [
        st.Page(overview_screen, title="1 · Overview", url_path="overview", default=True),
        st.Page(coverage_screen, title="2 · Competitor coverage", url_path="coverage"),
        st.Page(clusters_screen, title="3 · Customer clusters", url_path="clusters"),
        st.Page(demand_screen, title="4 · Demand drivers", url_path="demand"),
        st.Page(technology_screen, title="5 · Technology", url_path="technology"),
        st.Page(china_screen, title="6 · China", url_path="china"),
    ]
    navigation = st.navigation(pages, position="top")
    navigation.run()


if __name__ == "__main__":
    main()
