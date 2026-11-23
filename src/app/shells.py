"""Screens 2 to 6 of the dashboard, laid out as in the MVP design.

These are shells: layout and sections are in place, and each section is marked with its
evidence label. Content that is not loaded yet shows as "to collect" with the research story
that will fill it. No estimate or mockup value is shown as data.

Each section sits in its own white box, as on the Overview.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import replace

import plotly.graph_objects as go
import streamlit as st

from src.app.design import (
    badge_html,
    evidence_badge,
    html_table,
    hypothesis,
    kpi_card,
    note,
    placeholder,
    record_label,
    row_badge,
    row_basis,
    screen_header,
    source_link,
    stored_label_badge,
    tile_box,
    unconfirmed_toggle,
    visible,
)
from src.app.market_tile import market_share_tile
from src.app.ui.components import empty_state, status_chip  # noqa: E402
from src.app.ui.evidence import Evidence, card_footer, evidence_button
from src.domain.china import FAMILY_NAMES
from src.domain.confidence import HYPOTHESIS as HYPOTHESIS_LABEL  # noqa: E402
from src.domain.confidence import UNCONFIRMED  # noqa: E402
from src.domain.coverage_model import (  # noqa: E402
    COMPANIES,
    CYTIVA,
    FAMILIES,
    STEPS,
)
from src.domain.regions import HG, JP, NA, WE  # noqa: E402
from src.domain.tabs import AS_OF_LABEL, DEMAND_LABELS  # noqa: E402
from src.domain.thresholds import (  # noqa: E402
    BARRIER_RED_FROM,
    LOW_BARRIER_BELOW,
    SCORE_AMBER_BELOW,
    SCORE_GREEN_BELOW,
    TARIFF_STEP_HIGH_PCT,
    TARIFF_STEP_LOW_PCT,
)
from src.metrics import china as cm
from src.metrics.coverage import STEP_FAMILIES

STATUS_LEGEND = (
    "Legend: verified present · partial or to confirm · verified absence · not yet researched"
)


# Region colours and short keys for the coverage screen (presentation only). The regions
# themselves, and their order, are the domain's (src/domain/regions.py).
REGION_STYLE = {
    NA: ("r0", "#0F5A3C", "#E3F4EC"),
    WE: ("r1", "#1E3F73", "#E5F0FB"),
    HG: ("r2", "#3D2E7A", "#EEEAF8"),
    JP: ("r3", "#6B4A12", "#FAF0E0"),
}
COVERAGE_REGIONS = [(name, *REGION_STYLE[name]) for name in (NA, WE, HG, JP)]
COVERAGE_COMPANIES = list(COMPANIES)
COVERAGE_FAMILIES = list(FAMILIES)
COVERAGE_STEPS = list(STEPS)
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


def _label(data, key: str) -> str:
    """A display label from the demand README (src/domain/tabs.py DEMAND_LABELS), or to collect."""
    return data.labels.get(DEMAND_LABELS[key]) or "to collect"


def _approvals_title(data) -> str:
    """The approvals tile title, built from the Period values of the approval rows."""
    periods = list(dict.fromkeys(r["period"] for r in data.approvals if r.get("period")))
    return "Approvals, " + " and ".join(periods) if periods else "Approvals"


def _top_title(data) -> str:
    return f"Top 10 countries by {_label(data, 'cancer_measure').lower()}"


def _column_year(column: str) -> str:
    """The year a sheet column is named for: sales_fy2025_usd_bn gives FY2025."""
    match = re.search(r"(fy)?(\d{4})", column, re.IGNORECASE)
    return f"FY{match.group(2)}" if match and match.group(1) else (match.group(2) if match else "")


def _first_title(rows: list[dict]) -> str:
    """The source title stored with the first row that has one (the sheet's Source column)."""
    return next((r["source_title"] for r in rows if r.get("source_title")), "")


def _sales_line(sales: dict | None, region: str) -> str:
    """Biotech sales line on a region card: the period, the figure, its share and the source."""
    row = (sales or {}).get(region)
    if row is None:
        return "Biotech sales: to collect"
    return (
        f"Biotech sales {row['period']}: <a href='{row['source_url']}'>${row['value_m']:,.0f}m</a> "
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
                if cells.get((CYTIVA, region, f), {}).get("status") == "Made"
            )
            manufacturing = [
                cell["status"]
                for (company, reg, step), cell in (steps or {}).items()
                if company == CYTIVA and reg == region and not step.startswith("8.")
            ]
            local = manufacturing.count("Made")
            partial = sum(
                1
                for f in COVERAGE_FAMILIES
                if cells.get((CYTIVA, region, f), {}).get("status") == "Partial"
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


def _region_items(cells, steps, sales) -> list[Evidence]:
    """One drawer row per region card: the Cytiva counts and the sales figure's source."""
    out = []
    for region, *_rest in COVERAGE_REGIONS:
        sale = (sales or {}).get(region) or {}
        if cells is None:
            shown = "to collect"
        else:
            made = sum(
                1
                for f in COVERAGE_FAMILIES
                if cells.get((CYTIVA, region, f), {}).get("status") == "Made"
            )
            local = sum(
                1
                for (company, reg, step), cell in (steps or {}).items()
                if company == CYTIVA
                and reg == region
                and not step.startswith("8.")
                and cell["status"] == "Made"
            )
            shown = f"{made} of 8 families made; {local} of 7 steps local"
        out.append(
            Evidence(
                row=region,
                shown=shown,
                label=row_basis(sale.get("confidence"), sale.get("source_url"))
                if sale
                else "To collect",
                confidence=sale.get("confidence"),
                source_url=sale.get("source_url"),
                source_name="sales source",
            )
        )
    return out


def _footprint_items(cells: dict) -> list[Evidence]:
    """Every grid cell the matrix shows: company, region and family, with its source."""
    return [
        Evidence(
            row=f"{company}, {region}, {family}",
            shown=cell["status"],
            label=row_basis(cell.get("confidence"), cell.get("source_url")),
            confidence=cell.get("confidence"),
            source_url=cell.get("source_url"),
            source_name="grid source",
        )
        for (company, region, family), cell in sorted(cells.items())
    ]


def _steps_items(steps: dict | None) -> list[Evidence]:
    """Every step cell the matrix shows, with its source."""
    return [
        Evidence(
            row=f"{company}, {region}, {step}",
            shown=cell["status"],
            label=row_basis(cell.get("confidence"), cell.get("source_url")),
            confidence=cell.get("confidence"),
            source_url=cell.get("source_url"),
            source_name="step source",
        )
        for (company, region, step), cell in sorted((steps or {}).items())
    ]


def coverage_screen(
    cells: dict | None = None,
    steps: dict | None = None,
    sales: dict | None = None,
    implications: list[dict] | None = None,
) -> None:
    """Screen 2 in the MVP layout: a yellow note; region cards; the two matrices on the left;
    market size and implications on the right. Sections without loaded data show to collect."""
    screen_header(2, "Competitor coverage")
    show_l = unconfirmed_toggle()
    if cells is not None:
        cells = {k: v for k, v in cells.items() if visible(v.get("confidence"), show_l)}
    if steps is not None:
        steps = {k: v for k, v in steps.items() if visible(v.get("confidence"), show_l)}
    st.markdown(_region_cards(cells, steps, sales), unsafe_allow_html=True)
    evidence_button("cov-regions", "Region cards", _region_items(cells, steps, sales))
    note(
        "Each mark links to its public source. A ? is a researched lead that is not yet "
        "confirmed. Where we are ahead or behind peers, and where price power is at risk."
    )
    left, right = st.columns([2.6, 1], gap="small")
    with left:
        with tile_box("Product families made in region"):
            if cells is None:
                placeholder("Not loaded yet: run the refresh. To collect.")
            else:
                st.markdown(
                    f"<div class='covwrap'>{_footprint_matrix(cells)}</div>",
                    unsafe_allow_html=True,
                )
                evidence_button(
                    "cov-footprint",
                    "Product families made in region",
                    _footprint_items(cells),
                )
                st.markdown(_legend(), unsafe_allow_html=True)
        with tile_box("Bioprocess steps supplied from own region"):
            st.markdown(
                f"<div class='covwrap'>{_steps_matrix(steps)}</div>", unsafe_allow_html=True
            )
            evidence_button(
                "cov-steps", "Bioprocess steps supplied from own region", _steps_items(steps)
            )
            st.markdown(_legend(), unsafe_allow_html=True)
            st.markdown(_step_needs(), unsafe_allow_html=True)
    with right:
        with tile_box("Market size and share"):
            market_share_tile()
        with tile_box("Implications for Finance & IT"):
            if implications is None:
                placeholder("Not loaded yet: run the refresh. To collect.")
            for imp in implications or []:
                record_label(HYPOTHESIS_LABEL)
                hypothesis(imp["hypothesis"])
            evidence_button(
                "cov-implications",
                "Implications for Finance & IT",
                [
                    Evidence(row=imp["id"], shown=imp["hypothesis"], label=HYPOTHESIS_LABEL)
                    for imp in implications or []
                ],
            )


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
    if score < SCORE_GREEN_BELOW:
        return "#E6F4EC"
    if score < SCORE_AMBER_BELOW:
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
        body += (
            f"<tr><td>{i}</td><td style='font-weight:600'>{r['hub']}</td>"
            f"<td>{_region_tag(region)}</td>"
            f"<td style='text-align:right;font-weight:700'>{r['count']:,.0f}</td>"
            f"<td>{r['type']} ({r['scope']})</td><td>{r['as_of'] or ''}</td>"
            f"<td>{row_badge(r['confidence'], r['source_url'])}</td></tr>"
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
        "<th style='text-align:left'>Basis</th></tr>" + body + "</table>" + footer
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
        idx_col = "#B23A2C" if idx is not None and idx >= BARRIER_RED_FROM else "#1B2430"
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


def _hub_item(r: dict, title: str) -> Evidence:
    """One hub's density row for the drawer."""
    return Evidence(
        row=f"{r['hub']} ({title})",
        shown=f"{r['count']:,.0f} {r['type']} ({r['scope']})" if r.get("count") else "to collect",
        label=row_basis(r.get("confidence"), r.get("source_url")),
        confidence=r.get("confidence"),
        source_url=r.get("source_url"),
        source_name="density source",
    )


def _signal_items(signals: list[dict]) -> list[Evidence]:
    """One drawer row per end-market signal shown on the tile."""
    return [
        Evidence(
            row=f"{x['geography']}: {x['indicator']} ({x['period']})",
            shown=f"{x['value']:,.0f} {x['unit'] or ''}".strip()
            if x["value"] is not None
            else "n/d",
            label=row_basis(x.get("confidence"), x["source_url"]),
            confidence=x.get("confidence"),
            source_url=x["source_url"],
            source_name="signal source",
        )
        for x in signals
    ]


def clusters_screen(data=None) -> None:
    """Screen 3 on one page, MVP layout: headline figures, map with hubs and signal tags (left),
    top hubs and entry barrier index (right). Values come from the sheet and the sources they cite;
    anything missing shows as to collect."""
    from src.metrics import clusters as cm

    screen_header(3, "Customer clusters")
    show_l = unconfirmed_toggle()
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
    card_rows = [
        [_hub_item(h["densest"], "densest hub")] if h["densest"] else [],
        [_hub_item(h["gap"], "largest hub not supplied locally")] if h["gap"] else [],
        [_hub_item(h["entry"], "densest hub with a low barrier")] if h["entry"] else [],
        _signal_items(cm.directional_signals(data)),
    ]
    for col, (label, value, sub), rows in zip(st.columns(4), cards, card_rows, strict=True):
        with col:
            kpi_card(label, value, sub, footer=card_footer(f"clusters-card-{label}", label, rows))

    st.markdown(
        "<div style='font-size:10px;color:#6B7A88;margin:-4px 0 6px'>Densest = highest density "
        "count (companies, sites, plants or organisations; type shown). Not supplied locally = "
        "Cytiva makes 0 of 7 manufacturing steps in the hub's region (screen 2). Low barrier = "
        f"country barrier index below {LOW_BARRIER_BELOW:.1f}. Rising and falling = end-market "
        "signals that state a "
        "change.</div>",
        unsafe_allow_html=True,
    )
    local = data.local_steps
    left, right = st.columns([1.15, 1], gap="small")
    with left:
        with tile_box("Biotech hubs by density"):
            st.plotly_chart(
                _cluster_map(hubs, local), width="stretch", config={"displayModeBar": False}
            )
            evidence_button(
                "clusters-map",
                "Biotech hubs by density",
                [_hub_item(r, r["hub"]) for r in cm.density_rows(data)],
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
        with tile_box("End-market demand"):
            st.markdown(_signal_tags(cm.directional_signals(data)), unsafe_allow_html=True)
            evidence_button(
                "clusters-demand",
                "End-market demand",
                _signal_items(cm.directional_signals(data)),
            )
            st.markdown(
                "<div style='font-size:10px;color:#6B7A88'>&#9650; green: rising demand or "
                "interest. &#9660; red: falling. Source linked on each tag.</div>",
                unsafe_allow_html=True,
            )
    with right:
        with tile_box("Top hubs by density"):
            st.markdown(_top_hubs_table(cm.density_rows(data), hubs), unsafe_allow_html=True)
            evidence_button(
                "clusters-hubs",
                "Top hubs by density",
                [_hub_item(r, r["hub"]) for r in cm.density_rows(data)],
            )
        with tile_box("Market entry barrier index"):
            countries = [c for c in data.countries if visible(c.get("confidence"), show_l)]
            st.markdown(_barrier_table(countries), unsafe_allow_html=True)
            evidence_button(
                "clusters-barrier",
                "Market entry barrier index",
                [
                    Evidence(
                        row=c["country"],
                        shown=f"barrier index {c['barrier_index']:.1f}"
                        if c["barrier_index"] is not None
                        else "to collect",
                        label=row_basis(c.get("confidence"), c["source_url"]),
                        confidence=c.get("confidence"),
                        source_url=c["source_url"],
                        source_name="barrier source",
                    )
                    for c in countries
                ],
            )
            st.markdown(
                "<div style='font-size:10px;color:#6B7A88;margin-top:4px'>Scores run from 1 (low "
                "barrier) to 5 (high barrier). A dash means not yet assessed. The barrier index "
                f"averages only the scores present. Tariff score: below "
                f"{TARIFF_STEP_LOW_PCT}% = 1, "
                f"{TARIFF_STEP_LOW_PCT}&ndash;{TARIFF_STEP_HIGH_PCT}% = 3, "
                f"{TARIFF_STEP_HIGH_PCT}% and above = 5 (WTO applied rate, 2025). "
                "The trade openness index is "
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
                f"{p['country']}: {p['cases']:,.0f} new cancer cases ({p['year']})" for p in points
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


def _ev(row: str, shown: str, label: str, url: str | None, confidence=None) -> Evidence:
    """One drawer row for the demand screen."""
    return Evidence(
        row=row,
        shown=shown,
        label=label,
        confidence=confidence,
        source_url=url,
        source_name="source",
    )


def demand_screen(data=None) -> None:
    """Screen 4, from the research sheet. Every figure is stored with its source URL.
    Anything the sheet does not give shows as to collect. Each tile's Evidence button lists the
    tile's rows in the drawer; the tables carry only the Basis badge."""
    from src.metrics import demand as dm

    screen_header(4, "Demand drivers")
    if data is None:
        placeholder("Not loaded yet: run the refresh. To collect.")
        return
    show_l = unconfirmed_toggle()

    fda = dm.fda_biologics_2025(data)
    pipe = dm.pipeline_totals(data)
    total_pipe = pipe["total"]
    fda_rows = [
        _ev(
            f"{r['regulator']}, {r['metric']}",
            _cell(r["value"]),
            row_basis(r["confidence"], r["source_url"]),
            r["source_url"],
            r["confidence"],
        )
        for r in data.approvals
        if r["period"] == "2025"
        and (
            r["metric"].startswith("Of which biologics") or r["metric"].startswith("Of which gene")
        )
    ]
    mab_rows = [
        _ev(
            f"{r['drug']}, {r['company']}",
            f"${_num_val(r['sales_fy2025_usd_bn']):,.2f} bn",
            row_basis(r["confidence"], r["source_url"]),
            r["source_url"],
            r["confidence"],
        )
        for r in data.top_drugs
        if r["type"] == "mAb" and _num_val(r["sales_fy2025_usd_bn"]) is not None
    ]
    pipe_period = next((r["period"] for r in data.pipeline if r.get("period")), "")
    pipe_rows = [
        _ev(
            f"{r['medicine_type']}, {r['metric']}",
            _cell(r["value"]),
            row_basis(r["confidence"], r["source_url"]),
            r["source_url"],
            r["confidence"],
        )
        for r in pipe["rows"]
        if visible(r["confidence"], show_l)
    ]
    pledge_rows = [
        _ev(
            f"{r['company']}, {r['period']}",
            f"${_num_val(r['pledge_or_capacity']) or 0:,.1f} bn",
            row_basis(r["confidence"], r["source_url"]),
            r["source_url"],
            r["confidence"],
        )
        for r in data.capacity
        if r["kind"] == "Pledge"
    ]
    cards = (
        (
            f"FDA biologics approved {fda['period']}"
            if fda.get("period")
            else "FDA biologics approved",
            f"{fda['total']}" if fda["total"] is not None else "to collect",
            f"{fda['cder']} CDER biologics + {fda['cber']} CBER gene and cell therapies"
            if fda["total"] is not None
            else "",
            fda_rows,
        ),
        (
            "Top-15 drug sales from mAbs",
            f"${dm.mab_sales_top15(data):,.1f} bn",
            f"{_column_year('sales_fy2025_usd_bn')}, {_first_title(data.top_drugs)}",
            mab_rows,
        ),
        (
            "Gene, cell and RNA therapies in development",
            _num_fmt(total_pipe["value"]) if total_pipe else "to collect",
            f"{pipe_period}, {_first_title(data.pipeline)}",
            pipe_rows,
        ),
        (
            "US manufacturing pledges listed",
            f"${dm.pledges_total(data):,.1f} bn",
            "pledges, not spend",
            pledge_rows,
        ),
    )
    for col, (label, value, sub, rows) in zip(st.columns(4), cards, strict=True):
        with col:
            kpi_card(label, value, sub, footer=card_footer(f"demand-card-{label}", label, rows))

    left, mid, right = st.columns([1.1, 1, 1.1], gap="small")
    with left:
        with tile_box(_top_title(data)):
            st.plotly_chart(
                _burden_map(dm.map_points(data)), width="stretch", config={"displayModeBar": False}
            )
            top = dm.top_burden(data)
            st.markdown(
                html_table(
                    [
                        "Country",
                        f"{_label(data, 'cancer_measure')} {_label(data, 'cancer_period')}",
                        f"{_label(data, 'diabetes_measure')} {_label(data, 'diabetes_period')}",
                        f"{_label(data, 'daly_measure')} {_label(data, 'daly_period')}",
                        "Basis",
                    ],
                    [
                        [
                            r["country"],
                            _cell(r["new_cancer_cases_2024"]),
                            _cell(r["diabetes_adults_2024_m"]),
                            _cell(r["dalys_2021_m"]),
                            row_badge(r["confidence"], r["cancer_2024_source_url"]),
                        ]
                        for r in top
                    ],
                ),
                unsafe_allow_html=True,
            )
            note(
                f"Ranked by {_label(data, 'cancer_measure').lower()} in "
                f"{_label(data, 'cancer_period')} ({_label(data, 'cancer_source')}), one source. "
                f"Diabetes ({_label(data, 'diabetes_source')}) shown beside it. "
                f"DALYs ({_label(data, 'daly_source')}) are to collect."
            )
            evidence_button(
                "demand-burden",
                _top_title(data),
                [
                    _ev(
                        r["country"],
                        f"{_cell(r['new_cancer_cases_2024'])} new cases "
                        f"{_label(data, 'cancer_period')}",
                        row_basis(r["confidence"], r["cancer_2024_source_url"]),
                        r["cancer_2024_source_url"],
                        r["confidence"],
                    )
                    for r in top
                ],
            )
        with tile_box("Pipeline by medicine type"):
            rows = [
                r
                for r in pipe["rows"]
                if visible(r["confidence"], show_l)
                if not r["medicine_type"].startswith("Gene, cell")
            ]
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
            note(
                "Therapies in development, preclinical to pre-registration, "
                f"{_label(data, 'pipeline_period')}. Source: {_label(data, 'pipeline_source')}."
            )
            st.markdown(
                html_table(
                    ["Medicine type", "Measure", "Value", "Period", "Basis"],
                    [
                        [
                            _wrap(r["medicine_type"], 0),
                            _wrap(r["metric"], 0),
                            _cell(r["value"]),
                            r["period"],
                            row_badge(r["confidence"], r["source_url"]),
                        ]
                        for r in dm.other_pipeline(data)
                        if visible(r["confidence"], show_l)
                    ],
                ),
                unsafe_allow_html=True,
            )
            note(
                "Other counts measure different things (approvals, late-stage antibodies, trials, "
                "drugs in R&D). They are not comparable with the bars above."
            )
            evidence_button("demand-pipeline", "Pipeline by medicine type", pipe_rows)
    with mid:
        with tile_box(_approvals_title(data)):
            st.markdown(
                html_table(
                    ["Regulator", "Measure", "Period", "Value", "Basis"],
                    [
                        [
                            r["regulator"],
                            _wrap(r["metric"], 0),
                            r["period"],
                            _cell(r["value"]),
                            row_badge(r["confidence"], r["source_url"]),
                        ]
                        for r in data.approvals
                    ],
                ),
                unsafe_allow_html=True,
            )
            evidence_button(
                "demand-approvals",
                _approvals_title(data),
                [
                    _ev(
                        f"{r['regulator']}, {r['metric']} ({r['period']})",
                        _cell(r["value"]),
                        row_basis(r["confidence"], r["source_url"]),
                        r["source_url"],
                        r["confidence"],
                    )
                    for r in data.approvals
                ],
            )
        with tile_box("Biosimilar wave (patent expiries)"):
            st.markdown(
                html_table(
                    ["Drug", "Owner", "Expiry", "Basis"],
                    [
                        [
                            r["drug"],
                            r["owner"],
                            _cell(r["year"], year=True),
                            row_badge(r["confidence"], r["source_url"]),
                        ]
                        for r in data.expiries
                    ],
                ),
                unsafe_allow_html=True,
            )
            note(_label(data, "biosimilar_note"))
            evidence_button(
                "demand-expiry",
                "Biosimilar wave (patent expiries)",
                [
                    _ev(
                        f"{r['drug']}, {r['owner']} ({r['year']})",
                        r["event"] or "",
                        row_basis(r["confidence"], r["source_url"]),
                        r["source_url"],
                        r["confidence"],
                    )
                    for r in data.expiries
                ],
            )
        with tile_box("Policy and funding"):
            for r in data.policy:
                st.markdown(
                    f"<div style='font-size:10.5px;margin:3px 0'><span style='font-weight:700'>"
                    f"{r['item']}</span> <span style='color:#6B7A88'>"
                    f"({row_basis(r['confidence'], r['source_url'])}, {r['date']})"
                    f"</span><br>{r['what_it_says']}</div>",
                    unsafe_allow_html=True,
                )
            evidence_button(
                "demand-policy",
                "Policy and funding",
                [
                    _ev(
                        f"{r['item']}, {r['date']}",
                        r["what_it_says"],
                        row_basis(r["confidence"], r["source_url"]),
                        r["source_url"],
                        r["confidence"],
                    )
                    for r in data.policy
                ],
            )
    with right:
        with tile_box("Biggest drugs, FY2025 sales"):
            st.markdown(
                html_table(
                    ["Drug", "Company", "Sales, $bn", "Type", "Made with bioprocess", "Basis"],
                    [
                        [
                            r["drug"],
                            r["company"],
                            _cell(r["sales_fy2025_usd_bn"]),
                            r["type"],
                            dm.bioprocess_flag(r["bioprocess_use"]),
                            row_badge(r["confidence"], r["source_url"]),
                        ]
                        for r in data.top_drugs
                    ],
                ),
                unsafe_allow_html=True,
            )
            note(
                f"Source: {_first_title(data.top_drugs)} ({_column_year('sales_fy2025_usd_bn')}). "
                "Currency differences noted in the source."
            )
            evidence_button(
                "demand-drugs",
                "Biggest drugs, FY2025 sales",
                [
                    _ev(
                        f"{r['drug']}, {r['company']}",
                        f"{_cell(r['sales_fy2025_usd_bn'])} $bn",
                        row_basis(r["confidence"], r["source_url"]),
                        r["source_url"],
                        r["confidence"],
                    )
                    for r in data.top_drugs
                ],
            )
        with tile_box("Capacity pledges"):
            st.markdown(
                html_table(
                    ["Company", "Pledge, $bn", "Period", "Relevance", "Basis"],
                    [
                        [
                            r["company"],
                            _cell(r["pledge_or_capacity"]),
                            r["period"],
                            _wrap(r["biologics_relevance"], 0),
                            row_badge(r["confidence"], r["source_url"]),
                        ]
                        for r in data.capacity
                        if r["kind"] == "Pledge"
                    ],
                ),
                unsafe_allow_html=True,
            )
            note("Pledges, not money spent; periods differ and some include R and D.")
            evidence_button("demand-pledges", "Capacity pledges", pledge_rows)
        with tile_box("Cytiva products used, by medicine type"):
            note("Inferred, to test.")
            placeholder(
                f"{len(data.product_use)} rows awaiting confirmation. Hidden by default: "
                "analyst judgement, no source."
            )
            note(
                "High = core input; Some = used in part of the process; None = little or no use. "
                "To validate with Cytiva product and commercial teams."
            )
            evidence_button(
                "demand-product-use",
                "Cytiva products used, by medicine type",
                [
                    Evidence(
                        row=r["medicine_type"],
                        shown=(
                            f"resins {r['chromatography_resins']}, filtration {r['filtration']}, "
                            f"single-use {r['single_use_bioreactors_bags']}, media "
                            f"{r['cell_culture_media']}, cell and gene "
                            f"{r['cell_gene_therapy_tools']}"
                        ),
                        label="Hypothesis",
                        confidence=r["confidence"],
                    )
                    for r in data.product_use
                ],
            )
        with tile_box("Implications for Finance & IT"):
            for r in data.implications:
                hypothesis(f"{r['hypothesis']} ({r['area']})")
            evidence_button(
                "demand-implications",
                "Implications for Finance & IT",
                [
                    Evidence(
                        row=f"{r['id']} ({r['area']})",
                        shown=r["hypothesis"],
                        label="Hypothesis",
                        confidence=r["confidence"],
                    )
                    for r in data.implications
                ],
            )


def _num_val(text: str | None) -> float | None:
    """A sheet number as a float; "NA", "n/d" and blanks are None (to collect)."""
    if text is None or str(text).strip() in ("", "NA", "n/d"):
        return None
    return float(str(text).replace(",", "").replace("%", ""))


def _num_fmt(value: str | None) -> str:
    v = _num_val(value)
    return "to collect" if v is None else f"{v:,.0f}"


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


# Colour keys for the technology tables: confidence (H, M, L), relevance (High, Medium, Low).
_HEAT = {
    "H": ("#E6F4EC", "#1E6B45"),
    "M": ("#FFF4D6", "#7A5A00"),
    "L": ("#EEF1F4", "#6B7A88"),
    "High": ("#FBEAEA", "#B23A2C"),
    "Medium": ("#FFF4D6", "#7A5A00"),
    "Low": ("#EEF1F4", "#6B7A88"),
}


def _first_source(data, row_type: str, row_id: str) -> str:
    """The public link of a row's first source, or a dash."""
    from src.metrics import technology as tm

    found = tm.sources_for(data, row_type, row_id)
    return source_link(found[0]["url"]) if found else "&ndash;"


def _integration_heatmap(data, show_l: bool = False) -> str:
    """Systems against readiness groups. A filled cell means the system sits in that group; its
    colour is the confidence of the grouping."""
    from src.metrics import technology as tm

    groups = tm.integration_groups(data)
    systems: dict[str, dict] = {}
    for g in groups:
        for m in g["members"]:
            if not visible(m["confidence"], show_l):
                continue  # L rows stay hidden unless the screen toggle is on
            row_basis(m["confidence"], _first_url(data, "tech_integrations", m["id"]))
            entry = systems.setdefault(
                m["system"], {"id": m["id"], "interfaces": m["interfaces_available"], "cells": {}}
            )
            entry["cells"][g["key"]] = m["confidence"]
    heads = ["System", *[g["title"] for g in groups], "Interfaces"]
    rows = []
    for name, entry in systems.items():
        cells = [
            _conf_chip(entry["cells"][g["key"]]) if g["key"] in entry["cells"] else ""
            for g in groups
        ]
        rows.append(
            [
                f"<b>{name}</b>",
                *cells,
                _wrap(entry["interfaces"] or "&ndash;"),
            ]
        )
    return html_table(heads, rows)


def _first_url(data, table: str, row_id: str) -> str | None:
    """The first public source of a row, from the tile's source table (None when it has none)."""
    from src.metrics import technology as tm

    found = tm.sources_for(data, table, row_id)
    return found[0]["url"] if found else None


def _eos_items(data, rows: list[dict]) -> list[Evidence]:
    return [
        Evidence(
            row=r["product"],
            shown=f"{r['status_text'] or 'n/d'} {r.get('milestone_date_text') or ''}".strip(),
            label="Fact",
            confidence=r["confidence"],
            source_url=_first_url(data, "tech_eos", r["id"]),
            source_name="vendor source",
        )
        for r in rows
    ]


def _integration_items(data) -> list[Evidence]:
    from src.metrics import technology as tm

    out = []
    for g in tm.integration_groups(data):
        for m in g["members"]:
            out.append(
                Evidence(
                    row=f"{m['system']}, {g['title']}",
                    shown=m["interfaces_available"] or "n/d",
                    label="Hypothesis",
                    confidence=m["confidence"],
                    source_url=_first_url(data, "tech_integrations", m["id"]),
                    source_name="interface source",
                )
            )
    return out


def _exposure_items(data, rows: list[dict]) -> list[Evidence]:
    return [
        Evidence(
            row=f"{r.get('app') or r['product'] or 'n/d'}, {r['vendor'] or 'n/d'}",
            shown=f"{r['type'] or 'n/d'}, {r['date_value'] or 'n/d'}, {_fixed_status(r)}",
            label="Signal",
            confidence=r.get("scope_confidence"),
            source_url=_first_url(data, "tech_incidents", r["id"]),
            source_name="security source",
        )
        for r in rows
    ]


def _adoption_items(data, rows: list[dict]) -> list[Evidence]:
    return [
        Evidence(
            row=r["technology"],
            shown=f"{r['level']}: {r['signal'] or ''}",
            label="Fact",
            source_url=_first_url(data, "tech_adoption", r["id"]),
            source_name="example source",
        )
        for r in rows
    ]


def _implication_items(rows: list[dict]) -> list[Evidence]:
    return [
        Evidence(
            row=r["id"],
            shown=r["hypothesis"],
            label="Hypothesis",
            confidence=r["confidence"],
        )
        for r in rows
    ]


def _conf_chip(confidence: str | None) -> str:
    """A confidence chip. L is the UNCONFIRMED badge (shown only when the screen toggle is on)."""
    if confidence == "L":
        return badge_html(UNCONFIRMED)
    bg, fg = _HEAT.get(confidence, _HEAT["L"])
    return status_chip(confidence, bg, fg)


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
        basis = row_badge(r.get("scope_confidence"), _first_url(data, "tech_incidents", r["id"]))
        out.append(
            [
                (r.get("app") or r["product"] or "n/d") + tag + " " + basis,
                r["vendor"] or "n/d",
                r["date_value"] or "n/d",
                nature,
                _fixed_status(r),
            ]
        )
    return html_table(["Product", "Vendor", "Date", "Nature of failure", "Fixed or not"], out)


def _adoption_table(data, rows: list[dict]) -> str:
    """Technology first, then the adoption level, then the example. Its source is in the drawer."""

    out = []
    for r in rows:
        bg, fg = _LEVEL_COLOUR.get(r["level"], _LEVEL_COLOUR["No public signal"])
        example = r["signal"] or ""
        date_text = r["signal_date_text"] or ""
        out.append(
            [
                f"<b>{r['technology']}</b>",
                status_chip(r["level"], bg, fg),
                f"<div style='white-space:normal;min-width:260px'>{example} "
                f"<span class='t-meta'>{date_text}</span> "
                f"{row_badge(r['confidence'], r['source_url'])}</div>",
            ]
        )
    return html_table(["Technology", "Adoption", "Example"], out)


def _vendor_to(text: str | None) -> str:
    """Cytiva when only Cytiva is named as the buyer; otherwise Danaher."""
    names = [n.strip() for n in re.split(r"[;,]", text or "") if n.strip()]
    if len(names) == 1 and names[0].startswith(CYTIVA):
        return CYTIVA
    return "Danaher" if names else "n/d"


def _wrap(text: str, min_width: int = 150) -> str:
    """Long text wraps inside its table column instead of stretching the tile. A min_width of 0
    lets the column shrink, for tables that must fit their card."""
    return f"<div style='white-space:normal;min-width:{min_width}px'>{text}</div>"


def _implications_table(rows: list[dict]) -> str:
    """Hypotheses with their confidence. The text wraps inside the Hypothesis column."""
    body = [
        [
            f"<div style='white-space:normal;min-width:240px'>{r['hypothesis']}</div>",
            badge_html("Hypothesis"),
        ]
        for r in rows
    ]
    return html_table(["Hypothesis", "Basis"], body)


# Applications on the End of support tile, with the end-of-support row they match (if any).


def _eos_table(data, rows: list[dict]) -> str:
    """Tile 1: application, and the support milestone with its status colour, the tile note
    under the date, and the confidence badge. Source link in the drawer."""
    out = []
    for r in rows:
        bg, fg = _EOS_COLOUR[r["colour"]]
        note = f"<div class='t-meta'>{r['tile_note']}</div>" if r.get("tile_note") else ""
        milestone = (
            status_chip(r["status_text"] or "&ndash;", bg, fg)
            + " "
            + row_badge(r["confidence"], _first_url(data, "tech_eos", r["id"]))
            + note
        )
        if r.get("application"):
            first = f"<b>{r['application']}</b><div class='t-meta'>{r['product']}</div>"
        else:
            first = f"<b>{r['product']}</b>"  # no application listed in the sheet (EOS-04)
        out.append([first, milestone])
    return html_table(["Application", "End of support"], out)


def technology_screen(data=None, today=None) -> None:
    """Screen 5 (MVP layout): five tiles. Clicking a row (or a chip) opens its evidence."""
    from datetime import date as _date

    from src.metrics import technology as tm

    today = today or _date.today()
    screen_header(5, "Technology estate")
    show_l = unconfirmed_toggle()
    if data is None:
        placeholder("Not loaded yet: run the refresh. To collect.")
        return
    readme = next((n["text"] for n in data.notes if n["label"] == AS_OF_LABEL), "")
    st.markdown(
        f"<div class='t-body'>Data as of {readme}. Public sources; "
        "every value links to its evidence.</div>",
        unsafe_allow_html=True,
    )

    left, right = st.columns([1.1, 1], gap="small")
    with left:
        with tile_box("End of support"):
            rows = [r for r in tm.eos_tile_rows(data, today) if visible(r["confidence"], show_l)]
            if not rows:
                empty_state("No items to show.")
            else:
                st.markdown(_eos_table(data, rows), unsafe_allow_html=True)
            evidence_button("tech-eos", "End of support", _eos_items(data, rows))
        with tile_box("Integration readiness"):
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
            st.markdown(_integration_heatmap(data, show_l), unsafe_allow_html=True)
            evidence_button("tech-integration", "Integration readiness", _integration_items(data))
        with tile_box("Implications for Finance & IT"):
            implications = [
                r for r in tm.implication_rows(data) if visible(r["confidence"], show_l)
            ]
            st.markdown(_implications_table(implications), unsafe_allow_html=True)
            evidence_button(
                "tech-implications",
                "Implications for Finance & IT",
                _implication_items(implications),
            )
    with right:
        with tile_box("Security issues in apps we use · last 30 days"):
            exp = tm.exposure(data, today)
            st.markdown(
                f"<div class='t-meta'>{exp['window']}</div>",
                unsafe_allow_html=True,
            )
            rows = exp["shown"] + (exp["unconfirmed"] if show_l else [])
            if rows:
                st.markdown(_exposure_table(data, rows), unsafe_allow_html=True)
            else:
                st.markdown(
                    f"<div class='t-strong'>{tm.PENDING_EMPTY}</div>", unsafe_allow_html=True
                )
            evidence_button(
                "tech-security", "Security issues, last 30 days", _exposure_items(data, rows)
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
        with tile_box("Technology adoption signals"):
            adoption = [r for r in tm.adoption_rows(data) if visible(r["confidence"], show_l)]
            st.markdown(_adoption_table(data, adoption), unsafe_allow_html=True)
            evidence_button(
                "tech-adoption",
                "Technology adoption signals",
                _adoption_items(data, tm.adoption_rows(data)),
            )


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


def _cn_card(
    data, row: dict | None, title: str, big: str, small: str, items: list[Evidence]
) -> None:
    """A headline card on the shared KPI card: the basis badge sits in the line under the value,
    and the Evidence link at the bottom of the card."""
    footer = card_footer(f"cn-card-{title}", title, items)
    if row is None:
        kpi_card(title, "to collect", footer=footer)
        return
    kpi_card(
        title,
        big,
        f"{small} · {row_badge(row['confidence'], row['source_url'])} · {row['period'] or ''}",
        footer=footer,
    )


def _cn_num(value: float | None, fmt: str) -> str:
    return "n/d" if value is None else fmt.format(value)


def _fin_name(r: dict) -> str:
    """Short company name for the financials table: the division is named in brackets."""
    name, _, division = r["company"].partition(":")
    name = name.strip()
    if division.strip():
        # the division's first word, for example "Tofflon: bioprocess equipment ..." gives
        # "Tofflon (bioprocess)"
        return f"{name} ({division.split()[0]})"
    return name


def _cn_company(row: dict) -> str:
    name = row["name_en"]
    if row.get("products_checked") == "no":
        name += " <span class='cn-note'>(products not checked)</span>"
    return f"<b>{name}</b>" if row["company_id"] == "C00" else name


def _headline_items(h: dict | None) -> list[Evidence]:
    """The headline figure's row for the drawer (To collect when the sheet has no figure)."""
    if h is None:
        return [Evidence(row="headline figure", shown="to collect", label="To collect")]
    return [
        Evidence(
            row=h.get("metric") or h["id"],
            shown=f"{h['value_num']:g}" if h.get("value_num") is not None else str(h.get("value")),
            label=row_basis(h.get("confidence"), h.get("source_url")),
            confidence=h.get("confidence"),
            source_url=h.get("source_url"),
            source_name="headline source",
        )
    ]


def _china_coverage_items(data: cm.ChinaData) -> list[Evidence]:
    """Every family and step cell the coverage matrix shows, with its source."""
    names = {co["company_id"]: co["name_en"] for co in data.companies}
    items = [
        Evidence(
            row=f"{names.get(co, co)}, {FAMILY_NAMES.get(code, code)}",
            shown=cell["status"],
            label=row_basis(cell.get("confidence"), cell.get("source_url")),
            confidence=cell.get("confidence"),
            source_url=cell.get("source_url"),
            source_name="coverage source",
        )
        for (co, code), cell in data.coverage.items()
    ]
    items += [
        Evidence(
            row=f"{names.get(co, co)}, {step}",
            shown=cell["status"],
            label=row_basis(cell.get("confidence"), cell.get("source_url")),
            confidence=cell.get("confidence"),
            source_url=cell.get("source_url"),
            source_name="step source",
        )
        for (co, _region, step), cell in data.steps.items()
    ]
    return items


def _china_visible(data: cm.ChinaData, show_l: bool) -> cm.ChinaData:
    """The China data with L rows removed unless the screen toggle is on. Hidden L cells read as
    not found (?), as a cell with no row does."""

    def keep(r: dict) -> bool:
        return visible(r.get("confidence"), show_l)

    return replace(
        data,
        financials=[r for r in data.financials if keep(r)],
        vendors=[r for r in data.vendors if keep(r)],
        opportunities=[r for r in data.opportunities if keep(r)],
        implications=[r for r in data.implications if keep(r)],
        coverage={k: v for k, v in data.coverage.items() if keep(v)},
        steps={k: v for k, v in data.steps.items() if keep(v)},
    )


def china_screen(data: cm.ChinaData | None = None) -> None:
    screen_header(6, "China")
    show_l = unconfirmed_toggle()
    note("Selling into China and relying on Chinese vendors. All amounts in USD.")
    st.markdown(_CN_CSS, unsafe_allow_html=True)
    if data is None:
        with tile_box("China data"):
            placeholder("To collect. The China research sheet has not been loaded yet.")
        return
    data = _china_visible(data, show_l)

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
            f"of Danaher's continuing-operations sales, {h1['period']}"
            if h1 and h1.get("period")
            else "of Danaher's continuing-operations sales",
            _headline_items(h1),
        )
    with card2:
        _cn_card(
            data,
            h4,
            "China sales growth",
            "" if h4 is None else f"+{h4['value_num']:g}%",
            "China core sales growth year on year, latest quarter",
            _headline_items(h4),
        )
    with basis, tile_box("Basis of the figures"):
        st.markdown(
            f"<div class='t-meta'>RMB converted at {data.fx_rate:g} RMB per USD, an assumption "
            "until the annual average is loaded. "
            f"{cm.basis_sentence(data)}"
            "Growth shown is the latest reported quarter; no "
            "full-year China growth is disclosed.</div>",
            unsafe_allow_html=True,
        )
        evidence_button(
            "cn-basis",
            "Basis of the figures",
            [
                Evidence(
                    row="RMB per USD (conversion rate)",
                    shown=f"{data.fx_rate:g}",
                    label=record_label(HYPOTHESIS_LABEL),
                    source_name="assumption",
                )
            ],
        )

    # Row 2: financials (tile 3) and vendors (tile 4), side by side.
    fin_col, ven_col = st.columns(2, gap="small")
    with fin_col, tile_box("Chinese challenger financials (USD)"):
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
        evidence_button(
            "cn-financials",
            "Chinese challenger financials (USD)",
            [
                Evidence(
                    row=f"{_fin_name(r)}, {r['period'] or 'n/d'}",
                    shown=f"revenue {r['revenue_usd_m_shown']:,.0f} $m"
                    if r["revenue_usd_m_shown"] is not None
                    else "revenue n/d",
                    label=row_basis(r["confidence"], r["source_url"]),
                    confidence=r["confidence"],
                    source_url=r["source_url"],
                    source_name="financial source",
                )
                for r in cm.financial_rows(data)
            ],
        )
    with ven_col, tile_box("Chinese vendors to Danaher companies"):
        vendor_rows = [
            [
                f"{v['vendor_en']}<br><span class='cn-note'>{v['vendor_cn'] or ''}</span>",
                _wrap(v["supplies"] or "n/d"),
                _vendor_to(v["to_danaher_company"]),
                _wrap(v["relationship"] or "n/d"),
                cm.badge(data, v["confidence"], v["source_note"], v["source_url"]),
            ]
            for v in data.vendors
        ]
        st.markdown(
            _cn_html(
                ["Vendor", "Supplies", "To Danaher company", "Relationship", "Label"],
                vendor_rows,
            ),
            unsafe_allow_html=True,
        )
        evidence_button(
            "cn-vendors",
            "Chinese vendors to Danaher companies",
            [
                Evidence(
                    row=f"{v['vendor_en']}, {_vendor_to(v['to_danaher_company'])}",
                    shown=v["supplies"] or "n/d",
                    label=row_basis(v["confidence"], v["source_url"]),
                    confidence=v["confidence"],
                    source_url=v["source_url"],
                    source_name="vendor source",
                )
                for v in data.vendors
            ],
        )

    # Row 3: coverage matrices, full width (screen 2 rule).
    with tile_box("Local competitor coverage in China"):
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
        evidence_button(
            "cn-coverage",
            "Local competitor coverage in China",
            _china_coverage_items(data),
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
    with opp_col, tile_box("Commercial opportunities in China"):
        opp_rows = [
            [
                _wrap(o["opportunity"], 0),
                _wrap(o["why"] or "n/d", 0),
                _wrap(o["product_lines"] or "n/d", 0),
                stored_label_badge(HYPOTHESIS_LABEL)
                if o["evidence_label"] == "Hypothesis"
                else cm.badge(data, o["confidence"], o["source_note"], o["source_url"]),
            ]
            for o in data.opportunities
        ]
        st.markdown(
            _cn_html(["Opportunity", "Why", "Product lines", "Label"], opp_rows),
            unsafe_allow_html=True,
        )
        evidence_button(
            "cn-opportunities",
            "Commercial opportunities in China",
            [
                Evidence(
                    row=o["opportunity"],
                    shown=o["why"] or "n/d",
                    label=row_basis(o["confidence"], o["source_url"]),
                    confidence=o["confidence"],
                    source_url=o["source_url"],
                    source_name="opportunity source",
                )
                for o in data.opportunities
            ],
        )
    with imp_col, tile_box("Implications for Finance & IT"):
        for imp in data.implications:
            record_label(HYPOTHESIS_LABEL)
            hypothesis(imp["hypothesis"])
            st.markdown(
                f"<div class='cn-note'>Confirm or refute: {imp['confirm_or_refute'] or 'n/d'} · "
                f"Area: {imp['area'] or 'n/d'}</div>",
                unsafe_allow_html=True,
            )
        evidence_button(
            "cn-implications",
            "Implications for Finance & IT",
            [
                Evidence(row=imp["id"], shown=imp["hypothesis"], label=HYPOTHESIS_LABEL)
                for imp in data.implications
            ],
        )
