"""Screens 2 to 6 of the dashboard, laid out as in the MVP design.

These are shells: layout and sections are in place, and each section is marked with its
evidence label. Content that is not loaded yet shows as "to collect" with the research story
that will fill it. No estimate or mockup value is shown as data.

Each section sits in its own white box, as on the Overview.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import UTC, datetime

import plotly.graph_objects as go
import streamlit as st

from src.app.design import (
    evidence_badge,
    html_table,
    hypothesis,
    kpi_card,
    note,
    placeholder,
    screen_header,
    section,
    source_link,
)
from src.app.market_tile import market_share_tile
from src.ingest.china import FAMILY_NAMES
from src.metrics import china as cm
from src.metrics.coverage import STEP_FAMILIES

STATUS_LEGEND = (
    "Legend: verified present · partial or to confirm · verified absence · not yet researched"
)


def _box(title: str, kind: str, body: Callable[[], None]) -> None:
    """One section in its own bordered box: heading with its evidence badge, then the body."""
    with st.container(border=True):
        section(title, kind)
        body()


def _text(*lines: str) -> Callable[[], None]:
    def draw() -> None:
        for line in lines:
            placeholder(line)

    return draw


def _hyp(*lines: str) -> Callable[[], None]:
    def draw() -> None:
        for line in lines:
            hypothesis(line)

    return draw


COVERAGE_REGIONS = [
    ("North America", "r0", "#0F5A3C", "#E3F4EC"),
    ("Western Europe", "r1", "#1E3F73", "#E5F0FB"),
    ("High-growth markets", "r2", "#3D2E7A", "#EEEAF8"),
    ("Other developed markets", "r3", "#6B4A12", "#FAF0E0"),
]
COVERAGE_COMPANIES = [
    ("Cytiva", "CYT"),
    ("Thermo Fisher", "TMO"),
    ("Sartorius", "SRT"),
    ("Repligen", "RGN"),
    ("Avantor", "AVT"),
    ("Merck KGaA", "MRK"),
]
COVERAGE_FAMILIES = [
    "Media",
    "Single-use",
    "Resins",
    "Filtration",
    "Filling",
    "Genomic",
    "Systems",
    "Analytical",
]
COVERAGE_STEPS = [
    "1. Research tools",
    "2. Cell line and process dev.",
    "3. Upstream processing",
    "4. Downstream processing",
    "5. Formulation and fill-finish",
    "6. QC and release testing",
    "7. Facility and automation",
    "8. Service and support",
]
# Mark classes as in the MVP: green check (made), yellow half (partial or planned), pink cross
# (not made), grey dashed question mark (to collect).
_MARK_CLASS = {"Made": ("M", "&#10003;"), "Partial": ("P", "&#9680;"), "Not made": ("N", "&#215;")}


def _mark(status: str | None, url: str | None) -> str:
    """One boxed mark, linked to its public source. A mark whose only source is a research
    sheet is shown without a link."""
    if status not in _MARK_CLASS:
        return "<i class='mk u'>?</i>"
    cls, sym = _MARK_CLASS[status]
    box = f"<i class='mk {cls}'>{sym}</i>"
    if not url or "docs.google.com/spreadsheets" in url:
        return f"<span title='{status}: no public source linked yet'>{box}</span>"
    return f"<a href='{url}' title='{status}'>{box}</a>"


def _grid(row_label: str, rows: list[str], html_cell, labels: dict | None = None) -> str:
    """A matrix in the MVP layout: region bands with tints, company columns, a divider between
    regions. html_cell(region, company, row) returns the inner html of one cell."""
    top = (
        "<tr><th></th>"
        + "".join(
            f"<th colspan='{len(COVERAGE_COMPANIES)}' class='rg' "
            f"style='color:{color};background:{tint}'>{name}</th>"
            for name, _, color, tint in COVERAGE_REGIONS
        )
        + "</tr>"
    )
    sub = (
        f"<tr><th>{row_label}</th>"
        + "".join(
            f"<th class='n {r}'>{short}</th>"
            for _, r, _, _ in COVERAGE_REGIONS
            for _, short in COVERAGE_COMPANIES
        )
        + "</tr>"
    )
    body = ""
    for row in rows:
        cells = ""
        for region, r, _, _ in COVERAGE_REGIONS:
            for company, _ in COVERAGE_COMPANIES:
                cells += f"<td class='n {r}'>{html_cell(region, company, row)}</td>"
        body += f"<tr><td>{(labels or {}).get(row, row)}</td>{cells}</tr>"
    cols = "<col class='first'>" + "<col>" * (len(COVERAGE_REGIONS) * len(COVERAGE_COMPANIES))
    return f"<table class='cov'><colgroup>{cols}</colgroup>{top}{sub}{body}</table>"


def _footprint_matrix(cells: dict) -> str:
    def inner(region: str, company: str, family: str) -> str:
        cell = cells.get((company, region, family))
        if cell is None:
            return "<i class='mk u'>?</i>"
        return _mark(cell["status"], cell["source_url"])

    return _grid("Product family", COVERAGE_FAMILIES, inner)


def _steps_matrix(steps: dict | None = None) -> str:
    def inner(region: str, company: str, step: str) -> str:
        cell = steps.get((company, region, step)) if steps else None
        if cell is None:
            return "<i class='mk u'>?</i>"
        return _mark(cell["status"], cell["source_url"])

    # Service and support is shown, but it is not a manufacturing step and is not counted.
    return _grid(
        "Bioprocess step",
        COVERAGE_STEPS,
        inner,
        labels={"8. Service and support": "Service and support"},
    )


def _sales_line(sales: dict | None, region: str) -> str:
    """Biotech sales line on a region card: the Q1 2026 figure, its share and the 10-Q link."""
    row = (sales or {}).get(region)
    if row is None:
        return "Biotech sales Q1 2026: to collect"
    return (
        f"Biotech sales Q1 2026: <a href='{row['source_url']}'>${row['value_m']:,.0f}m</a> "
        f"({row['share']:.1f}% of Biotech sales)"
    )


def _region_cards(cells: dict | None, steps: dict | None = None, sales: dict | None = None) -> str:
    """Four region cards in the MVP style: big numbers in the region colour on the region tint."""
    cards = ""
    for region, _r, color, tint in COVERAGE_REGIONS:
        if cells is None:
            fams = "to collect"
            stp = "to collect"
        else:
            made = sum(
                1
                for f in COVERAGE_FAMILIES
                if cells.get(("Cytiva", region, f), {}).get("status") == "Made"
            )
            manufacturing = [
                cell["status"]
                for (company, reg, step), cell in (steps or {}).items()
                if company == "Cytiva" and reg == region and not step.startswith("8.")
            ]
            local = manufacturing.count("Made")
            partial = sum(
                1
                for f in COVERAGE_FAMILIES
                if cells.get(("Cytiva", region, f), {}).get("status") == "Partial"
            )
            extra = f" · {partial} partial" if partial else ""
            fams = (
                f"<span class='big' style='color:{color}'>{made} of 8</span> families made{extra}"
            )
            stp = f"<span class='big' style='color:{color}'>{local} of 7</span> steps local"
        sale = (sales or {}).get(region)
        badge = evidence_badge(
            sale["confidence"] if sale else None, sale["source_url"] if sale else None
        )
        cards += (
            f"<div class='rc' style='background:{tint};border-color:{color}'>"
            f"<div class='rt' style='color:{color}'>{region.upper()} {badge}</div>"
            f"<div class='rn'>{fams} &nbsp; {stp}</div>"
            f"<div class='rs'>{_sales_line(sales, region)}</div></div>"
        )
    return f"<div class='rcs'>{cards}</div>"


def _legend() -> str:
    """Legend under each matrix: the same marks as in the cells."""
    items = [
        ("M", "&#10003;", "Made"),
        ("P", "&#9680;", "Partial or planned"),
        ("N", "&#215;", "Not made (researched, no plant confirmed)"),
        ("u", "?", "No evidence found yet (not the same as not made)"),
    ]
    spans = "".join(
        f"<span><i class='mk {cls}'>{sym}</i>{label}</span>" for cls, sym, label in items
    )
    return f"<div class='legend'>{spans}</div>"


def _step_needs() -> str:
    """The step rule, as the calculation applies it (metrics.coverage.STEP_FAMILIES)."""
    rows = ""
    for step, families in STEP_FAMILIES.items():
        label = step.split(". ", 1)[1] if step.startswith("8.") else step
        chips = "".join(f"<span class='chip'>{f}</span>" for f in families)
        chips = chips or "<span class='note'>No product family: local team</span>"
        rows += f"<div class='need'><b>{label}</b><span>{chips}</span></div>"
    return (
        "<div class='needs'><div class='note'><b>What 100% looks like:</b> a step is green when "
        "the region makes every family it needs (AND). If only some are made, it is yellow "
        "(partial). Step 2 also covers CGT and mRNA. Service and support is shown but not "
        "counted.</div>" + rows + "</div>"
    )


def _fact_and_signal(title: str) -> None:
    """Coverage tables mix Fact (filings, sites) with Signal (job ads, inferred sites)."""
    st.markdown(
        f"<div class='sec'>{title} <span class='badge b-fact'>Fact and Signal</span></div>",
        unsafe_allow_html=True,
    )


def coverage_screen(
    cells: dict | None = None,
    steps: dict | None = None,
    sales: dict | None = None,
) -> None:
    """Screen 2 in the MVP layout: a yellow note; region cards; the two matrices on the left;
    market size and implications on the right. Sections without loaded data show to collect."""
    screen_header(2, "Competitor coverage")
    st.markdown(_region_cards(cells, steps, sales), unsafe_allow_html=True)
    note(
        "Each mark links to its public source. A ? is a researched lead that is not yet "
        "confirmed. Where we are ahead or behind peers, and where price power is at risk."
    )
    left, right = st.columns([2.6, 1], gap="small")
    with left:
        with st.container(border=True):
            _fact_and_signal("Product families made in region")
            if cells is None:
                placeholder("Not loaded yet: run the refresh. To collect.")
            else:
                st.markdown(
                    f"<div class='covwrap'>{_footprint_matrix(cells)}</div>",
                    unsafe_allow_html=True,
                )
                st.markdown(_legend(), unsafe_allow_html=True)
        with st.container(border=True):
            _fact_and_signal("Bioprocess steps supplied from own region")
            st.markdown(
                f"<div class='covwrap'>{_steps_matrix(steps)}</div>", unsafe_allow_html=True
            )
            st.markdown(_legend(), unsafe_allow_html=True)
            st.markdown(_step_needs(), unsafe_allow_html=True)
    with right:
        with st.container(border=True):
            market_share_tile()
        with st.container(border=True):
            section("Implications for Finance & IT", "hyp")
            hypothesis("Can Finance see product margin after freight, duties and transfer pricing?")
            hypothesis("Can we analyse price, volume and mix by product and customer?")


TINT = {
    "North America": ("#E3F4EC", "#0F5A3C"),
    "Western Europe": ("#E5F0FB", "#1E3F73"),
    "High-growth markets": ("#EEEAF8", "#3D2E7A"),
    "Other developed markets": ("#FAF0E0", "#6B4A12"),
}
REGION_SHORT = {
    "North America": "N. America",
    "Western Europe": "W. Europe",
    "High-growth markets": "High-growth",
    "Other developed markets": "Other developed",
}


def _score_bg(score: float | None) -> str:
    if score is None:
        return "#F4F6F8"
    if score < 2:
        return "#E6F4EC"
    if score < 3.5:
        return "#FFF4D6"
    return "#FDECEA"


def _cluster_map(hubs: list[dict], local: dict[str, int]) -> go.Figure:
    from src.metrics import clusters as cm

    fig = go.Figure()
    for region, isos in cm.MAP_ISO3.items():
        fill = TINT[region][0]
        fig.add_trace(
            go.Choropleth(
                locations=isos,
                z=[1] * len(isos),
                colorscale=[[0, fill], [1, fill]],
                showscale=False,
                marker_line_color="#FFFFFF",
                hoverinfo="skip",
            )
        )
    for h in hubs:
        if not h["position"]:
            continue
        lat, lon = h["position"]
        colour, label = cm.local_colour(h["region"], local)
        size = cm.bubble_size(h["count"])
        count_text = (
            f"{h['count']:,.0f} {h['type']} ({h['scope']})"
            if h["count"] is not None
            else "density count: to collect"
        )
        fig.add_trace(
            go.Scattergeo(
                lat=[lat],
                lon=[lon],
                mode="markers+text",
                marker={
                    "size": size,
                    "color": colour,
                    "opacity": 0.6,
                    "line": {"color": colour, "width": 1.2},
                },
                text=[h["hub"].split(" (")[0].split(" / ")[0]],
                textposition="top center",
                textfont={"size": 9, "color": "#24414F"},
                hovertext=f"{h['hub']}<br>{count_text}<br>Cytiva region: {label}",
                hoverinfo="text",
                showlegend=False,
            )
        )
    fig.update_geos(
        showland=True,
        landcolor="#F4F6F8",
        showcountries=True,
        countrycolor="#E2E7EC",
        showcoastlines=False,
        showframe=False,
        projection_type="natural earth",
        lataxis_range=[-45, 72],
        lonaxis_range=[-135, 160],
    )
    fig.update_layout(
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        height=260,
        paper_bgcolor="rgba(0,0,0,0)",
        geo={"bgcolor": "rgba(0,0,0,0)"},
    )
    return fig


def _signal_tags(signals: list[dict]) -> str:
    chips = []
    for s in signals:
        up = s["direction"] == "up"
        arrow, fg, bg = (
            ("&#9650;", "#1E6B45", "#E6F4EC") if up else ("&#9660;", "#9A2A1E", "#FDECEA")
        )
        value = f"{s['value']:,.0f}" if s["value"] is not None else ""
        chips.append(
            f"<a href='{s['source_url']}' target='_blank' style='text-decoration:none'>"
            f"<span style='display:inline-block;margin:2px 4px 2px 0;padding:3px 8px;"
            f"border-radius:12px;background:{bg};color:{fg};font-size:10.5px;font-weight:600'>"
            f"<span style='font-size:9px'>{arrow}</span> {s['geography']}: {s['indicator']} "
            f"{value} {s['unit'] or ''} ({s['period']})</span></a>"
        )
    return "".join(chips)


def _region_tag(region: str | None) -> str:
    if region is None:
        return ""
    bg, fg = TINT[region]
    return (
        f"<span style='padding:1px 7px;border-radius:9px;background:{bg};color:{fg};"
        f"font-size:9.5px;font-weight:700'>{REGION_SHORT[region]}</span>"
    )


def _top_hubs_table(rows: list[dict], hubs: list[dict]) -> str:
    body = ""
    for i, r in enumerate(rows[:6], 1):
        region = next((h["region"] for h in hubs if h["hub_id"] == r["hub_id"]), None)
        link = f"<a href='{r['source_url']}' target='_blank'>source</a>"
        body += (
            f"<tr><td>{i}</td><td style='font-weight:600'>{r['hub']}</td>"
            f"<td>{_region_tag(region)}</td>"
            f"<td style='text-align:right;font-weight:700'>{r['count']:,.0f}</td>"
            f"<td>{r['type']} ({r['scope']})</td><td>{r['as_of'] or ''}</td>"
            f"<td>{r['confidence']}</td><td>{link}</td></tr>"
        )
    no_count = [h["hub"].split(" (")[0] for h in hubs if h["count"] is None]
    footer = (
        "<div style='font-size:10px;color:#6B7A88;margin-top:4px'>No density count in the "
        f"sheet yet: {', '.join(no_count)}.</div>"
        if no_count
        else ""
    )
    return (
        "<table style='width:100%;border-collapse:collapse;font-size:11px'>"
        "<tr style='font-size:9px;color:#6B7A88;text-transform:uppercase'>"
        "<th style='text-align:left'>#</th><th style='text-align:left'>Hub</th>"
        "<th style='text-align:left'>Region</th><th style='text-align:right'>Count</th>"
        "<th style='text-align:left'>Type</th><th style='text-align:left'>As of</th>"
        "<th style='text-align:left'>Conf.</th><th></th></tr>" + body + "</table>" + footer
    )


def _barrier_table(countries: list[dict]) -> str:
    """Scores (tariffs, customs clearance, local buying preference), the Tholos trade openness
    index (lower = more open) and the barrier index (average of the scores present)."""
    dims = [
        # LEGACY tariff score: from the old CSV until it is in the seed sheet (SIGNAL at most).
        ("Tariffs (legacy, SIGNAL)", "tariff_score_1_5"),
        ("Customs clearance", "customs_friction_1_5"),
        ("Local buying preference", "local_preference_1_5"),
    ]
    head = "".join(f"<th style='text-align:center'>{d}</th>" for d, _ in dims)
    body = ""
    for c in countries:
        cells = ""
        for _, key in dims:
            v = c[key]
            txt = (
                "&ndash;"
                if v is None
                else (f"{v:.0f}" if key == "tariff_score_1_5" else f"{v:.1f}")
            )
            cells += (
                f"<td style='text-align:center;background:{_score_bg(v)};padding:3px'>{txt}</td>"
            )
        tbi = c.get("tbi_2025_score")  # absent in a database refreshed before CD-27
        tbi_txt = "&ndash;" if tbi is None else f"{tbi:.2f}"
        idx = c["barrier_index"]
        idx_col = "#B23A2C" if idx is not None and idx >= 2.5 else "#1B2430"
        body += (
            f"<tr><td style='font-weight:600'>{c['country']}</td>{cells}"
            f"<td style='text-align:center;color:#3A4A58'>{tbi_txt}</td>"
            f"<td style='text-align:center;font-weight:700;color:{idx_col}'>{idx:.1f}"
            + (
                f"<div class='t-meta'>{c['display_on_tile']}</div>"
                if c.get("display_on_tile") and not c["display_on_tile"].startswith("Index")
                else ""
            )
            + "</td></tr>"
        )
    return (
        "<table style='width:100%;border-collapse:collapse;font-size:10.5px'>"
        "<tr style='font-size:9px;color:#6B7A88;text-transform:uppercase'>"
        "<th style='text-align:left'>Country</th>"
        + head
        + "<th style='text-align:center'>Trade openness index 2025 (legacy, SIGNAL)</th>"
        "<th style='text-align:center'>Barrier index</th></tr>" + body + "</table>"
    )


def clusters_screen(data=None) -> None:
    """Screen 3 on one page, MVP layout: headline figures, map with hubs and signal tags (left),
    top hubs and entry barrier index (right). Values come from the sheet and the sources they cite;
    anything missing shows as to collect."""
    from src.metrics import clusters as cm

    screen_header(3, "Customer clusters")
    if data is None:
        placeholder("Not loaded yet: run the refresh. To collect.")
        return
    hubs = cm.all_hubs(data)
    h = cm.headline_tiles(data)

    def _hub(r: dict | None) -> str:
        return f"{r['count']:,.0f} {r['type']}" if r else "to collect"

    cards = (
        (
            "Densest hub in the world",
            h["densest"]["hub"].split(" (")[0] if h["densest"] else "to collect",
            f"{_hub(h['densest'])} ({h['densest']['scope']})" if h["densest"] else "",
        ),
        (
            "Largest hub Cytiva does not supply locally",
            h["gap"]["hub"].split(" (")[0] if h["gap"] else "none",
            f"{_hub(h['gap'])}; Cytiva makes {h['gap_steps']} of 7 steps in this region"
            if h["gap"]
            else "",
        ),
        (
            "Densest hub with a low barrier",
            h["entry"]["hub"].split(" (")[0] if h["entry"] else "none",
            f"{_hub(h['entry'])}; country barrier index {h['entry_index']:.1f}"
            if h["entry"]
            else "",
        ),
        (
            "End-market signals: rising vs falling",
            f"{h['rising']} rising, {h['falling']} falling",
            "signals with a stated change; arrows on the map panel",
        ),
    )
    for col, (label, value, sub) in zip(st.columns(4), cards, strict=True):
        with col:
            kpi_card(label, value, sub)

    st.markdown(
        "<div style='font-size:10px;color:#6B7A88;margin:-4px 0 6px'>Densest = highest density "
        "count (companies, sites, plants or organisations; type shown). Not supplied locally = "
        "Cytiva makes 0 of 7 manufacturing steps in the hub's region (screen 2). Low barrier = "
        "country barrier index below 2.0. Rising and falling = end-market signals that state a "
        "change.</div>",
        unsafe_allow_html=True,
    )
    local = data.local_steps
    left, right = st.columns([1.15, 1], gap="small")
    with left:
        with st.container(border=True):
            section("Biotech hubs by density", "fact")
            st.plotly_chart(
                _cluster_map(hubs, local), width="stretch", config={"displayModeBar": False}
            )
            st.markdown(
                "<div style='font-size:10px;color:#3A4A58'>"
                "<span style='color:#2E9E5B'>&#9679;</span> Mostly local (5&ndash;7 of 7) &nbsp; "
                "<span style='color:#E0A44A'>&#9679;</span> Partly local &nbsp; "
                "<span style='color:#C2412D'>&#9679;</span> Imported &nbsp; "
                "<span style='color:#6B7A88'>bubble = density count; grey = to collect. "
                "Colour: Cytiva steps made in the hub's region (screen 2).</span></div>",
                unsafe_allow_html=True,
            )
        with st.container(border=True):
            section("End-market demand", "signal")
            st.markdown(_signal_tags(cm.directional_signals(data)), unsafe_allow_html=True)
            st.markdown(
                "<div style='font-size:10px;color:#6B7A88'>&#9650; green: rising demand or "
                "interest. &#9660; red: falling. Source linked on each tag.</div>",
                unsafe_allow_html=True,
            )
    with right:
        with st.container(border=True):
            section("Top hubs by density", "fact")
            st.markdown(_top_hubs_table(cm.density_rows(data), hubs), unsafe_allow_html=True)
        with st.container(border=True):
            section("Market entry barrier index", "hyp")
            st.markdown(_barrier_table(data.countries), unsafe_allow_html=True)
            st.markdown(
                "<div style='font-size:10px;color:#6B7A88;margin-top:4px'>Scores run from 1 (low "
                "barrier) to 5 (high barrier). A dash means not yet assessed. The barrier index "
                "averages only the scores present. Tariff score: below 5% = 1, 5&ndash;10% = 3, "
                "10% and above = 5 (WTO applied rate, 2025). The trade openness index is "
                "published by the Tholos Foundation on its own scale (lower = more open) and is "
                "shown for comparison only.</div>",
                unsafe_allow_html=True,
            )


def _pct_bar(label: str, value: float | None, maximum: float, text: str) -> str:
    width = 0 if not value or not maximum else min(100, value / maximum * 100)
    return (
        f"<div style='display:flex;align-items:center;gap:6px;font-size:10.5px;margin:2px 0'>"
        f"<span style='width:150px'>{label}</span>"
        f"<div style='flex:1;height:9px;background:#F1F4F7;border-radius:4px'>"
        f"<div style='width:{width:.0f}%;height:9px;background:#1E4257;border-radius:4px'>"
        f"</div></div><span style='width:90px;text-align:right'>{text}</span></div>"
    )


def _flag_chip(flag: str) -> str:
    colours = {
        "Yes": ("#E6F4EC", "#1E6B45"),
        "Partly": ("#FFF4D6", "#7A5A00"),
        "No": ("#FDECEA", "#9A2A1E"),
    }
    bg, fg = colours.get(flag, ("#F4F6F8", "#6B7A88"))
    return (
        f"<span style='padding:1px 7px;border-radius:9px;background:{bg};color:{fg};"
        f"font-size:9.5px;font-weight:700'>{flag}</span>"
    )


def _burden_map(points: list[dict]) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scattergeo(
            lat=[p["lat"] for p in points],
            lon=[p["lon"] for p in points],
            mode="markers",
            marker={
                "size": [max(8, min(40, (p["cases"] / 1e6) ** 0.5 * 14)) for p in points],
                "color": "#1E4257",
                "opacity": 0.55,
                "line": {"color": "#1E4257", "width": 1},
            },
            hovertext=[
                f"{p['country']}: {p['cases']:,.0f} new cancer cases (2022)" for p in points
            ],
            hoverinfo="text",
        )
    )
    fig.update_geos(
        showland=True,
        landcolor="#F4F6F8",
        showcountries=True,
        countrycolor="#E2E7EC",
        showcoastlines=False,
        showframe=False,
        projection_type="natural earth",
        lataxis_range=[-45, 72],
        lonaxis_range=[-135, 160],
    )
    fig.update_layout(
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        height=260,
        paper_bgcolor="rgba(0,0,0,0)",
        geo={"bgcolor": "rgba(0,0,0,0)"},
    )
    return fig


def _cell(value, fallback: str = "to collect", year: bool = False) -> str:
    """A table value as text: numbers get thousands separators, empty values the fallback.
    A year is shown as it is written (2028, never 2,028)."""
    if value is None or value == "":
        return fallback
    if year:
        return str(value).strip()
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float):
        return f"{value:,.0f}" if value.is_integer() else f"{value:,.1f}"
    text = str(value).strip()
    try:
        number = float(text.replace(",", ""))
    except ValueError:
        return text  # text, NA and other non-numbers are shown as they are
    decimals = len(text.split(".")[1]) if "." in text else 0
    return f"{number:,.{decimals}f}"


def demand_screen(data=None) -> None:
    """Screen 4, from the research sheet. Every figure is stored with its source URL.
    Anything the sheet does not give shows as to collect."""
    from src.metrics import demand as dm

    screen_header(4, "Demand drivers")
    if data is None:
        placeholder("Not loaded yet: run the refresh. To collect.")
        return

    fda = dm.fda_biologics_2025(data)
    pipe = dm.pipeline_totals(data)
    total_pipe = pipe["total"]
    cards = (
        (
            "FDA biologics approved 2025",
            f"{fda['total']}" if fda["total"] is not None else "to collect",
            f"{fda['cder']} CDER biologics + {fda['cber']} CBER gene and cell therapies"
            if fda["total"] is not None
            else "",
        ),
        (
            "Top-15 drug sales from mAbs",
            f"${dm.mab_sales_top15(data):,.1f} bn",
            "FY2025, Pharma 50 (secondary source)",
        ),
        (
            "Gene, cell and RNA therapies in development",
            _num_fmt(total_pipe["value"]) if total_pipe else "to collect",
            "Q2 2026, ASGCT and Citeline",
        ),
        (
            "US manufacturing pledges listed",
            f"${dm.pledges_total(data):,.1f} bn",
            "pledges, not spend",
        ),
    )
    for col, (label, value, sub) in zip(st.columns(4), cards, strict=True):
        with col:
            kpi_card(label, value, sub)

    left, mid, right = st.columns([1.1, 1, 1.1], gap="small")
    with left:
        with st.container(border=True):
            section("Top 10 countries by new cancer cases", "fact")
            st.plotly_chart(
                _burden_map(dm.map_points(data)), width="stretch", config={"displayModeBar": False}
            )
            st.markdown(
                html_table(
                    [
                        "Country",
                        "New cancer cases 2024",
                        "Adults with diabetes 2024, m",
                        "DALYs 2021, m",
                        "Source",
                    ],
                    [
                        [
                            r["country"],
                            _cell(r["new_cancer_cases_2024"]),
                            _cell(r["diabetes_adults_2024_m"]),
                            _cell(r["dalys_2021_m"]),
                            source_link(r["cancer_2024_source_url"]),
                        ]
                        for r in dm.top_burden(data)
                    ],
                ),
                unsafe_allow_html=True,
            )
            note(
                "Ranked by new cancer cases in 2024 (GLOBOCAN 2024), one source. Diabetes "
                "(IDF 2024) shown beside it. DALYs (WHO GHE) are to collect."
            )
        with st.container(border=True):
            section("Pipeline by medicine type", "fact")
            rows = [r for r in pipe["rows"] if not r["medicine_type"].startswith("Gene, cell")]
            maximum = max((_num_val(r["value"]) or 0 for r in rows), default=0)
            st.markdown(
                "".join(
                    _pct_bar(
                        r["medicine_type"].split(" (")[0],
                        _num_val(r["value"]),
                        maximum,
                        r["value"],
                    )
                    for r in rows
                ),
                unsafe_allow_html=True,
            )
            note("Therapies in development, preclinical to pre-registration, Q2 2026.")
            st.markdown(
                html_table(
                    ["Medicine type", "Measure", "Value", "Period", "Confidence", "Source"],
                    [
                        [
                            r["medicine_type"],
                            r["metric"],
                            _cell(r["value"]),
                            r["period"],
                            r["confidence"] or "n/d",
                            source_link(r["source_url"]),
                        ]
                        for r in dm.other_pipeline(data)
                    ],
                ),
                unsafe_allow_html=True,
            )
            note(
                "Other counts measure different things (approvals, late-stage antibodies, trials, "
                "drugs in R&D). They are not comparable with the bars above."
            )
    with mid:
        with st.container(border=True):
            section("Approvals, 2025 and 2026 to date", "fact")
            st.markdown(
                html_table(
                    ["Regulator", "Measure", "Period", "Value", "Confidence", "Source"],
                    [
                        [
                            r["regulator"],
                            r["metric"],
                            r["period"],
                            _cell(r["value"]),
                            r["confidence"] or "n/d",
                            source_link(r["source_url"]),
                        ]
                        for r in data.approvals
                    ],
                ),
                unsafe_allow_html=True,
            )
        with st.container(border=True):
            section("Biosimilar wave (patent expiries)", "signal")
            st.markdown(
                html_table(
                    ["Drug", "Owner", "Expiry", "Confidence", "Source"],
                    [
                        [
                            r["drug"],
                            r["owner"],
                            _cell(r["year"], year=True),
                            r["confidence"] or "n/d",
                            source_link(r["source_url"]),
                        ]
                        for r in data.expiries
                    ],
                ),
                unsafe_allow_html=True,
            )
            note(
                "Ocrevus is not in the table: its year is not verified and it has no source yet. "
                "Two sources are 2024 articles and are to be replaced with company filings."
            )
        with st.container(border=True):
            section("Policy and funding", "fact")
            for r in data.policy:
                st.markdown(
                    f"<div style='font-size:10.5px;margin:3px 0'><span style='font-weight:700'>"
                    f"{r['item']}</span> <span style='color:#6B7A88'>({r['label']}, {r['date']})"
                    f"</span><br>{r['what_it_says']}</div>",
                    unsafe_allow_html=True,
                )
    with right:
        with st.container(border=True):
            section("Biggest drugs, FY2025 sales", "fact")
            st.markdown(
                html_table(
                    ["Drug", "Company", "Sales, $bn", "Type", "Made with bioprocess", "Source"],
                    [
                        [
                            r["drug"],
                            r["company"],
                            _cell(r["sales_fy2025_usd_bn"]),
                            r["type"],
                            dm.bioprocess_flag(r["bioprocess_use"]),
                            source_link(r["source_url"]),
                        ]
                        for r in data.top_drugs
                    ],
                ),
                unsafe_allow_html=True,
            )
            note(
                "Source: Drug Discovery and Development Pharma 50 (FY2025), a secondary "
                "compilation of company reports. Currency differences noted in the source."
            )
        with st.container(border=True):
            section("Capacity pledges", "signal")
            st.markdown(
                html_table(
                    ["Company", "Pledge, $bn", "Period", "Relevance", "Source"],
                    [
                        [
                            r["company"],
                            _cell(r["pledge_or_capacity"]),
                            r["period"],
                            r["biologics_relevance"],
                            source_link(r["source_url"]),
                        ]
                        for r in data.capacity
                        if r["kind"] == "Pledge"
                    ],
                ),
                unsafe_allow_html=True,
            )
            note("Pledges, not money spent; periods differ and some include R and D.")
        with st.container(border=True):
            section("Cytiva products used, by medicine type", "hyp")
            note("Inferred, to test.")
            placeholder(
                f"{len(data.product_use)} rows awaiting confirmation. Hidden by default: "
                "analyst judgement, no source."
            )
            note(
                "High = core input; Some = used in part of the process; None = little or no use. "
                "To validate with Cytiva product and commercial teams."
            )
        with st.container(border=True):
            section("Implications for Finance & IT", "hyp")
            for r in data.implications:
                hypothesis(f"{r['hypothesis']} ({r['area']})")


def _num_val(text: str | None) -> float | None:
    """A sheet number as a float; "NA", "n/d" and blanks are None (to collect)."""
    if text is None or str(text).strip() in ("", "NA", "n/d"):
        return None
    return float(str(text).replace(",", "").replace("%", ""))


def _num_fmt(value: str | None) -> str:
    v = _num_val(value)
    return "to collect" if v is None else f"{v:,.0f}"


def _register_table(register: list[dict]) -> str:
    head = (
        "<tr><th>Product</th><th>Where used</th><th>Vendor support status</th><th>Source</th></tr>"
    )
    body = "".join(
        f"<tr><td>{r['product']}</td><td>{r['where_used']}</td>"
        f"<td>{r['vendor_support_status']}</td>"
        f"<td><a href='{r['source_url']}'>link</a></td></tr>"
        for r in register
    )
    return f"<table class='c'>{head}{body}</table>"


def _incidents_table(incidents: list[dict]) -> str:
    head = (
        "<tr><th>Date added</th><th>Vendor</th><th>Vulnerability</th><th>Estate product</th></tr>"
    )
    body = "".join(
        f"<tr><td>{i['incident_date']}</td><td>{i['vendor']}</td>"
        f"<td><a href='{i['source_url']}'>{i['cve']}</a> · {i['title'].split(': ', 1)[-1]}</td>"
        f"<td>{i['estate_link']}</td></tr>"
        for i in incidents
    )
    return f"<table class='c'>{head}{body}</table>"


def _format_check(stamp: str) -> str:
    """'2026-11-09T14:18:22+00:00' -> 'checked 9 Nov 2026, 14:18 UTC' (the refresh runs in UTC)."""
    moment = datetime.fromisoformat(stamp).astimezone(UTC)
    return f"checked {moment:%d %b %Y, %H:%M} UTC".replace(" 0", " ")


_CHIP = {
    "H": ("FACT", "#E6F4EC", "#1E6B45", ""),
    "M": ("SIGNAL", "#FFF4D6", "#7A5A00", ""),
    "L": ("UNCONFIRMED", "#F4F6F8", "#6B7A88", "dashed"),
}
_EOS_COLOUR = {
    "red": ("#FDECEA", "#9A2A1E"),
    "amber": ("#FFF4D6", "#7A5A00"),
    "green": ("#E6F4EC", "#1E6B45"),
    "grey": ("#F4F6F8", "#6B7A88"),
}
_LEVEL_COLOUR = {
    "Strong": ("#E6F4EC", "#1E6B45"),
    "Emerging": ("#FFF4D6", "#7A5A00"),
    "Early": ("#E7F1F6", "#1E4257"),
    "No public signal": ("#F4F6F8", "#6B7A88"),
}


def _badge(conf: str) -> str:
    text, bg, fg, border = _CHIP.get(conf, _CHIP["L"])
    style = f"background:{bg};color:{fg};border:1px {border or 'solid'} {fg};"
    return (
        f"<span style='{style}padding:1px 6px;border-radius:9px;font-size:9px;"
        f"font-weight:700;letter-spacing:.3px'>{text}</span>"
    )


def _hyp_badge(conf: str) -> str:
    return (
        f"<span style='background:#F1E9FB;color:#5B2E91;padding:1px 6px;border-radius:9px;"
        f"font-size:9px;font-weight:700'>HYPOTHESIS</span> "
        f"<span style='font-size:9px;color:#6B7A88'>confidence {conf}</span>"
    )


def _evidence_drawer(data, row_type: str, row: dict) -> None:
    """Side panel for one row: the quote, every linked source, the estate evidence, the
    confidence, and (for implications) the rows it is based on."""
    from src.metrics import technology as tm

    @st.dialog("Evidence")
    def _show() -> None:
        st.markdown(f"**{row.get('id') or row.get('watch_id') or row.get('feed_id')}**")
        q = tm.evidence_text(row)
        if q:
            st.markdown(f"> {q}")
        conf = row.get("confidence") or row.get("date_confidence") or ""
        if conf:
            st.markdown(f"Confidence: **{conf}**")
        for s in tm.sources_for(data, row_type, row.get("id") or row.get("watch_id") or ""):
            st.markdown(
                f"- {s['title']} · {s['publisher']} · {s['date_text']} · tier "
                f"{s['tier']} · [{s['url']}]({s['url']})"
            )
        if row_type == "tech_implications":
            for rid in tm.based_on(data, row.get("based_on")):
                st.markdown(f"- Based on **{rid}**")
            st.markdown(f"Would confirm or refute: {row.get('confirm_or_refute', '')}")
        for e in tm.estate_for(data, re.findall(r"EST-\d+", row.get("estate_evidence_ids") or "")):
            st.markdown(
                f"- Estate {e['id']}: {e['evidence_quote']} "
                f"({e['operating_company']}, confidence {e['confidence']})"
            )

    _show()


def _row_button(label: str, key: str, data, row_type: str, row: dict) -> None:
    if st.button(label, key=key, type="tertiary"):
        _evidence_drawer(data, row_type, row)


# Colour keys for the technology tables: confidence (H, M, L), relevance (High, Medium, Low).
_HEAT = {
    "H": ("#E6F4EC", "#1E6B45"),
    "M": ("#FFF4D6", "#7A5A00"),
    "L": ("#EEF1F4", "#6B7A88"),
    "High": ("#FBEAEA", "#B23A2C"),
    "Medium": ("#FFF4D6", "#7A5A00"),
    "Low": ("#EEF1F4", "#6B7A88"),
}


def _chip(text: str, bg: str, fg: str) -> str:
    return (
        f"<span style='background:{bg};color:{fg};padding:1px 6px;border-radius:8px;"
        f"font-weight:600;white-space:nowrap'>{text}</span>"
    )


def _heat(text: str, key: str) -> str:
    bg, fg = _HEAT.get(key, _HEAT["L"])
    return _chip(text, bg, fg)


def _first_source(data, row_type: str, row_id: str) -> str:
    """The public link of a row's first source, or a dash."""
    from src.metrics import technology as tm

    found = tm.sources_for(data, row_type, row_id)
    return source_link(found[0]["url"]) if found else "&ndash;"


