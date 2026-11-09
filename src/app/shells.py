"""Screens 2 to 6 of the dashboard, laid out as in the MVP design.

These are shells: layout and sections are in place, and each section is marked with its
evidence label. Content that is not loaded yet shows as "to collect" with the research story
that will fill it. No estimate or mockup value is shown as data.

Each section sits in its own white box, as on the Overview.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

import streamlit as st

from src.app.design import header, hypothesis, note, placeholder, section

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
_MARK = {
    "Made": "<span class='good'>&#10003;</span>",
    "Partial": "<span class='partial'>&#9680;</span>",
    "Not made": "<span class='weak'>&#215;</span>",
}


def _footprint_matrix(cells: dict) -> str:
    """Families by region: one column per company, as on the MVP screen."""
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
        "<tr><th>Product family</th>"
        + "".join(
            f"<th class='n'>{short}</th>"
            for _ in COVERAGE_REGIONS
            for _, short in COVERAGE_COMPANIES
        )
        + "</tr>"
    )
    body = ""
    for family in COVERAGE_FAMILIES:
        cells_html = ""
        for region, _, _, _ in COVERAGE_REGIONS:
            for company, _ in COVERAGE_COMPANIES:
                cell = cells.get((company, region, family))
                mark = _MARK.get(cell["status"], "?") if cell else "<span class='tc'>?</span>"
                cells_html += f"<td class='n'>{mark}</td>"
        body += f"<tr><td>{family}</td>{cells_html}</tr>"
    return f"<table class='c cov'>{top}{sub}{body}</table>"


def coverage_screen(cells: dict | None = None) -> None:
    header(
        "Competitor coverage by region",
        "Where are we ahead of or behind peers, and where is price power at risk?",
    )
    _box(
        "Regional summary (Cytiva)",
        "fact",
        _text(
            "North America · Western Europe · High-growth markets · Japan, Australia and New "
            "Zealand: products made, steps local, Biotechnology sales by region. "
            "Sources: Cytiva site list (company releases, June 2025); Danaher 10-Q regional "
            "sales. To collect (CD-20)."
        ),
    )

    def matrix() -> None:
        if cells is None:
            placeholder("Not loaded yet: run the refresh. To collect.")
            return
        st.markdown(_footprint_matrix(cells), unsafe_allow_html=True)
        note(
            "Fact · each mark is from a primary source (company site list, annual report or "
            "release), linked in the database. "
            "✓ made · ◐ partial (under build, planned, or products not fully confirmed) · "
            "× not made · ? to collect (not yet researched). Peer cells are sourced where a "
            "2025 filing or release names the site and its product line; the rest are to collect."
        )

    _box("Product families made in region", "fact", matrix)

    def legend() -> None:
        note(STATUS_LEGEND)

    _box("Bioprocess steps supplied from own region", "pending", legend)
    _box(
        "Market size and share",
        "signal",
        _text(
            "Bioprocessing market size (GMI), scope stored with the value; Danaher share as a "
            "range. To collect (CD-21)."
        ),
    )
    _box(
        "Implications for Finance & IT",
        "hyp",
        _hyp(
            "Can Finance see product margin after freight, duties and transfer pricing?",
            "Can we analyse price, volume and mix by product and customer?",
        ),
    )


def clusters_screen() -> None:
    header(
        "Customer clusters",
        "Where potential buyers are concentrated, how well Cytiva supplies them nearby, "
        "and how hard each market is to enter.",
    )
    _box(
        "GMP manufacturing sites: headline figures",
        "fact",
        _text(
            "Sites · clusters · share near strong local supply · priority clusters. "
            "To collect (CD-22)."
        ),
    )
    _box(
        "Cluster map",
        "fact",
        _text(
            "Map of GMP sites by cluster, coloured by Cytiva local supply. Needs geocoded site "
            "data from FDA and EudraGMDP registers. To collect (CD-22)."
        ),
    )
    _box(
        "End-market demand",
        "signal",
        _text(
            "Direction of demand by drug type. Sources: earnings calls, FDA approvals. To collect."
        ),
    )
    _box(
        "Top clusters (ranked)",
        "signal",
        _text("Ranked clusters with Defend, Priority or Watch signal (rule-based). To collect."),
    )
    _box(
        "Market entry barrier index",
        "hyp",
        _text(
            "Five factors scored 1–3, averaged. Weights and thresholds need owner approval before "
            "any score is shown."
        ),
    )
    _box(
        "Implications for Finance & IT",
        "hyp",
        _hyp("Link expansion to capex, entity, tax and duty set-up."),
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
