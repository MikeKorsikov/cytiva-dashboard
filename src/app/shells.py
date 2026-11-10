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


def clusters_screen(data=None) -> None:
    """Screen 3 in the MVP layout. Figures come from the research sheet (stored with source URLs);
    anything the sheet does not give shows as to collect."""
    from src.metrics import clusters as cm

    header(
        "Customer clusters",
        "Where potential buyers are concentrated, how well Cytiva supplies them nearby, "
        "and how hard each market is to enter.",
    )
    st.markdown(
        "<div class='banner'>Data: research sheet \"Screen 3 - Customer clusters data\", public "
        "sources, each figure linked. To collect = not yet in the sheet.</div>",
        unsafe_allow_html=True,
    )
    if data is None:
        placeholder("Not loaded yet: run the refresh. To collect.")
        return
    k = cm.kpis(data)
    largest = k["largest_cluster"]
    kpi_cards = (
        (
            "Biologics CDMO sites listed",
            f"{k['cdmo_sites']}",
            f"partial list; capacity given for {k['cdmo_sites_with_capacity']}",
        ),
        ("Sites near strong local supply", "to collect", "needs site-level data"),
        ("Clusters with sourced facts", f"{k['clusters_with_facts']}", "hubs in the sheet"),
        (
            "Largest cluster by capacity",
            largest["cluster"] if largest else "to collect",
            f"{largest['value']:,.0f} L, {largest['as_of']}" if largest else "",
        ),
    )
    for col, (label, value, sub) in zip(st.columns(4), kpi_cards, strict=True):
        with col, st.container(border=True):
            st.markdown(f"<div class='lb'>{label}</div>", unsafe_allow_html=True)
            st.markdown(
                f"<div class='big'>{value}</div><div class='rs'>{sub}</div>", unsafe_allow_html=True
            )

    left, right = st.columns([1, 1], gap="small")
    with left:
        with st.container(border=True):
            section("Demand by country", "signal")
            countries = data.countries
            fig = go.Figure(
                go.Bar(
                    x=[c["demand_score"] for c in countries][::-1],
                    y=[c["country"] for c in countries][::-1],
                    orientation="h",
                    marker={"color": "#1E3F73"},
                    hovertemplate="%{y}: %{x:.2f}<extra></extra>",
                )
            )
            fig.update_layout(
                xaxis={"title": "Demand score (0 to 1)", "range": [0, 1]},
                margin={"l": 10, "r": 10, "t": 10, "b": 40},
                height=520,
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig, use_container_width=True)
            note(
                "Average of the available norms: Nature Index, FDA drug sites, trial "
                "registrations, CDMO sites. Cluster map: to collect (site coordinates needed)."
            )
        with st.container(border=True):
            section("End-market demand", "signal")
            st.dataframe(
                [
                    {
                        "Geography": sig["geography"],
                        "Indicator": sig["indicator"],
                        "Value": sig["value"],
                        "Unit": sig["unit"],
                        "Period": sig["period"],
                        "Source": sig["source_url"],
                    }
                    for sig in data.signals
                ],
                column_config={"Source": st.column_config.LinkColumn("Source")},
                hide_index=True,
                use_container_width=True,
            )
        with st.container(border=True):
            section("Implications for Finance & IT", "hyp")
            hypothesis(
                "For a new regional site, can Finance assess capex, tax and legal-entity set-up?"
            )
            hypothesis(
                "Where barriers are high, can Finance model local entity, duty and registration "
                "costs?"
            )
    with right:
        with st.container(border=True):
            section("Top clusters", "fact")
            st.dataframe(
                [
                    {
                        "Cluster": c["cluster"],
                        "Country": c["country"],
                        "Headline fact": (
                            f"{c['metric']}: {c['value']:,.0f} {c['unit'] or ''}".strip()
                        ),
                        "As of": c["as_of"],
                        "Confidence": c["confidence"],
                        "Source": c["source_url"],
                    }
                    for c in cm.cluster_table(data)
                ],
                column_config={"Source": st.column_config.LinkColumn("Source")},
                hide_index=True,
                use_container_width=True,
            )
            note(
                "Not ranked: the sheet has no metric common to all clusters. Sites and local steps "
                "per cluster: to collect."
            )
        with st.container(border=True):
            section("Market entry barrier index", "hyp")
            st.dataframe(
                [
                    {
                        "Country": c["country"],
                        "Index (1 low, 3 high)": c["barrier_index"],
                        "Scores (of 5)": c["barrier_scores_available"],
                        "Customs (1-5)": c["customs_friction_1_5"],
                        "Local preference (1-5)": c["local_preference_1_5"],
                        "Confidence": c["barrier_confidence"],
                    }
                    for c in cm.barrier_table(data)
                ],
                hide_index=True,
                use_container_width=True,
            )
            note(
                "Averages the scores present; blank is not assessed, not zero. Tariffs (WITS) not "
                "yet pulled; regulatory and geopolitical scores mostly to collect."
            )


def demand_screen() -> None:
    header(
        "Demand drivers",
        "What creates demand for medicines made with Cytiva-type equipment.",
    )
    _box(
        "Disease burden by country",
        "fact",
        _text("DALYs by country and trend. Sources: IHME GBD, WHO GHO. To collect."),
    )
    _box(
        "Top 10 countries by burden",
        "fact",
        _text("Rank, DALYs, cancer cases, diabetes, trials, Cytiva supply status. To collect."),
    )
    _box(
        "Pipeline by medicine type",
        "fact",
        _text("Active trials by type and year-on-year change, ClinicalTrials.gov. To collect."),
    )
    _box(
        "Trial sponsors by region",
        "fact",
        _text("Sponsor region of active trials. ClinicalTrials.gov. To collect."),
    )
    _box(
        "Approvals and patent expiries",
        "fact",
        _text("Novel approvals per year (FDA, EMA, NMPA); key patent expiry years. To collect."),
    )
    _box(
        "Policy and funding",
        "signal",
        _text("IRA, BIOSECURE, most-favoured-nation pricing, biotech funding. To collect."),
    )
    _box(
        "Biggest drugs by sales",
        "fact",
        _text("Largest medicines by FY2025 sales and type, from company reports. To collect."),
    )
    _box(
        "Manufacturing capacity announcements",
        "signal",
        _text("Announced investment, location and status from company releases. To collect."),
    )
    _box(
        "Cytiva product mapping by medicine type",
        "hyp",
        _text("Medicine type × product line, level high or some. Mapping is a hypothesis."),
    )
    _box(
        "Implications for Finance & IT",
        "hyp",
        _hyp("Ask whether revenue can be reported by medicine type and customer pipeline stage."),
    )


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