def _integration_heatmap(data) -> str:
    """Systems against readiness groups. A filled cell means the system sits in that group; its
    colour is the confidence of the grouping."""
    from src.metrics import technology as tm

    groups = tm.integration_groups(data)
    systems: dict[str, dict] = {}
    for g in groups:
        for m in g["members"]:
            entry = systems.setdefault(
                m["system"], {"id": m["id"], "interfaces": m["interfaces_available"], "cells": {}}
            )
            entry["cells"][g["key"]] = m["confidence"]
    heads = ["System", *[g["title"] for g in groups], "Interfaces", "Source"]
    rows = []
    for name, entry in systems.items():
        cells = [
            _heat(entry["cells"][g["key"]], entry["cells"][g["key"]])
            if g["key"] in entry["cells"]
            else ""
            for g in groups
        ]
        rows.append(
            [
                f"<b>{name}</b>",
                *cells,
                entry["interfaces"] or "&ndash;",
                _first_source(data, "tech_integrations", entry["id"]),
            ]
        )
    return html_table(heads, rows)


def _fixed_status(r: dict) -> str:
    """Whether a vendor fix exists, from the vendor statement or the action; never assumed."""
    statement = (r.get("vendor_statement") or "").strip()
    action = (r.get("action") or "").strip()
    if statement.lower().startswith("fixed"):
        return "Fixed"
    if action.lower().startswith("patch by deadline"):
        return "Patch due"
    if action.lower().startswith("patch available"):
        return "Patch available"
    return "Not reported"


