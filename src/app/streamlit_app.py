"""Streamlit app: Overview screen (MVP screen 1), laid out to fit one screen without scrolling.

Run from the repo root:

    uv run streamlit run src/app/streamlit_app.py

The page reads the app database (data/app.db), or the file in APP_DB_PATH if set. Missing
values show as "n/d". The page never writes to the database. Each section shows its evidence
label and source in one short line.
"""

from __future__ import annotations

import os
import sqlite3
import sys
from datetime import date
from pathlib import Path

import streamlit as st

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.app.design import CSS as DESIGN_CSS  # noqa: E402
from src.app.design import (  # noqa: E402
    badge_html,
    html_table,
    placeholder,
    record_label,
    remember_source_types,
    row_badge,
    row_badge_typed,
    screen_header,
    stored_label_badge,
    tile_box,
    unconfirmed_toggle,
    visible,
)
from src.app.shells import (  # noqa: E402
    china_screen,
    clusters_screen,
    coverage_screen,
    demand_screen,
    technology_screen,
)
from src.app.ui.evidence import (  # noqa: E402
    attention_items,
    deal_items,
    evidence_button,
    financial_items,
    implication_items,
    layoff_items,
    news_items,
    price_items,
    ranking_items,
)
from src.domain.confidence import FACT as FACT_LABEL  # noqa: E402
from src.domain.confidence import HYPOTHESIS as HYPOTHESIS_LABEL  # noqa: E402
from src.domain.confidence import SIGNAL as SIGNAL_LABEL  # noqa: E402
from src.domain.tabs import (  # noqa: E402
    OVERVIEW_MA_TAB,
    README_PRICES,
    README_RANKINGS,
    README_SARTORIUS,
)
from src.metrics import coverage as coverage_metrics  # noqa: E402
from src.metrics import overview  # noqa: E402
from src.metrics.source_types import source_types  # noqa: E402

# Database path: APP_DB_PATH if set (for viewing a separate refresh), else the repo database.
DB_PATH = Path(os.environ.get("APP_DB_PATH", REPO_ROOT / "data" / "app.db"))

CSS = DESIGN_CSS


def _fmt(value: float | None, pattern: str) -> str:
    return "n/d" if value is None else pattern.format(value)


_table = html_table  # the shared table, also used on the other screens


def _share_prices(conn) -> None:
    prices = overview.share_prices(conn)
    cols = st.columns(len(prices))
    for col, p in zip(cols, prices, strict=True):
        if p["last_close_usd"] is None:
            col.metric(label=f"{p['company']} ({p['ticker']})", value="awaiting feed")
            continue
        col.metric(
            label=f"{p['company']} ({p['ticker']})",
            value=_fmt(p["last_close_usd"], "${:,.2f}"),
            delta=_fmt(p["change_12m_pct"], "{:+.1f}% 12m"),
        )
    awaiting = any(p["last_close_usd"] is None for p in prices)
    evidence_button("prices", "Share prices (last close, USD)", price_items(prices))
    st.markdown(
        "<p class='note'>"
        + (overview.readme_note(conn, README_PRICES) or _NOT_IN_SHEET.format(README_PRICES))
        + (" Awaiting feed: no price stored yet." if awaiting else "")
        + "</p>",
        unsafe_allow_html=True,
    )


def _financials(conn) -> None:
    rows = overview.peer_financials(conn)
    if not rows:
        placeholder("Not loaded yet: run the refresh. To collect.")
        return
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
        ("Basis", "evidence_label", None),
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
            elif key == "evidence_label":
                text = row_badge(r["confidence"], r["source_url"])
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
            "",
        ]
    )
    st.markdown(_table([c[0] for c in columns], html_rows, classes), unsafe_allow_html=True)
    evidence_button("financials", "Peer financials (latest FY, USD)", financial_items(rows))
    st.markdown(
        "<p class='note'>Basis per row, from the sheet: Fact = high confidence and a primary "
        "source (company release or filing); Signal = medium confidence or a secondary source. "
        + (overview.readme_note(conn, README_SARTORIUS) or _NOT_IN_SHEET.format(README_SARTORIUS))
        + " Growth as reported, in reporting currency. Green best, red weakest.</p>",
        unsafe_allow_html=True,
    )


