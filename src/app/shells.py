"""Screens 2 to 6 of the dashboard, laid out as in the Miro design.

These are shells: layout and sections are in place, and each section is marked with its
evidence label. Content that is not loaded yet shows as "to collect" with the research story
that will fill it. No estimate or mockup value is shown as data.
"""

from __future__ import annotations

import streamlit as st

from src.app.design import header, hypothesis, note, placeholder, section

STATUS_LEGEND = (
    "Legend: verified present · partial or to confirm · verified absence · not yet researched"
)


def coverage_screen() -> None:
    header(
        "Competitor coverage by region",
        "Where are we ahead of or behind peers, and where is price power at risk?",
    )
    section("Regional summary (Cytiva)", "fact")
    placeholder(
        "North America · Western Europe · High-growth markets · Japan, Australia and New "
        "Zealand: products made, steps local, Biotechnology sales by region. "
        "Sources: Danaher 10-K site list and 10-Q regional sales. To collect (CD-20)."
    )
    section("Product families made in region", "pending")
    placeholder(
        "8 families × 4 regions × 7 companies (Cytiva plus six peers). "
        "Each cell: made, partial or to confirm, not made, with source link. To collect (CD-20)."
    )
    note(STATUS_LEGEND)
    section("Bioprocess steps supplied from own region", "pending")
    placeholder("8 steps × 4 regions × 7 companies, derived from the product grid. To collect.")
    section("Market size and share", "signal")
    placeholder(
        "Bioprocessing market size (GMI), scope stored with the value; Danaher share as a range. "
        "To collect (CD-21)."
    )
    section("Implications for Finance & IT", "hyp")
    hypothesis("Can Finance see product margin after freight, duties and transfer pricing?")
    hypothesis("Can we analyse price, volume and mix by product and customer?")


def clusters_screen() -> None:
    header(
        "Customer clusters",
        "Where potential buyers are concentrated, how well Cytiva supplies them nearby, "
        "and how hard each market is to enter.",
    )
    section("GMP manufacturing sites: headline figures", "fact")
    placeholder(
        "Sites · clusters · share near strong local supply · priority clusters. To collect (CD-22)."
    )
    section("Cluster map", "fact")
    placeholder(
        "Map of GMP sites by cluster, coloured by Cytiva local supply. Needs geocoded site data "
        "from FDA and EudraGMDP registers. To collect (CD-22)."
    )
    section("End-market demand", "signal")
    placeholder(
        "Direction of demand by drug type. Sources: earnings calls, FDA approvals. To collect."
    )
    section("Top clusters (ranked)", "signal")
    placeholder("Ranked clusters with Defend, Priority or Watch signal (rule-based). To collect.")
    section("Market entry barrier index", "hyp")
    placeholder(
        "Five factors scored 1–3, averaged. Weights and thresholds need owner approval before "
        "any score is shown."
    )
    section("Implications for Finance & IT", "hyp")
    hypothesis("Link expansion to capex, entity, tax and duty set-up.")


def demand_screen() -> None:
    header(
        "Demand drivers",
        "What creates demand for medicines made with Cytiva-type equipment.",
    )
    section("Disease burden by country", "fact")
    placeholder("DALYs by country and trend. Sources: IHME GBD, WHO GHO. To collect.")
    section("Top 10 countries by burden", "fact")
    placeholder("Rank, DALYs, cancer cases, diabetes, trials, Cytiva supply status. To collect.")
    section("Pipeline by medicine type", "fact")
    placeholder("Active trials by type and year-on-year change, ClinicalTrials.gov. To collect.")
    section("Trial sponsors by region", "fact")
    placeholder("Sponsor region of active trials. ClinicalTrials.gov. To collect.")
    section("Approvals and patent expiries", "fact")
    placeholder("Novel approvals per year (FDA, EMA, NMPA); key patent expiry years. To collect.")
    section("Policy and funding", "signal")
    placeholder("IRA, BIOSECURE, most-favoured-nation pricing, biotech funding. To collect.")
    section("Biggest drugs by sales", "fact")
    placeholder("Largest medicines by FY2025 sales and type, from company reports. To collect.")
    section("Manufacturing capacity announcements", "signal")
    placeholder("Announced investment, location and status from company releases. To collect.")
    section("Cytiva product mapping by medicine type", "hyp")
    placeholder("Medicine type × product line, level high or some. Mapping is a hypothesis.")
    section("Implications for Finance & IT", "hyp")
    hypothesis("Ask whether revenue can be reported by medicine type and customer pipeline stage.")


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


def technology_screen(register: list[dict] | None = None) -> None:
    header(
        "Technology estate",
        "What is ending, what is exposed, what integrates well, and where adoption is heading.",
    )
    section("End-of-support register", "signal")
    if register:
        st.markdown(_register_table(register), unsafe_allow_html=True)
        note(
            "Signal · products shown in public case studies and vendor releases; Cytiva has "
            "not confirmed the list. A vendor date is shown only where the vendor states one."
        )
    else:
        placeholder("No estate items loaded yet. Run the refresh. To collect.")
    section("Incidents in the last 30 days", "signal")
    placeholder(
        "Vendor incidents from the CISA KEV catalogue, vendor advisories and status pages. "
        "Rolling 30-day window only. To collect."
    )
    section("Integration readiness", "pending")
    placeholder("API and event-ready, mixed, or legacy (EDI, IDoc, XML, flat files). To collect.")
    section("Technology adoption signals", "signal")
    placeholder(
        "17 technologies, Strong, Emerging or Early, with evidence. Established and emerging "
        "technologies are shown separately. To collect."
    )
    section("Implications for Finance & IT", "hyp")
    hypothesis("Link the estate to finance processes.")


def china_screen() -> None:
    header(
        "China",
        "Selling into China and relying on Chinese vendors. All amounts in USD.",
    )
    section("China share of Danaher sales", "fact")
    placeholder(
        "China share and growth YoY from Danaher 10-K and results calls. To collect (CD-28)."
    )
    section("Local competitor coverage in China", "pending")
    placeholder(
        "Cytiva plus 12 Chinese challengers × 8 product families and 7 steps. "
        "Made, partial, not made, with source per cell. To collect (CD-28)."
    )
    section("Chinese challenger financials (USD)", "fact")
    placeholder(
        "Listed challengers from CNINFO filings; CNY converted at the annual average. To collect."
    )
    section("Confirmed Chinese vendors", "signal")
    placeholder(
        "Vendors, what they supply, and to which Danaher company. "
        "Unconfirmed relationships marked 'to confirm'. To collect."
    )
    section("Commercial opportunities in China", "signal")
    placeholder("Opportunities to sell, with reason, product lines and evidence label. To collect.")
    section("Implications for Finance & IT", "hyp")
    hypothesis("Can Finance track the 80/80 localisation target: China spend by local vendor?")
    hypothesis("Can we see China margin after local price cuts, by product family?")