def _exposure_table(data, rows: list[dict]) -> str:
    """Application, vendor, date, nature of the failure, and whether it is fixed. Rows with scope
    L are marked UNCONFIRMED. A Vendor match is tagged; an Exact match is not."""
    out = []
    for r in rows:
        nature = f"<div style='white-space:normal;min-width:150px'><b>{r['type'] or 'n/d'}</b>"
        if r.get("scope_confidence") == "L":
            nature += " <span class='t-meta'>UNCONFIRMED</span>"
        nature += "</div>"
        tag = "" if r.get("match") == "Exact" else " <span class='t-meta'>vendor match</span>"
        out.append(
            [
                (r.get("app") or r["product"] or "n/d") + tag,
                r["vendor"] or "n/d",
                r["date_value"] or "n/d",
                nature,
                _fixed_status(r),
            ]
        )
    return html_table(["Product", "Vendor", "Date", "Nature of failure", "Fixed or not"], out)


def _adoption_table(data, rows: list[dict]) -> str:
    """Technology first, then the adoption level, then an example that links to its source."""
    from src.metrics import technology as tm

    out = []
    for r in rows:
        bg, fg = _LEVEL_COLOUR.get(r["level"], _LEVEL_COLOUR["No public signal"])
        found = tm.sources_for(data, "tech_adoption", r["id"])
        example = r["signal"] or ""
        if found:
            example = f"<a href='{found[0]['url']}'>{example}</a>"
        date_text = r["signal_date_text"] or ""
        out.append(
            [
                f"<b>{r['technology']}</b>",
                _chip(r["level"], bg, fg),
                f"{example} <span class='t-meta'>{date_text}</span>",
            ]
        )
    return html_table(["Technology", "Adoption", "Example"], out)