def _rankings(conn) -> None:
    rows = overview.ranking_table(conn, "Forbes Global 2000")
    html_rows = [[r["company"], r["2026"] or "To collect", r["2025"] or "To collect"] for r in rows]
    st.markdown(_table(["Company", "2026", "2025"], html_rows), unsafe_allow_html=True)
    evidence_button("rankings", "Forbes Global 2000 rank", ranking_items(rows))
    st.markdown(
        "<p class='note'>"
        + (overview.readme_note(conn, README_RANKINGS) or _NOT_IN_SHEET.format(README_RANKINGS))
        + "</p>",
        unsafe_allow_html=True,
    )


def _ma_cell(value) -> str:
    """A count from the sheet's deals, or To collect where the sheet has no figure yet."""
    return "To collect" if value is None else f"{value}"


def _deals(conn) -> None:
    today = date.today()
    ma = overview.ma_activity(conn, today)
    headers = [
        "Buyer",
        "M&A 12m",
        "M&A 5y",
        "Lic 12m",
        "Lic 5y",
        "Collab 12m",
        "Collab 5y",
        "Basis",
    ]
    keys = [
        "M&A 12m",
        "M&A 5y",
        "Licensing 12m",
        "Licensing 5y",
        "Collaboration 12m",
        "Collaboration 5y",
    ]
    html_rows = [
        [r["company"]]
        + [_ma_cell(r[k]) for k in keys]
        + [badge_html(r["Basis"]) if r["Basis"] else "&ndash;"]
        for r in ma
    ]
    st.markdown(_table(headers, html_rows), unsafe_allow_html=True)
    try:
        notes = conn.execute(
            "SELECT text, source_url FROM screen_notes WHERE tab = ? ORDER BY rowid",
            (OVERVIEW_MA_TAB,),
        ).fetchall()
    except sqlite3.OperationalError:  # database refreshed before the notes table existed
        notes = []
    for n in notes:
        st.markdown(
            f"<p class='note'>{n['text']} <a href='{n['source_url']}'>source</a></p>",
            unsafe_allow_html=True,
        )
    signals = overview.feed_deal_signals(conn, today)
    for _ in overview.sheet_deals(conn):
        record_label(FACT_LABEL)  # the counts above are the sheet's Fact deals
    for sig in signals["shown"]:
        row_badge(None, sig["source_url"])  # feed items: SIGNAL by the rule
    evidence_button(
        "deals",
        "Deal activity (announced)",
        deal_items(overview.sheet_deals(conn), signals["shown"]),
    )
    st.markdown(
        f"<div class='sec'>{'Unverified deal signals (feed)'} {badge_html(SIGNAL_LABEL)}</div>",
        unsafe_allow_html=True,
    )
    if not signals["shown"]:
        st.markdown(
            "<p class='nw'><span class='muted'>None in the last 12 months.</span></p>",
            unsafe_allow_html=True,
        )
    for sig in signals["shown"]:
        st.markdown(
            f"<p class='nw'><b>{sig['acquirer']}</b> <span class='muted'>· "
            f"{sig['announced_date']}</span><br><a href='{sig['source_url']}'>"
            f"{sig['headline']}</a></p>",
            unsafe_allow_html=True,
        )
    if signals["more"]:
        st.markdown(
            f"<p class='note'>{signals['more']} more in the feed; not counted.</p>",
            unsafe_allow_html=True,
        )
    st.markdown(
        "<p class='note'>M&amp;A in the last 12 months: the sheet's deals, each badged from its "
        "confidence and the type of its first source. Basis is the weakest badge of a company's "
        "counted deals. 5-year, licensing and collaboration counts: to collect. Feed items are "
        "unverified and not counted.</p>",
        unsafe_allow_html=True,
    )


