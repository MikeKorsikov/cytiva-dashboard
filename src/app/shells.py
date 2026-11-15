"""Screens 2 to 6 of the dashboard, laid out as in the MVP design.

These are shells: layout and sections are in place, and each section is marked with its
evidence label. Content that is not loaded yet shows as "to collect" with the research story
that will fill it. No estimate or mockup value is shown as data.

Each section sits in its own white box, as on the Overview.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

import plotly.graph_objects as go
import streamlit as st

from src.app.design import header, hypothesis, note, placeholder, section
from src.app.market_tile import market_share_tile
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
    ("Japan, Australia and New Zealand", "r3", "#6B4A12", "#FAF0E0"),
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


# Biotech sales by Danaher reporting region, Q1 2026 (Note 4 of the 10-Q), $m and share.
# Values from the Legal entities sheet, tab Value-chain coverage. The sheet's "Other developed
# markets" is Japan, Australia and New Zealand. Source: Danaher SEC filings (10-Q).
BIOTECH_SALES_SOURCE = (
    "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0000313616&type=10-Q"
)
BIOTECH_SALES_Q1_2026 = {
    "North America": (524, "29.2%"),
    "Western Europe": (726, "40.4%"),
    "High-growth markets": (490, "27.3%"),
    "Japan, Australia and New Zealand": (57, "3.2%"),
}


def _region_cards(cells: dict | None, steps: dict | None = None) -> str:
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
        cards += (
            f"<div class='rc' style='background:{tint};border-color:{color}'>"
            f"<div class='rt' style='color:{color}'>{region.upper()} "
            "<span class='badge b-fact'>Fact</span></div>"
            f"<div class='rn'>{fams} &nbsp; {stp}</div>"
            f"<div class='rs'>Biotech sales Q1 2026: <a href='{BIOTECH_SALES_SOURCE}'>"
            f"${BIOTECH_SALES_Q1_2026[region][0]}m</a> ({BIOTECH_SALES_Q1_2026[region][1]} "
            "of Biotech sales)</div></div>"
        )
    return f"<div class='rcs'>{cards}</div>"


def _legend() -> str:
    """Legend under each matrix: the same marks as in the cells."""
    items = [
        ("M", "&#10003;", "Made"),
        ("P", "&#9680;", "Partial or planned"),
        ("N", "&#215;", "Not made (researched, no plant confirmed)"),
        ("u", "?", "Researched lead, not yet confirmed"),
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
) -> None:
    """Screen 2 in the MVP layout: a yellow note; region cards; the two matrices on the left;
    market size and implications on the right. Sections without loaded data show to collect."""
    header(
        "Competitor coverage by region",
        "Where are we ahead of or behind peers, and where is price power at risk?",
    )
    st.markdown(
        "<div class='banner'>Cytiva footprint from its 2025 investment programme, Repligen and "
        "Sartorius filings. Each mark links to its public source. A ? is a researched lead "
        "that is not yet confirmed.</div>",
        unsafe_allow_html=True,
    )
    st.markdown(_region_cards(cells, steps), unsafe_allow_html=True)
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
    "Japan, Australia and New Zealand": ("#FAF0E0", "#6B4A12"),
}
REGION_SHORT = {
    "North America": "N. America",
    "Western Europe": "W. Europe",
    "High-growth markets": "High-growth",
    "Japan, Australia and New Zealand": "JP / ANZ",
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
        height=330,
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
        ("Tariffs", "tariff_score_1_5"),
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
            f"<td style='text-align:center;font-weight:700;color:{idx_col}'>{idx:.1f}</td></tr>"
        )
    return (
        "<table style='width:100%;border-collapse:collapse;font-size:10.5px'>"
        "<tr style='font-size:9px;color:#6B7A88;text-transform:uppercase'>"
        "<th style='text-align:left'>Country</th>"
        + head
        + "<th style='text-align:center'>Trade openness index 2025</th>"
        "<th style='text-align:center'>Barrier index</th></tr>" + body + "</table>"
    )


def clusters_screen(data=None) -> None:
    """Screen 3 on one page, MVP layout: headline figures, map with hubs and signal tags (left),
    top hubs and entry barrier index (right). Values come from the sheet and the sources they cite;
    anything missing shows as to collect."""
    from src.metrics import clusters as cm

    header(
        "Customer clusters",
        "Where potential buyers are concentrated, how well Cytiva supplies them nearby, "
        "and how hard each market is to enter.",
    )
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
        with col, st.container(border=True):
            st.markdown(
                f"<div class='lb'>{label}</div><div class='big'>{value}</div>"
                f"<div class='rs'>{sub}</div>",
                unsafe_allow_html=True,
            )

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


def demand_screen(data=None) -> None:
    """Screen 4 in the MVP layout, from the research sheet (stored with source URLs).
    Anything the sheet does not give shows as to collect."""
    from src.metrics import demand as dm

    header(
        "Demand drivers",
        "What creates demand for biologics: disease burden, pipeline, approvals, sales, "
        "capacity and policy.",
    )
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
        with col, st.container(border=True):
            st.markdown(
                f"<div class='lb'>{label}</div><div class='big'>{value}</div>"
                f"<div class='rs'>{sub}</div>",
                unsafe_allow_html=True,
            )

    left, mid, right = st.columns([1.1, 1, 1.1], gap="small")
    with left:
        with st.container(border=True):
            section("Top 10 countries by disease burden", "fact")
            st.plotly_chart(
                _burden_map(dm.map_points(data)), width="stretch", config={"displayModeBar": False}
            )
            st.dataframe(
                [
                    {
                        "Country": r["country"],
                        "New cancer cases 2022": r["new_cancer_cases_2022"],
                        "Adults with diabetes, m": r["diabetes_adults_2024_m"],
                        "DALYs, m": r["dalys_2021_m"] or "to collect",
                        "Source": r["cancer_source_url"],
                    }
                    for r in dm.top_burden(data)
                ],
                column_config={"Source": st.column_config.LinkColumn("Source")},
                hide_index=True,
                width="stretch",
            )
            note(
                "Ranked by new cancer cases (GLOBOCAN 2022), one source. Diabetes (IDF 2024) "
                "shown beside it. The map of burden and DALY ranking: to collect (WHO GHE file)."
            )
        with st.container(border=True):
            section("Pipeline by medicine type", "fact")
            bars = ""
            maximum = 2217
            for r in pipe["rows"]:
                if r["medicine_type"].startswith("Gene cell"):
                    continue
                bars += _pct_bar(
                    r["medicine_type"].split(" (")[0], _num_val(r["value"]), maximum, r["value"]
                )
            st.markdown(bars, unsafe_allow_html=True)
            note(
                "Therapies in development, Q2 2026. Monoclonal antibody, bispecific and peptide "
                "counts: to collect."
            )
    with mid:
        with st.container(border=True):
            section("Approvals 2025", "fact")
            st.dataframe(
                [
                    {
                        "Regulator": r["regulator"],
                        "Measure": r["metric"],
                        "2025": r["value"],
                        "Confidence": r["confidence"],
                        "Source": r["source_url"],
                    }
                    for r in data.approvals
                ],
                column_config={"Source": st.column_config.LinkColumn("Source")},
                hide_index=True,
                width="stretch",
            )
        with st.container(border=True):
            section("Biosimilar wave (patent expiries)", "signal")
            st.dataframe(
                [
                    {
                        "Drug": r["drug"],
                        "Owner": r["owner"],
                        "Expiry": r["year"],
                        "Confidence": r["confidence"],
                        "Source": r["source_url"] or "to collect",
                    }
                    for r in data.expiries
                ],
                column_config={"Source": st.column_config.LinkColumn("Source")},
                hide_index=True,
                width="stretch",
            )
            note(
                "Ocrevus 2029 is not in the table: no source yet. Two sources are 2024 articles "
                "and are to be replaced with company filings."
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
            st.dataframe(
                [
                    {
                        "Drug": r["drug"],
                        "Company": r["company"],
                        "Sales, $bn": r["sales_fy2025_usd_bn"],
                        "Type": r["type"],
                        "Made with bioprocess equipment": dm.bioprocess_flag(r["bioprocess_use"]),
                        "Source": r["source_url"],
                    }
                    for r in data.top_drugs
                ],
                column_config={"Source": st.column_config.LinkColumn("Source")},
                hide_index=True,
                width="stretch",
            )
            note(
                "Source: Drug Discovery and Development Pharma 50 (FY2025), a secondary "
                "compilation of company reports. Currency differences noted in the source."
            )
        with st.container(border=True):
            section("Capacity pledges", "signal")
            st.dataframe(
                [
                    {
                        "Company": r["company"],
                        "Pledge, $bn": r["pledge_or_capacity"],
                        "Period": r["period"],
                        "Relevance": r["biologics_relevance"],
                        "Source": r["source_url"],
                    }
                    for r in data.capacity
                    if r["kind"] == "Pledge"
                ],
                column_config={"Source": st.column_config.LinkColumn("Source")},
                hide_index=True,
                width="stretch",
            )
            note("Pledges, not money spent; periods differ and some include R and D.")
        with st.container(border=True):
            section("Cytiva products used, by medicine type", "hyp")
            st.markdown(_product_matrix(data.product_use), unsafe_allow_html=True)
            note(
                "Hypothesis: analyst judgement from general bioprocess knowledge, not a sourced "
                "fact. High = core input; Some = used in part of the process; None = little or "
                "no use. To validate with Cytiva product and commercial teams."
            )
        with st.container(border=True):
            section("Implications for Finance & IT", "hyp")
            hypothesis("Can we report revenue by medicine type?")
            hypothesis("Customer pipeline as demand signal?")


def _product_matrix(rows: list[dict]) -> str:
    cols = [
        ("Resins", "chromatography_resins"),
        ("Filtration", "filtration"),
        ("Single-use", "single_use_bioreactors_bags"),
        ("Media", "cell_culture_media"),
        ("Cell and gene", "cell_gene_therapy_tools"),
    ]
    mark = {"High": "&#9679;", "Some": "&#9675;", "None": "&ndash;"}
    head = "".join(f"<th style='text-align:center'>{c}</th>" for c, _ in cols)
    body = ""
    for r in rows:
        cells = "".join(
            f"<td style='text-align:center;color:#1E4257'>{mark.get(r[k], '&ndash;')}</td>"
            for _, k in cols
        )
        body += f"<tr><td style='font-weight:600'>{r['medicine_type']}</td>{cells}</tr>"
    return (
        "<table style='width:100%;border-collapse:collapse;font-size:10.5px'>"
        "<tr style='font-size:9px;color:#6B7A88;text-transform:uppercase'>"
        f"<th style='text-align:left'>Medicine type</th>{head}</tr>{body}</table>"
    )


def _num_val(text: str | None) -> float | None:
    if text is None or str(text).strip() == "":
        return None
    return float(str(text).replace(",", ""))


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


def technology_screen(
    register: list[dict] | None = None,
    incidents: list[dict] | None = None,
    checked_on: str | None = None,
) -> None:
    header(
        "Technology estate",
        "What is ending, what is exposed, what integrates well, and where adoption is heading.",
    )

    def estate() -> None:
        if register:
            st.markdown(_register_table(register), unsafe_allow_html=True)
            note(
                "Signal · products shown in public case studies and vendor releases; Cytiva has "
                "not confirmed the list. A vendor date is shown only where the vendor states one."
            )
        else:
            placeholder("No estate items loaded yet. Run the refresh. To collect.")

    def window() -> None:
        if checked_on is None:
            placeholder("Not checked yet: the refresh has not completed. To collect.")
            return
        if incidents:
            st.markdown(_incidents_table(incidents), unsafe_allow_html=True)
        else:
            placeholder(
                "No actively exploited vulnerability in the last 30 days for the products in "
                "the register."
            )
        note(
            f"Fact · CISA Known Exploited Vulnerabilities catalogue, rolling 30 days, "
            f"{_format_check(checked_on)}. Vendor advisories and status pages are not yet included."
        )

    _box("End-of-support register", "signal", estate)
    _box("Incidents in the last 30 days", "fact", window)
    _box(
        "Integration readiness",
        "pending",
        _text("API and event-ready, mixed, or legacy (EDI, IDoc, XML, flat files). To collect."),
    )
    _box(
        "Technology adoption signals",
        "signal",
        _text(
            "17 technologies, Strong, Emerging or Early, with evidence. Established and emerging "
            "technologies are shown separately. To collect."
        ),
    )
    _box("Implications for Finance & IT", "hyp", _hyp("Link the estate to finance processes."))


def china_screen() -> None:
    header(
        "China",
        "Selling into China and relying on Chinese vendors. All amounts in USD.",
    )
    _box(
        "China share of Danaher sales",
        "fact",
        _text(
            "China share and growth YoY from Danaher 10-K and results calls. To collect (CD-28)."
        ),
    )
    _box(
        "Local competitor coverage in China",
        "pending",
        _text(
            "Cytiva plus 12 Chinese challengers × 8 product families and 7 steps. "
            "Made, partial, not made, with source per cell. To collect (CD-28)."
        ),
    )
    _box(
        "Chinese challenger financials (USD)",
        "fact",
        _text(
            "Listed challengers from CNINFO filings; CNY converted at the annual average. "
            "To collect."
        ),
    )
    _box(
        "Confirmed Chinese vendors",
        "signal",
        _text(
            "Vendors, what they supply, and to which Danaher company. "
            "Unconfirmed relationships marked 'to confirm'. To collect."
        ),
    )
    _box(
        "Commercial opportunities in China",
        "signal",
        _text("Opportunities to sell, with reason, product lines and evidence label. To collect."),
    )
    _box(
        "Implications for Finance & IT",
        "hyp",
        _hyp(
            "Can Finance track the 80/80 localisation target: China spend by local vendor?",
            "Can we see China margin after local price cuts, by product family?",
        ),
    )