def _vendor_to(text: str | None) -> str:
    """Cytiva when only Cytiva is named as the buyer; otherwise Danaher."""
    names = [n.strip() for n in re.split(r"[;,]", text or "") if n.strip()]
    if len(names) == 1 and names[0].startswith("Cytiva"):
        return "Cytiva"
    return "Danaher" if names else "n/d"


def _wrap(text: str) -> str:
    """Long text wraps inside its table column instead of stretching the tile."""
    return f"<div style='white-space:normal;min-width:150px'>{text}</div>"


def _implications_table(rows: list[dict]) -> str:
    """Hypotheses with their confidence. The text wraps inside the Hypothesis column."""
    body = [
        [
            f"<div style='white-space:normal;min-width:240px'>{r['hypothesis']}</div>",
            _heat(r["confidence"], r["confidence"]),
        ]
        for r in rows
    ]
    return html_table(["Hypothesis", "Confidence"], body)


# Applications on the End of support tile, with the end-of-support row they match (if any).
APP_EOS = {"Oracle E-Business Suite": "EOS-02", "SAP ERP (ECC)": "EOS-01"}


def _eos_table(data, rows: list[dict]) -> str:
    """Tile 1: application, and the support milestone with its status colour, the tile note
    under the date, and the confidence badge. Source link in the drawer."""
    out = []
    for r in rows:
        bg, fg = _EOS_COLOUR[r["colour"]]
        note = f"<div class='t-meta'>{r['tile_note']}</div>" if r.get("tile_note") else ""
        milestone = (
            _chip(r["status_text"] or "&ndash;", bg, fg)
            + " "
            + _heat(r["confidence"], r["confidence"])
            + note
        )
        out.append([f"<b>{r['product']}</b>", milestone])
    return html_table(["Application", "End of support"], out)