def _news(conn) -> None:
    for item in overview.news_for_screen(conn):
        if item.get("headline") is None:
            st.markdown(
                f"<p class='nw'><b>{item['company']}</b> "
                "<span class='muted'>no headlines yet</span></p>",
                unsafe_allow_html=True,
            )
            continue
        seed = " <span class='muted'>(seed)</span>" if item.get("seed") else ""
        st.markdown(
            f"<p class='nw'><b>{item['company']}</b> "
            f"{row_badge(item.get('confidence'), item['url'])}{seed} "
            f"<span class='muted'>· {item['tag']} · {item['date']}</span><br>"
            f"<a href='{item['url']}'>{item['headline']}</a></p>",
            unsafe_allow_html=True,
        )
    evidence_button("news", "Competitor news (latest)", news_items(overview.news_for_screen(conn)))
    st.markdown(
        "<p class='note'>Signal · company newsrooms and news search · headlines and links only. "
        "(seed) = the sheet's seed item, where the news feed has no item for the company.</p>",
        unsafe_allow_html=True,
    )


def _layoffs(conn, show_l: bool = False) -> None:
    marks = {
        "Yes": "<span class='good'>&#10003;</span>",
        "No": "<span class='weak'>&#10007;</span>",
        "Unknown": "<span class='tc'>?</span>",
    }
    html_rows = []
    for row in overview.layoff_marks(conn):
        cells = [row["company"]]
        for year in (2026, 2025, 2024):
            cell = row["years"].get(year)
            if cell is not None and not visible(cell["confidence"], show_l):
                cell = None  # an L cell is hidden unless the screen toggle is on
            if cell is None:
                cells.append("<span class='tc'>?</span>")
                continue
            mark = marks.get(cell["mark"], "<span class='tc'>?</span>")
            cells.append(f"<a href='{cell['url']}' title='{cell['note']}'>{mark}</a>")
        html_rows.append(cells)
    st.markdown(_table(["Company", "2026", "2025", "2024"], html_rows), unsafe_allow_html=True)
    evidence_button(
        "layoffs",
        "Layoffs announced (2024–2026)",
        layoff_items(overview.layoff_marks(conn), show_l),
    )
    st.markdown(
        "<p class='note'>Signal · ✓ announced cuts or severance; ✗ none found in the sources "
        "searched (not proof of none); ? to collect. Hover a mark for its note; click for the "
        "source.</p>",
        unsafe_allow_html=True,
    )


def _attention(conn) -> None:
    items = overview.attention_items(conn)
    if not items:
        placeholder("Not loaded yet: run the refresh. To collect.")
        return
    for a in items:
        st.markdown(
            f"<p class='nw'><span class='tc'><b>{a['action']}</b></span> "
            f"{row_badge_typed(a.get('confidence'), a.get('source_type_text'), None)} "
            f"<b>{a['issue']}</b><br>{a['key_fact']} "
            f"<span class='muted'>· review by {a['review_by']}</span></p>",
            unsafe_allow_html=True,
        )
    evidence_button("attention", "Attention", attention_items(items))
    st.markdown(
        "<p class='note'>Five items at most. ACT = a decision or check is due; MONITOR = keep "
        "watching. Badges follow the sheet's evidence label.</p>",
        unsafe_allow_html=True,
    )


def _implications(conn, show_l: bool = False) -> None:
    items = [i for i in overview.implications(conn) if visible(i.get("confidence"), show_l)]
    if not items:
        placeholder("Not loaded yet: run the refresh. To collect.")
        return
    for r in items:
        st.markdown(
            f"<p class='hyp'>{stored_label_badge(HYPOTHESIS_LABEL)} {r['hypothesis']} "
            f"<span class='muted'>({r['area']}; confidence {r['confidence']})</span></p>",
            unsafe_allow_html=True,
        )
    evidence_button("implications", "Implications for Finance & IT", implication_items(items))
    st.markdown(
        "<p class='note'>Hypotheses to test internally, not findings.</p>", unsafe_allow_html=True
    )


