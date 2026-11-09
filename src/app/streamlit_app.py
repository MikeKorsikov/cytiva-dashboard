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
from src.app.design import header  # noqa: E402
from src.app.shells import (  # noqa: E402
    china_screen,
    clusters_screen,
    coverage_screen,
    demand_screen,
    technology_screen,
)
from src.metrics import coverage as coverage_metrics  # noqa: E402
from src.metrics import overview  # noqa: E402
from src.metrics import technology as tech_metrics  # noqa: E402

# Database path: APP_DB_PATH if set (for viewing a separate refresh), else the repo database.
DB_PATH = Path(os.environ.get("APP_DB_PATH", REPO_ROOT / "data" / "app.db"))

CSS = DESIGN_CSS


def _fmt(value: float | None, pattern: str) -> str:
    return "n/d" if value is None else pattern.format(value)


def _table(
    headers: list[str],
    rows: list[list[str]],
    classes: dict | None = None,
    auto_width: bool = False,
) -> str:
    """Compact HTML table. `classes` maps (row, col) to a CSS class for highlighting.
    `auto_width` sizes the table to its content instead of the full column."""
    classes = classes or {}
    head = "".join(f'<th class="{"n" if i else ""}">{h}</th>' for i, h in enumerate(headers))
    body = ""
    for r, row in enumerate(rows):
        cells = ""
        for c, value in enumerate(row):
            css = " ".join(filter(None, ["n" if c else "", classes.get((r, c), "")]))
            cells += f'<td class="{css}">{value}</td>'
        body += f"<tr>{cells}</tr>"
    table_class = "c auto" if auto_width else "c"
    return f'<table class="{table_class}"><tr>{head}</tr>{body}</table>'


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
        "Merck KGaA group (IFRS, EUR). Growth in reporting currency. "
        "Green best, red weakest.</p>",
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
        "<p class='note'>Entered by hand from the Forbes Global 2000 figures of 8 Nov 2026; "
        "not re-checked online (the public list page does not show company ranks). "
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
        "<p class='note'>Fact · deals reported by the companies, each with its release link. "
        "Signal · Google News and GDELT headlines for the rest, where the company is the subject. "
        "Each deal is counted once. Lower bounds; history builds with each refresh.</p>",
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
        headline = item["headline"]  # shown in full; it wraps onto the second line
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
    # Layout follows the MVP mockup: a navy header; share prices across the top; financials,
    # rankings and deal activity on the left; competitor news and implications on the right.
    # Each block sits in its own bordered box.
    header(
        "Danaher / Cytiva Competitive Monitor",
        "Outside-in · public data only · Overview (screen 1 of 6) · "
        "Fact = filings and prices · Signal = news and estimates · Hypothesis = to test",
    )
    with st.container(border=True):
        _share_prices(conn)
    left, right = st.columns([2, 1], gap="small")
    with left:
        with st.container(border=True):
            _financials(conn)
        rank_col, deal_col = st.columns([1, 2], gap="small")
        with rank_col, st.container(border=True):
            _rankings(conn)
        with deal_col, st.container(border=True):
            _deals(conn)
    with right:
        with st.container(border=True):
            _news(conn)
        with st.container(border=True):
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


def coverage_page() -> None:
    cells = None
    if DB_PATH.exists():
        conn = overview.connect_readonly(DB_PATH)
        try:
            cells = coverage_metrics.footprint_cells(conn)
        finally:
            conn.close()
    coverage_screen(cells)


def technology_page() -> None:
    register, incidents, checked_on = None, None, None
    if DB_PATH.exists():
        conn = overview.connect_readonly(DB_PATH)
        try:
            register = tech_metrics.estate_register(conn)
            incidents = tech_metrics.recent_incidents(conn, date.today())
            checked_on = tech_metrics.last_successful_check(conn)
        finally:
            conn.close()
    technology_screen(register, incidents, checked_on)


def main() -> None:
    st.set_page_config(page_title="Danaher / Cytiva Competitive Monitor", layout="wide")
    pages = [
        st.Page(overview_screen, title="1 · Overview", url_path="overview", default=True),
        st.Page(coverage_page, title="2 · Competitor coverage", url_path="coverage"),
        st.Page(clusters_screen, title="3 · Customer clusters", url_path="clusters"),
        st.Page(demand_screen, title="4 · Demand drivers", url_path="demand"),
        st.Page(technology_page, title="5 · Technology", url_path="technology"),
        st.Page(china_screen, title="6 · China", url_path="china"),
    ]
    st.markdown(DESIGN_CSS, unsafe_allow_html=True)  # shared style for every screen
    navigation = st.navigation(pages, position="top")
    navigation.run()


if __name__ == "__main__":
    main()