def technology_screen(data=None, today=None) -> None:
    """Screen 5 (MVP layout): five tiles. Clicking a row (or a chip) opens its evidence."""
    from datetime import date as _date

    from src.metrics import technology as tm

    today = today or _date.today()
    screen_header(5, "Technology estate")
    if data is None:
        placeholder("Not loaded yet: run the refresh. To collect.")
        return
    readme = next((n["text"] for n in data.notes if n["label"] == "As of"), "")
    st.markdown(
        f"<div class='t-body'>Data as of {readme}. Public sources; "
        "every value links to its evidence.</div>",
        unsafe_allow_html=True,
    )

    left, right = st.columns([1.1, 1], gap="small")
    with left:
        with st.container(border=True):
            section("End of support", "fact")
            rows = tm.eos_tile_rows(data, today)
            if not rows:
                st.markdown("<div class='t-meta'>No items to show.</div>", unsafe_allow_html=True)
            else:
                st.markdown(_eos_table(data, rows), unsafe_allow_html=True)
            note_text = tm.eos_note(data)
            if note_text:
                st.markdown(f"<div class='t-meta'>{note_text}</div>", unsafe_allow_html=True)
        with st.container(border=True):
            section("Integration readiness", "fact")
            st.markdown(
                "<div class='t-meta'>Grouping is a hypothesis from vendor "
                "interfaces, not from how Cytiva built each integration.</div>",
                unsafe_allow_html=True,
            )
            st.markdown(
                "<div class='t-meta'>Cell colour = confidence of the grouping: "
                "H high, M medium, L low (hidden unless shown).</div>",
                unsafe_allow_html=True,
            )
            st.markdown(_integration_heatmap(data), unsafe_allow_html=True)
        with st.container(border=True):
            section("Implications for Finance & IT", "hyp")
            st.markdown(_implications_table(tm.implication_rows(data)), unsafe_allow_html=True)
    with right:
        with st.container(border=True):
            section("Security issues in apps we use · last 30 days", "signal")
            exp = tm.exposure(data, today)
            st.markdown(
                f"<div class='t-meta'>{exp['window']}</div>",
                unsafe_allow_html=True,
            )
            show_unconfirmed = st.toggle(
                "Show unconfirmed (L)", value=False, key="tech_tile2_unconfirmed"
            )
            rows = exp["shown"] + (exp["unconfirmed"] if show_unconfirmed else [])
            if rows:
                st.markdown(_exposure_table(data, rows), unsafe_allow_html=True)
            else:
                st.markdown(
                    f"<div class='t-strong'>{tm.PENDING_EMPTY}</div>", unsafe_allow_html=True
                )
            if exp["pending"]:
                st.markdown(
                    f"<div class='t-meta'>{len(exp['pending'])} more awaiting confirmation</div>",
                    unsafe_allow_html=True,
                )
            st.markdown(
                "<div class='t-foot'>Public sources only. "
                "Whether Cytiva was affected is unknown.</div>",
                unsafe_allow_html=True,
            )
        with st.container(border=True):
            section("Technology adoption signals", "fact")
            st.markdown(_adoption_table(data, tm.adoption_rows(data)), unsafe_allow_html=True)


