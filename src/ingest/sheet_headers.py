"""Header maps for the seed sheet exports of screens 2 and 6 (and the register).

Each export is read through its map: a dict of sheet header -> field name used by the loader.
read_sheet() fails loudly when a file has a header the map does not know, or when a mapped header
is missing. A changed header in the sheet therefore stops the load instead of being read silently.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

DATA_ROOT = Path(__file__).resolve().parents[2] / "data"

_CHINA_COMPANIES = {
    "ID": "ID",
    "Company (EN)": "Company (EN)",
    "Company (CN)": "Company (CN)",
    "Listed?": "Listed?",
    "Exchange code": "Exchange code",
    "Ownership / status": "Ownership / status",
    "Main business": "Main business",
    "Source IDs": "Source IDs",
    "Confidence": "Confidence",
}

HEADER_MAPS: dict[str, dict[str, str]] = {
    "china/sheet/companies.csv": _CHINA_COMPANIES,
    "china/sheet/coverage_evidence.csv": {
        "Evidence ID": "Evidence ID",
        "Company ID": "Company ID",
        "Family": "Family",
        "Status": "Status",
        "Evidence (quote)": "Evidence (quote)",
        "Source IDs": "Source IDs",
        "Source date": "Source date",
        "Confidence": "Confidence",
    },
    "china/sheet/coverage_grid.csv": {
        "ID": "ID",
        "Company": "Company",
        "Med (media)": "Med (media)",
        "SU (single-use)": "SU (single-use)",
        "Res (resins)": "Res (resins)",
        "Filt (filtration)": "Filt (filtration)",
        "Fill (filling)": "Fill (filling)",
        "Gen (genomic)": "Gen (genomic)",
        # The sheet now writes a comma; the loader keys on the older semicolon form.
        "Sys (systems, bioreactors)": "Sys (systems; bioreactors)",
        "Anl (analytical)": "Anl (analytical)",
        "Families evidenced": "Families evidenced",
        "Step 8 service in China": "Step 8 service in China",
    },
    "china/sheet/financials.csv": {
        "ID": "ID",
        "Company ID": "Company ID",
        "Company": "Company",
        "Code": "Code",
        "Period": "Period",
        "Revenue (RMB m)": "Revenue (RMB m)",
        "Revenue YoY %": "Revenue YoY %",
        "Gross margin %": "Gross margin %",
        "R&D / revenue %": "R&D / revenue %",
        "Net profit attrib. (RMB m)": "Net profit attrib. (RMB m)",
        "Revenue (USD bn)": "Revenue (USD bn)",
        "Basis": "Basis",
        "Source IDs": "Source IDs",
        "Confidence": "Confidence",
        "Notes": "Notes",
    },
    "china/sheet/headline.csv": {
        "ID": "ID",
        "Metric": "Metric",
        "Value": "Value",
        "Unit": "Unit",
        "Period": "Period",
        "Show on tile?": "Show on tile?",
        "Evidence (quote)": "Evidence (quote)",
        "Source IDs": "Source IDs",
        "Confidence": "Confidence",
        "Notes": "Notes",
    },
    "china/sheet/implications.csv": {
        "ID": "ID",
        "Hypothesis (not a finding)": "Hypothesis (not a finding)",
        "Based on": "Based on",
        "What would confirm or refute it": "What would confirm or refute it",
        "Area": "Area",
        "Confidence": "Confidence",
    },
    "china/sheet/opportunities.csv": {
        "ID": "ID",
        "Opportunity": "Opportunity",
        "Why (evidence summary)": "Why (evidence summary)",
        "Product lines": "Product lines",
        "Label": "Label",
        "Evidence (quote)": "Evidence (quote)",
        "Source IDs": "Source IDs",
        "Source date": "Source date",
        "Confidence": "Confidence",
    },
    "china/sheet/sources.csv": {
        "ID": "ID",
        "Title": "Title",
        "Publisher": "Publisher",
        "Date": "Date",
        "URL": "URL",
        "Type": "Type",
        "Notes": "Notes",
    },
    "china/sheet/vendors.csv": {
        "ID": "ID",
        "Vendor (EN)": "Vendor (EN)",
        "Vendor (CN)": "Vendor (CN)",
        "Code": "Code",
        "Supplies": "Supplies",
        "To (Danaher company)": "To (Danaher company)",
        "Relationship type": "Relationship type",
        "Evidence (quote)": "Evidence (quote)",
        "Source IDs": "Source IDs",
        "Confidence": "Confidence",
    },
    "technology/sheet/applications.csv": {
        "Name": "name",
        "Vendor": "vendor",
        "Area": "area",
        "Domain": "domain",
        "Business functions using it": "business_functions",
        "Research status": "research_status",
        "Ad mentions (22 Oct 2026)": "ad_mentions_22oct",
        "Likely owner or instance": "owner_instance",
        "L1 processes (hypothesis)": "l1_processes",
        "Lifecycle (assumed)": "lifecycle",
        "Evidence": "evidence",
        "Confidence (H/M/L)": "confidence",
        "Source ID (EA prep Sources tab)": "source_id_ea",
        "EA diagram: core processes enabled (1 application per process)": "ea_core_processes",
        "EA diagram: technology layer (runs on)": "ea_technology_layer",
        "Ad mentions (20 Nov 2026, Cytiva + Danaher Corporate)": "ad_mentions_20nov",
    },
    "clusters/sheet/clusters.csv": {
        "Fact ID": "fact_id",
        "Cluster ID": "cluster_id",
        "Cluster": "cluster",
        "Country": "country",
        "Metric": "metric",
        "Value": "value",
        "Unit": "unit",
        "As of": "as_of",
        "Source": "source_title",
        "URL": "source_url",
        "Confidence": "confidence",
        "Evidence": "evidence",
        "Source ID": "source_id",
    },
    "clusters/sheet/cdmo_sites.csv": {
        "Site ID": "site_id",
        "CDMO": "cdmo",
        "City": "city",
        "Country": "country",
        "Capacity (L)": "capacity_l",
        "Status": "status",
        "As of": "as_of",
        "Source": "source_title",
        "URL": "source_url",
        "Confidence": "confidence",
        "Evidence": "evidence",
    },
    "clusters/sheet/market_signals.csv": {
        "Indicator ID": "indicator_id",
        "Geography": "geography",
        "Indicator": "indicator",
        "Value": "value",
        "Unit": "unit",
        "Customer segment": "customer_segment",
        "Period": "period",
        "Source": "source_title",
        "URL": "source_url",
        "Confidence": "confidence",
        "Evidence": "evidence",
        "Source ID": "source_id",
    },
    "clusters/sheet/country_barriers.csv": {
        "Country": "country",
        "ISO3": "iso3",
        "LPI score 2023": "lpi_score_2023",
        "LPI rank 2023": "lpi_rank_2023",
        "LPI customs score 2023": "lpi_customs_score_2023",
        "LPI customs rank 2023": "lpi_customs_rank_2023",
        "Customs friction (1 low to 5 high)": "customs_friction_1_5",
        "Trade measures (1-5)": "trade_measures_1_5",
        "Trade measures evidence": "trade_measures_evidence",
        "Local preference (1-5)": "local_preference_1_5",
        "Local preference evidence": "local_preference_evidence",
        "Regulatory friction (1-5)": "regulatory_friction_1_5",
        "Regulatory evidence": "regulatory_evidence",
        "Geopolitical risk (1-5)": "geopolitical_risk_1_5",
        "Geopolitical evidence": "geopolitical_evidence",
        "Entry barrier index (average of available scores)": "sheet_barrier_index",
        "Scores available (of 5)": "sheet_scores_available",
        "Confidence": "confidence",
        "Source IDs": "source_ids",
        "Display on tile": "display_on_tile",
    },
    "clusters/sheet/demand_by_country.csv": {
        "Country": "country",
        "Region": "region",
        "Academia and government research: Nature Index Share 2025 (biological sciences, 2026 edition)": "nature_index_share_2025",  # noqa: E501
        "Top-100 research institutions: academia (2026 edition)": "top100_academia",
        "Top-100 research institutions: government labs (2026 edition)": "top100_government",
        "R&D spending, all sectors (GERD, PPP $bn, 2021)": "gerd_ppp_bn_2021",
        "Big pharma and generics: FDA-catalogued drug sites FY2024": "fda_drug_sites_fy2024",
        "Biotech and pharma: share of R&D companies by HQ (2026)": "rd_company_share_2026",
        "Biotech therapeutics companies (Biotechgate)": "biotech_therapeutics_companies",
        "Biotech R&D services companies, incl. CROs (Biotechgate)": "biotech_services_companies",
        "CRO and clinical demand: trial registrations since 2019 (WHO)": "trial_registrations_since_2019",  # noqa: E501
        "Interventional trials starting 2025 (ClinicalTrials.gov, not yet verified)": "trials_started_2025",  # noqa: E501
        "CDMOs: biologics sites listed": "cdmo_biologics_sites",
        "CDMOs: listed capacity (L)": "cdmo_capacity_l",
        "Segments with evidence (of 6)": "segments_with_evidence",
        "Norm. research": "norm_research",
        "Norm. pharma sites": "norm_pharma_sites",
        "Norm. biotech": "norm_biotech",
        "Norm. R&D services": "norm_rd_services",
        "Norm. CDMO sites": "norm_cdmo_sites",
        "Demand score (0-1, average of available norms)": "demand_score",
        "Gaps and notes": "gaps_and_notes",
        "R&D spending, all sectors (GERD, PPP $bn, 2024, OECD MSTI Mar 2026)": "gerd_ppp_bn_2024",
        "GERD 2024 note": "gerd_2024_note",
    },
    "clusters/sheet/demand_by_region.csv": {
        "Region": "region",
        "Countries tracked": "countries_tracked",
        "Academia and government research (Nature Index Share 2025)": "nature_index_share_2025",
        "Share of tracked research": "share_of_tracked_research",
        "Top-100 institutions: academia": "top100_academia",
        "Top-100 institutions: government labs": "top100_government",
        "FDA-catalogued drug sites (big pharma, generics)": "fda_drug_sites",
        "Share of tracked drug sites": "share_of_tracked_drug_sites",
        "Biotech therapeutics companies (Biotechgate)": "biotech_therapeutics_companies",
        "Biotech R&D services companies (Biotechgate)": "biotech_services_companies",
        "CDMO biologics sites listed": "cdmo_biologics_sites",
        "CDMO listed capacity (L)": "cdmo_capacity_l",
        "Highest demand score in region": "highest_demand_score",
    },
    "clusters/sheet/research_institutions.csv": {
        "Rank": "rank",
        "Institution": "institution",
        "Country": "country",
        "Segment": "segment",
        "Nature Index Share 2025": "nature_index_share_2025",
        "Nature Index Count 2025": "nature_index_count_2025",
        "Confidence": "confidence",
        "Source ID": "source_id",
        "Classification note": "classification_note",
    },
    "clusters/sheet/data_sources.csv": {
        "Source ID": "source_id",
        "Source": "source",
        "Source type": "source_type",
        "Used in": "used_in",
        "URL or endpoint": "url",
        "Access method": "access_method",
        "Refresh query or request": "refresh_query",
        "Refresh frequency": "refresh_frequency",
        "Last pulled": "last_pulled",
        "Notes": "notes",
    },
    "coverage/sheet/sources.csv": {
        "ID": "ID",
        "Title": "Title",
        "Publisher": "Publisher",
        "Date": "Date",
        "URL": "URL",
        "Type": "Type",
    },
    "coverage/sheet/peer_sites.csv": {
        "Site ID": "Site ID",
        "Company": "Company",
        "Site": "Site",
        "Country": "Country",
        "Danaher region": "Danaher region",
        "Families made": "Families made",
        "Evidence (summary of source)": "Evidence (summary of source)",
        "Source ID": "Source ID",
        "Confidence": "Confidence",
    },
    "coverage/sheet/register_sites.csv": {
        "Site ID": "Site ID",
        "Site": "Site",
        "Country": "Country",
        "Region": "Region",
        "Site type": "Site type",
        "Activities seen": "Activities seen",
        "Presence": "Presence",
        "Heritage": "Heritage",
        "Evidence": "Evidence",
        "Confidence (H/M/L)": "Confidence (H/M/L)",
        "Source": "Source",
        "Linked entities": "Linked entities",
        "Danaher reporting region": "Danaher reporting region",
        "Value-chain stages made here": "Value-chain stages made here",
        "Stage evidence": "Stage evidence",
        "Source URL": "Source URL",
        "Source quote": "Source quote",
        "Source date": "Source date",
        "Service evidence (region)": "Service evidence (region)",
        "Service quote": "Service quote",
        "Service source URL": "Service source URL",
    },
    "coverage/sheet/t3_market_size.csv": {
        "ID": "ID",
        "Estimate": "Estimate",
        "Value (USD bn)": "Value (USD bn)",
        "Year": "Year",
        "Publisher": "Publisher",
        "Scope": "Scope",
        "Share figures given": "Share figures given",
        "Use on tile": "Use on tile",
        "Evidence (quote)": "Evidence (quote)",
        "Source IDs": "Source IDs",
        "Confidence": "Confidence",
    },
    "coverage/sheet/t3_supplier_revenue.csv": {
        "ID": "ID",
        "Company": "Company",
        "Reported unit": "Reported unit",
        "FY2025 revenue (reported currency, m)": "FY2025 revenue (reported currency, m)",
        "Currency": "Currency",
        "FY2025 revenue (USD m)": "FY2025 revenue (USD m)",
        "Share of disclosed peer pool": "Share of disclosed peer pool",
        "Growth (as reported)": "Growth (as reported)",
        "Scope of the unit": "Scope of the unit",
        "Evidence (quote)": "Evidence (quote)",
        "Source IDs": "Source IDs",
        "Confidence": "Confidence",
    },
    "coverage/sheet/t4_region_cards.csv": {
        "Region": "Region",
        "Cytiva families made (of 8)": "Cytiva families made (of 8)",
        "Cytiva steps local (of 8)": "Cytiva steps local (of 8)",
        "Biotech sales Q1 2026 ($m)": "Biotech sales Q1 2026 ($m)",
        "Share of Biotech sales": "Share of Biotech sales",
        "Peers with a site found": "Peers with a site found",
        "Source IDs": "Source IDs",
        "Confidence": "Confidence",
        "Sales evidence (quote)": "Sales evidence (quote)",
    },
}


def read_sheet(path: Path) -> list[dict]:
    """Read one export through its header map. Keys are the field names of the map.

    Raises ValueError if the file has no map, a header the map does not know, or a mapped header
    that is missing from the file."""
    key = path.resolve().relative_to(DATA_ROOT.resolve()).as_posix()
    if key not in HEADER_MAPS:
        raise ValueError(f"{key}: no header map")
    mapping = HEADER_MAPS[key]
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames or []
        unknown = [h for h in headers if h not in mapping]
        missing = [h for h in mapping if h not in headers]
        if unknown or missing:
            raise ValueError(f"{key}: unmapped headers {unknown}, missing headers {missing}")
        return [{mapping[h]: (v or "") for h, v in row.items()} for row in reader]


# ---------------------------------------------------------------------------
# Tabs with more than one table (screen 4). A tab is read as sections: each section starts at
# a header row, identified by its first cell. Sections end at a blank row. Rows outside every
# section are "loose" (summaries, totals, notes and mockup checks); titles are skipped.
# Every header of a section must be mapped, and every mapped header must be present.


@dataclass(frozen=True)
class Section:
    """One table in a tab: the first cell of its header row, and its header map."""

    header: str
    name: str
    columns: dict[str, str]


@dataclass(frozen=True)
class TabSpec:
    sections: tuple[Section, ...]
    titles: tuple[str, ...] = ()


@dataclass
class TabRead:
    rows: dict[str, list[dict]]  # section name -> data rows (field -> text, plus "_cells")
    loose: list[list[str]]  # non-blank rows outside every section, titles excluded


SECTION_TABS: dict[str, TabSpec] = {
    "demand/sheet/t1_disease_burden.csv": TabSpec(
        (
            Section(
                "Country",
                "burden",
                {
                    "Country": "country",
                    "Map region": "map_region",
                    "New cancer cases 2022": "new_cancer_cases_2022",
                    "Adults (20-79) with diabetes 2024, millions": "diabetes_adults_2024_m",
                    "Total DALYs 2021 (WHO GHE)": "dalys_2021_m",
                    "Cancer source": "cancer_2022_source_id",
                    "Diabetes source": "diabetes_source_id",
                    "Confidence": "confidence",
                    "Notes": "note",
                    "New cancer cases 2024 (GLOBOCAN 2024)": "new_cancer_cases_2024",
                    "Cancer 2024 source": "cancer_2024_source_id",
                },
            ),
        )
    ),
    "demand/sheet/t3_pipeline_by_type.csv": TabSpec(
        (
            Section(
                "Medicine type",
                "pipeline",
                {
                    "Medicine type": "medicine_type",
                    "Metric": "metric",
                    "Value": "value",
                    "Previous value": "previous_value",
                    "Change": "change",
                    "Period": "period",
                    "Source": "source_title",
                    "URL": "source_url",
                    "Confidence": "confidence",
                    "Evidence": "evidence",
                },
            ),
            Section(
                "Region",
                "pipeline_region",
                {
                    "Region": "region",
                    "Share of drugs in pipeline": "share_of_drugs",
                    "Share of companies with a pipeline": "share_of_companies",
                    "Period": "period",
                    "Source": "source_title",
                    "URL": "source_url",
                    "Confidence": "confidence",
                    "Evidence": "evidence",
                },
            ),
        ),
        titles=("Pipeline by company HQ region (all types)",),
    ),
    "demand/sheet/t4_approvals_expiries.csv": TabSpec(
        (
            Section(
                "Regulator",
                "approval",
                {
                    "Regulator": "regulator",
                    "Metric": "metric",
                    "Value": "value",
                    "Period": "period",
                    "Source": "source_title",
                    "URL": "source_url",
                    "Confidence": "confidence",
                    "Evidence": "evidence",
                },
            ),
            Section(
                "Drug",
                "expiry",
                {
                    "Drug": "drug",
                    "Owner": "owner",
                    "Type": "type",
                    "Event": "event",
                    "Year": "year",
                    "Source": "source_title",
                    "URL": "source_url",
                    "Confidence": "confidence",
                    "Evidence": "evidence",
                },
            ),
        ),
        titles=("Approvals", "Biosimilar wave (loss of exclusivity)"),
    ),
    "demand/sheet/t5_policy_funding.csv": TabSpec(
        (
            Section(
                "Item",
                "policy",
                {
                    "Item": "item",
                    "Label": "label",
                    "What it says": "what_it_says",
                    "Effect on biologics demand": "effect_on_biologics_demand",
                    "Date": "date",
                    "Source": "source_title",
                    "URL": "source_url",
                    "Confidence": "confidence",
                    "Evidence": "evidence",
                },
            ),
        )
    ),
    "demand/sheet/t6_biggest_drugs.csv": TabSpec(
        (
            Section(
                "Rank",
                "top_drug",
                {
                    "Rank": "rank",
                    "Drug": "drug",
                    "Company": "company",
                    "Sales FY2025, USD bn": "sales_fy2025_usd_bn",
                    "Type (our classification)": "type",
                    "Disease area (our classification)": "disease_area",
                    "Made with bioprocess equipment?": "bioprocess_use",
                    "Source": "source_title",
                    "URL": "source_url",
                    "Confidence": "confidence",
                    "Evidence": "evidence",
                },
            ),
        ),
        titles=("Summary (calculated)",),
    ),
    "demand/sheet/t7_capacity_pledges.csv": TabSpec(
        (
            Section(
                "Company",
                "pledge",
                {
                    "Company": "company",
                    "Pledge, USD bn": "pledge_usd_bn",
                    "Period": "period",
                    "What it includes": "includes",
                    "Biologics relevance (our view)": "biologics_relevance",
                    "Announced": "announced",
                    "Source": "source_title",
                    "URL": "source_url",
                    "Confidence": "confidence",
                    "Evidence": "evidence",
                },
            ),
            Section(
                "Built capacity (not pledges)",
                "built",
                {
                    "Built capacity (not pledges)": "company",
                    "Capacity, L": "capacity_l",
                    "Status": "status",
                    "As of": "as_of",
                    "Source": "source_title",
                    "URL": "source_url",
                    "Confidence": "confidence",
                    "Evidence": "evidence",
                },
            ),
        )
    ),
    "demand/sheet/t8_products_used.csv": TabSpec(
        (
            Section(
                "Medicine type",
                "product",
                {
                    "Medicine type": "medicine_type",
                    "Chromatography resins": "chromatography_resins",
                    "Filtration": "filtration",
                    "Single-use bioreactors and bags": "single_use_bioreactors_bags",
                    "Cell culture media": "cell_culture_media",
                    "Cell and gene therapy tools": "cell_gene_therapy_tools",
                    "Rationale": "rationale",
                    "Confidence": "confidence",
                    "Changed from mockup": "changed_from_mockup",
                },
            ),
        )
    ),
    "demand/sheet/sources.csv": TabSpec(
        (
            Section(
                "Source ID",
                "source",
                {
                    "Source ID": "source_id",
                    "Source": "source_title",
                    "Type": "type",
                    "Used in": "used_in",
                    "URL or endpoint": "url",
                    "Refresh method": "refresh_method",
                    "Frequency": "frequency",
                    "Last pulled": "last_pulled",
                    "Notes": "notes",
                },
            ),
        )
    ),
}

# T2 holds two side-by-side tables with repeated headers, so it is checked by position rather
# than by section: row 2 must start with these headers, and its first column is the ranking.
DEMAND_T2 = "demand/sheet/t2_top10_countries.csv"
DEMAND_T2_HEADER = ("Country", "New cancer cases 2024", "Adults with diabetes, m")


def read_tab(path: Path) -> TabRead:
    """Read a multi-table tab through its section map. Fails on a missing or changed header."""
    key = path.resolve().relative_to(DATA_ROOT.resolve()).as_posix()
    if key not in SECTION_TABS:
        raise ValueError(f"{key}: no section map")
    spec = SECTION_TABS[key]
    with path.open(encoding="utf-8", newline="") as handle:
        table = list(csv.reader(handle))
    rows: dict[str, list[dict]] = {s.name: [] for s in spec.sections}
    loose: list[list[str]] = []
    found: set[str] = set()
    current: tuple[Section, dict[int, str]] | None = None
    for cells in table:
        values = [c.strip() for c in cells]
        if not any(values):
            current = None
            continue
        section = next((s for s in spec.sections if s.header == values[0]), None)
        if section is not None:
            if section.name in found:
                raise ValueError(f"{key}: section {section.name} appears twice")
            head = {i: h for i, h in enumerate(values) if h}
            unknown = [h for h in head.values() if h not in section.columns]
            missing = [h for h in section.columns if h not in head.values()]
            if unknown or missing:
                raise ValueError(
                    f"{key}: section {section.name}: unmapped headers {unknown}, "
                    f"missing headers {missing}"
                )
            found.add(section.name)
            current = (section, {i: section.columns[h] for i, h in head.items()})
            continue
        if current is not None:
            section, positions = current
            record = {f: (values[i] if i < len(values) else "") for i, f in positions.items()}
            record["_cells"] = values
            rows[section.name].append(record)
            continue
        if values[0] in spec.titles and sum(1 for v in values if v) == 1:
            continue
        loose.append(values)
    absent = [s.header for s in spec.sections if s.name not in found]
    if absent:
        raise ValueError(f"{key}: section header missing: {absent}")
    return TabRead(rows, loose)


# Screen 1 (overview). Every tab is read through its section map; a changed header fails the read.
OVERVIEW_TABS: dict[str, TabSpec] = {
    "overview/sheet/attention.csv": TabSpec(
        (
            Section(
                "ID",
                "attention",
                {
                    "ID": "id",
                    "Issue": "issue",
                    "Action": "action",
                    "Evidence label": "evidence_label",
                    "Why it matters (goal at risk)": "why_it_matters",
                    "Key fact": "key_fact",
                    "Detail lives in": "detail_lives_in",
                    "Source": "source",
                    "Review by": "review_by",
                },
            ),
        )
    ),
    "overview/sheet/sources.csv": TabSpec(
        (
            Section(
                "ID",
                "source",
                {
                    "ID": "id",
                    "Title": "title",
                    "Publisher": "publisher",
                    "Date": "date",
                    "URL": "url",
                    "Type": "type",
                },
            ),
        )
    ),
    "overview/sheet/t1_peer_financials.csv": TabSpec(
        (
            Section(
                "ID",
                "financials",
                {
                    "ID": "id",
                    "Company": "company",
                    "Ticker": "ticker",
                    "FY": "fy",
                    "Currency": "currency",
                    "Revenue (m)": "revenue_m",
                    "Revenue growth, reported %": "revenue_growth_reported_pct",
                    "Organic / cc growth %": "organic_growth_pct",
                    "Gross profit (m)": "gross_profit_m",
                    "Net income (m)": "net_income_m",
                    "Operating cash flow (m)": "operating_cash_flow_m",
                    "Free cash flow (m)": "free_cash_flow_m",
                    "Revenue (USD m)": "revenue_usd_m",
                    "Gross margin %": "gross_margin_pct",
                    "Net margin %": "net_margin_pct",
                    "FCF margin %": "fcf_margin_pct",
                    "Source IDs": "source_ids",
                    "Confidence": "confidence",
                    "Notes": "notes",
                },
            ),
        )
    ),
    "overview/sheet/t1_rankings.csv": TabSpec(
        (
            Section(
                "ID",
                "rankings",
                {
                    "ID": "id",
                    "Company": "company",
                    "Forbes Global 2000 (2026)": "forbes_2026",
                    "Forbes Global 2000 (2025)": "forbes_2025",
                    "S&P long-term rating": "sp_rating",
                    "Fortune Global 500": "fortune_500",
                    "EcoVadis": "ecovadis",
                    "Source": "source",
                    "Status": "status",
                },
            ),
        )
    ),
    "overview/sheet/t2_ma.csv": TabSpec(
        (
            Section(
                "ID",
                "ma",
                {
                    "ID": "id",
                    "Buyer": "buyer",
                    "Target": "target",
                    "Type": "type",
                    "Announced": "announced",
                    "Completed": "completed",
                    "Value": "value",
                    "Area": "area",
                    "In last 12 months?": "in_last_12_months",
                    "Source IDs": "source_ids",
                    "Confidence": "confidence",
                },
            ),
        )
    ),
    "overview/sheet/t3_share_prices.csv": TabSpec(
        (
            Section(
                "ID",
                "prices",
                {
                    "ID": "id",
                    "Company": "company",
                    "Ticker (Yahoo)": "ticker",
                    "Exchange": "exchange",
                    "Currency": "currency",
                    "Last close": "last_close",
                    "Close date": "close_date",
                    "12-month change %": "change_12m_pct",
                    "52-week low": "low_52w",
                    "52-week high": "high_52w",
                    "Refresh": "refresh",
                },
            ),
        )
    ),
    "overview/sheet/t4_competitor_news.csv": TabSpec(
        (
            Section(
                "ID",
                "news",
                {
                    "ID": "id",
                    "Company": "company",
                    "Feed (company newsroom)": "feed",
                    "Search query for news feed": "search_query",
                    "Latest verified headline (seed)": "headline",
                    "Date": "date",
                    "Tag": "tag",
                    "URL": "url",
                    "Source type": "source_type",
                    "Confidence": "confidence",
                },
            ),
        )
    ),
    "overview/sheet/t5_implications.csv": TabSpec(
        (
            Section(
                "ID",
                "implications",
                {
                    "ID": "id",
                    "Hypothesis (not a finding)": "hypothesis",
                    "Based on": "based_on",
                    "What would confirm or refute it": "confirm_or_refute",
                    "Area": "area",
                    "Confidence": "confidence",
                },
            ),
        )
    ),
}

SECTION_TABS.update(OVERVIEW_TABS)