def render(conn) -> None:
    show_l = unconfirmed_toggle()
    # Layout follows the MVP mockup: a navy header; share prices across the top; financials,
    # rankings and deal activity on the left; competitor news and implications on the right.
    # Each block sits in its own bordered box.
    screen_header(1, "Overview")
    with st.container(border=True):
        _share_prices(conn)
    left, right = st.columns([2, 1], gap="small")
    with left:
        with tile_box("Peer financials (latest FY, USD)"):
            _financials(conn)
        rank_col, deal_col, layoff_col = st.columns([1, 2, 1], gap="small")
        with rank_col, tile_box("Forbes Global 2000 rank"):
            _rankings(conn)
        with deal_col, tile_box("Deal activity (announced)"):
            _deals(conn)
        with layoff_col, tile_box("Layoffs announced (2024–2026)"):
            _layoffs(conn, show_l)
    with right:
        with tile_box("Attention"):
            _attention(conn)
        with tile_box("Competitor news (latest)"):
            _news(conn)
        with tile_box("Implications for Finance & IT"):
            _implications(conn, show_l)


def _remember_sources() -> None:
    """Each page starts by loading the source type of every sheet URL, for the badge rule."""
    types: dict[str, str] = {}
    if DB_PATH.exists():
        conn = overview.connect_readonly(DB_PATH)
        try:
            types = source_types(conn)
        finally:
            conn.close()
    remember_source_types(types)


_NOT_IN_SHEET = "To collect: add the \u201c{}\u201d row to the overview sheet README."


def overview_screen() -> None:
    _remember_sources()
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
    _remember_sources()
    cells = None
    sales = None
    implications = None
    if DB_PATH.exists():
        conn = overview.connect_readonly(DB_PATH)
        try:
            cells = coverage_metrics.grid_cells(conn)
            sales = coverage_metrics.biotech_sales(conn)
            implications = coverage_metrics.implications(conn)
        finally:
            conn.close()
    steps = coverage_metrics.step_cells(cells) if cells is not None else None
    coverage_screen(cells, steps, sales, implications)


def clusters_page() -> None:
    _remember_sources()
    from src.metrics import clusters as cm

    data = None
    if DB_PATH.exists():
        conn = overview.connect_readonly(DB_PATH)
        try:
            data = cm.load(conn)
        finally:
            conn.close()
    clusters_screen(data)


def demand_page() -> None:
    _remember_sources()
    from src.metrics import demand as dm

    data = None
    if DB_PATH.exists():
        conn = overview.connect_readonly(DB_PATH)
        try:
            data = dm.load(conn)
        finally:
            conn.close()
    demand_screen(data)


def technology_page() -> None:
    _remember_sources()
    from src.metrics import technology as tm

    data = None
    if DB_PATH.exists():
        conn = overview.connect_readonly(DB_PATH)
        try:
            data = tm.load(conn)
        finally:
            conn.close()
    technology_screen(data, date.today())


def china_page() -> None:
    _remember_sources()
    from src.metrics import china as cm

    data = None
    if DB_PATH.exists():
        conn = overview.connect_readonly(DB_PATH)
        try:
            data = cm.load(conn)
        finally:
            conn.close()
    china_screen(data)


def main() -> None:
    st.set_page_config(page_title="Danaher / Cytiva Competitive Monitor", layout="wide")
    pages = [
        st.Page(overview_screen, title="1 · Overview", url_path="overview", default=True),
        st.Page(coverage_page, title="2 · Competitor coverage", url_path="coverage"),
        st.Page(clusters_page, title="3 · Customer clusters", url_path="clusters"),
        st.Page(demand_page, title="4 · Demand drivers", url_path="demand"),
        st.Page(technology_page, title="5 · Technology", url_path="technology"),
        st.Page(china_page, title="6 · China", url_path="china"),
    ]
    st.markdown(DESIGN_CSS, unsafe_allow_html=True)  # shared style for every screen
    navigation = st.navigation(pages, position="top")
    navigation.run()


if __name__ == "__main__":
    main()