# Note style for the China notes: the same 9px note as the Overview.
_CN_CSS = (
    "<style>.cn-note{font-size:9px !important;color:#6B7A88;margin:2px 0 0 0 !important;"
    "line-height:1.3}</style>"
)


def _cn_html(head: list[str], rows: list[list[str]]) -> str:
    """China tables use the shared table, as on the other screens."""
    return html_table(head, rows)


def _china_matrix(
    row_label: str,
    rows: list[str],
    columns: list[dict],
    html_cell: Callable[[dict, str], str],
    labels: dict[str, str] | None = None,
) -> str:
    """Screen 2 matrix for the China region: rows are product families or steps, columns are
    companies. Same markup and classes as the screen 2 matrices (table.cov, region tint r0)."""
    top = (
        "<tr><th></th>"
        f"<th colspan='{len(columns)}' class='rg' style='color:#0F5A3C;background:#E3F4EC'>"
        "China</th></tr>"
    )
    head = (
        f"<tr><th>{row_label}</th>"
        + "".join(f"<th class='n r0'>{_cn_short(co)}</th>" for co in columns)
        + "</tr>"
    )
    body = ""
    for row in rows:
        cells = "".join(f"<td class='n r0'>{html_cell(co, row)}</td>" for co in columns)
        body += f"<tr><td>{(labels or {}).get(row, row)}</td>{cells}</tr>"
    # First column is the same width as on screen 2, so family and step names are not cut off.
    cols = "<col class='first'>" + "<col>" * len(columns)
    return (
        f"<div class='covwrap'><table class='cov'><colgroup>{cols}</colgroup>"
        f"{top}{head}{body}</table></div>"
    )


def _cn_short(row: dict) -> str:
    """Company name as a column header. Cytiva is shown as Cytiva; the others keep their names."""
    return row["name_en"].replace(" (in China)", "")


def _cn_link(url: str | None) -> str:
    """Link to the public source. A row with no public source shows a dash."""
    if not url or "docs.google.com/spreadsheets" in url:
        return "&ndash;"
    return f"<a href='{url}'>source</a>"


def _cn_kind(label: str | None) -> str:
    return {"Fact": "fact", "Signal": "signal", "Hypothesis": "hyp"}.get(label or "", "pending")


def _cn_mixed_title(title: str, badge: str) -> None:
    st.markdown(
        f"<div class='sec'>{title} <span class='badge b-fact'>{badge}</span></div>",
        unsafe_allow_html=True,
    )


def _cn_card(data, row: dict | None, title: str, big: str, small: str) -> None:
    """A headline card on the shared KPI card: the evidence label and source sit in the line
    under the value."""
    if row is None:
        kpi_card(title, "to collect")
        return
    kpi_card(
        title,
        big,
        f"{small} · {cm.badge(data, row['confidence'], row['source_note'], row['source_url'])} · "
        f"{row['period'] or ''} · "
        f"{_cn_link(row['source_url'])}",
    )


def _cn_num(value: float | None, fmt: str) -> str:
    return "n/d" if value is None else fmt.format(value)


def _fin_name(r: dict) -> str:
    """Short company name for the financials table: the division is named in brackets."""
    name = r["company"].split(":")[0].strip()
    if r["id"] == "F-03b":
        return f"{name} (bioprocess)"
    return name


def _cn_company(row: dict) -> str:
    name = row["name_en"]
    if row.get("products_checked") == "no":
        name += " <span class='cn-note'>(products not checked)</span>"
    return f"<b>{name}</b>" if row["company_id"] == "C00" else name


def china_screen(data: cm.ChinaData | None = None) -> None:
    screen_header(6, "China")
    note("Selling into China and relying on Chinese vendors. All amounts in USD.")
    st.markdown(_CN_CSS, unsafe_allow_html=True)
    if data is None:
        with st.container(border=True):
            section("China data", "pending")
            placeholder("To collect. The China research sheet has not been loaded yet.")
        return

    # Row 1: the two headline cards on the left, the basis of the figures on the right.
    h1 = data.headline.get("H-01")
    h4 = data.headline.get("H-04")
    card1, card2, basis = st.columns([1, 1, 2], gap="small")
    with card1:
        _cn_card(
            data,
            h1,
            "China share of Danaher sales",
            "" if h1 is None else f"{h1['value_num']:g}%",
            "of Danaher's continuing-operations sales, FY2025",
        )
    with card2:
        _cn_card(
            data,
            h4,
            "China sales growth",
            "" if h4 is None else f"+{h4['value_num']:g}%",
            "China core sales growth year on year, latest quarter",
        )
    with basis, st.container(border=True):
        st.markdown("<div class='lb'>Basis of the figures</div>", unsafe_allow_html=True)
        st.markdown(
            f"<div class='t-meta'>RMB converted at {data.fx_rate:g} RMB per USD, an assumption "
            "until the annual average is loaded. "
            f"{cm.basis_sentence(data)}"
            "Growth shown is the latest reported quarter; no "
            "full-year China growth is disclosed.</div>",
            unsafe_allow_html=True,
        )

    # Row 2: financials (tile 3) and vendors (tile 4), side by side.
    fin_col, ven_col = st.columns(2, gap="small")
    with fin_col, st.container(border=True):
        _cn_mixed_title("Chinese challenger financials (USD)", "Fact and Signal")
        fin_rows = []
        for r in cm.financial_rows(data):
            usd = r["revenue_usd_m_shown"]
            usd_text = "n/d" if usd is None else f"{usd:,.0f}"
            if r["company_id"] == "C00":
                usd_text += " (derived)"
            fin_rows.append(
                [
                    _cn_company({"company_id": r["company_id"], "name_en": _fin_name(r)}),
                    _wrap(r["period"] or "n/d"),
                    usd_text,
                    _cn_num(r["revenue_yoy_pct"], "{:+.1f}%"),
                    _cn_num(r["gross_margin_pct"], "{:.1f}%"),
                ]
            )
        st.markdown(
            _cn_html(
                ["Company", "Period", "Revenue (USD m)", "Growth YoY", "Gross margin"],
                fin_rows,
            ),
            unsafe_allow_html=True,
        )
    with ven_col, st.container(border=True):
        _cn_mixed_title("Chinese vendors to Danaher companies", "Fact and Signal")
        vendor_rows = [
            [
                f"{v['vendor_en']}<br><span class='cn-note'>{v['vendor_cn'] or ''}</span>",
                _wrap(v["supplies"] or "n/d"),
                _vendor_to(v["to_danaher_company"]),
                _wrap(v["relationship"] or "n/d"),
                cm.badge(data, v["confidence"], v["source_note"], v["source_url"]),
                _cn_link(v["source_url"]),
            ]
            for v in data.vendors
        ]
        st.markdown(
            _cn_html(
                ["Vendor", "Supplies", "To Danaher company", "Relationship", "Label", "Source"],
                vendor_rows,
            ),
            unsafe_allow_html=True,
        )

    # Row 3: coverage matrices, full width (screen 2 rule).
    with st.container(border=True):
        _cn_mixed_title("Local competitor coverage in China", "Fact and Signal")
        # Columns: Cytiva first as the reference, then the local competitors in alphabetical order.
        cytiva = [co for co in data.companies if co["company_id"] == "C00"]
        local = sorted(
            (co for co in data.companies if co["company_id"] != "C00"),
            key=lambda co: co["name_en"].casefold(),
        )
        columns = cytiva + local

        def family_cell(co: dict, code: str) -> str:
            cell = data.coverage.get((co["company_id"], code))
            return _mark(cell["status"], cell["source_url"]) if cell else "<i class='mk u'>?</i>"

        def step_cell(co: dict, step: str) -> str:
            cell = data.steps.get((co["company_id"], cm.CHINA_REGION, step))
            return _mark(cell["status"], cell["source_url"]) if cell else "<i class='mk u'>?</i>"

        st.markdown(
            _china_matrix(
                "Product family",
                cm.FAMILY_ORDER,
                columns,
                family_cell,
                labels=FAMILY_NAMES,
            ),
            unsafe_allow_html=True,
        )
        st.markdown(
            _china_matrix(
                "Bioprocess step",
                COVERAGE_STEPS,
                columns,
                step_cell,
                labels={"8. Service and support": "Service and support"},
            ),
            unsafe_allow_html=True,
        )
        st.markdown(_legend(), unsafe_allow_html=True)
        st.markdown(
            "<div class='cn-note'>In this grid, ? means no evidence was found in the sources "
            "checked. It is not proof that the company does not make the family. A step is Made "
            "only when every family it needs is Made.</div>",
            unsafe_allow_html=True,
        )

    # Row 4: commercial opportunities (left) and implications (right), side by side.
    opp_col, imp_col = st.columns(2, gap="small")
    with opp_col, st.container(border=True):
        _cn_mixed_title("Commercial opportunities in China", "Fact, Signal and Hypothesis")
        opp_rows = [
            [
                o["opportunity"],
                o["why"] or "n/d",
                o["product_lines"] or "n/d",
                o["evidence_label"]
                if o["evidence_label"] == "Hypothesis"
                else cm.badge(data, o["confidence"], o["source_note"], o["source_url"]),
                _cn_link(o["source_url"]),
            ]
            for o in data.opportunities
        ]
        st.markdown(
            _cn_html(["Opportunity", "Why", "Product lines", "Label", "Source"], opp_rows),
            unsafe_allow_html=True,
        )
    with imp_col, st.container(border=True):
        section("Implications for Finance & IT", "hyp")
        for imp in data.implications:
            hypothesis(imp["hypothesis"])
            st.markdown(
                f"<div class='cn-note'>Confirm or refute: {imp['confirm_or_refute'] or 'n/d'} · "
                f"Area: {imp['area'] or 'n/d'}</div>",
                unsafe_allow_html=True,
            )
