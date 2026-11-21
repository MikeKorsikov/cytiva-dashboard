"""App database schema, from BRD section 7.

Every data table carries the common fields: source_url, source_type, published_date,
loaded_at, evidence_label, is_sample, verification_status and check_notes.

Business columns are listed per table. Column types are SQLite types.
"""

from dataclasses import dataclass, field

COMMON_COLUMNS: dict[str, str] = {
    "source_url": "TEXT NOT NULL",
    "source_type": "TEXT NOT NULL",  # API, document, news, curated
    "published_date": "TEXT",  # ISO date of the source
    "loaded_at": "TEXT NOT NULL",  # ISO timestamp of the load
    "evidence_label": "TEXT NOT NULL",  # Fact, Signal, Hypothesis
    "is_sample": "INTEGER NOT NULL DEFAULT 0",
    "verification_status": "TEXT NOT NULL",  # passed, unverified
    "check_notes": "TEXT",
}

SOURCE_TYPES = ("API", "document", "news", "curated")
EVIDENCE_LABELS = ("Fact", "Signal", "Hypothesis")
VERIFICATION_STATUSES = ("passed", "unverified")


@dataclass(frozen=True)
class Table:
    name: str
    key: tuple[str, ...]  # natural key used for upserts
    columns: dict[str, str] = field(default_factory=dict)


TABLES: tuple[Table, ...] = (
    Table(
        "company",
        ("company_id",),
        {
            "company_id": "TEXT NOT NULL",
            "name": "TEXT NOT NULL",
            "ticker": "TEXT",
            "country": "TEXT",
            "reporting_standard": "TEXT",
            "fiscal_year_end": "TEXT",
            "group_or_segment": "TEXT",
        },
    ),
    Table(
        "region",
        ("region_id",),
        {
            "region_id": "TEXT NOT NULL",
            "name": "TEXT NOT NULL",
        },
    ),
    Table(
        "fx_rate",
        ("currency", "period", "rate_type"),
        {
            "currency": "TEXT NOT NULL",
            "period": "TEXT NOT NULL",
            "rate_type": "TEXT NOT NULL",
            "rate_to_usd": "REAL NOT NULL",  # average or period_end
        },
    ),
    Table(
        "share_price_daily",
        ("ticker", "price_date"),
        {
            "ticker": "TEXT NOT NULL",
            "price_date": "TEXT NOT NULL",
            "close_usd": "REAL NOT NULL",
            "close_local": "REAL",
            "currency": "TEXT",
        },
    ),
    Table(
        "financial_metric",
        ("company_id", "fiscal_year", "metric"),
        {
            "company_id": "TEXT NOT NULL",
            "fiscal_year": "INTEGER NOT NULL",
            "metric": "TEXT NOT NULL",
            "value_usd": "REAL",
            "value_local": "REAL",
            "currency": "TEXT",
        },
    ),
    Table(
        "ranking",
        ("company_id", "ranking", "year"),
        {
            "company_id": "TEXT NOT NULL",
            "ranking": "TEXT NOT NULL",
            "value": "TEXT",
            "year": "INTEGER",
        },
    ),
    Table(
        "deal",
        ("acquirer", "announced_date", "headline"),
        {
            "acquirer": "TEXT NOT NULL",  # peer company named as the subject of the headline
            "announced_date": "TEXT NOT NULL",
            "category": "TEXT NOT NULL",  # M&A, Licensing, Collaboration
            "headline": "TEXT NOT NULL",  # target names are not parsed (headline and link only)
            "value_usd": "REAL",  # deal value, only where stated in the source
            "status": "TEXT",  # announced
        },
    ),
    Table(
        "news_item",
        ("url",),
        {
            "url": "TEXT NOT NULL",
            "company_id": "TEXT",
            "item_date": "TEXT",
            "tag": "TEXT",
            "headline": "TEXT NOT NULL",
            "summary": "TEXT",
        },
    ),
    # Screen 2, from the seed sheets (data/coverage/sheet/). Sources and sites keep their sheet IDs.
    Table(
        "s2_source",
        ("id",),
        {
            "id": "TEXT NOT NULL",  # S01 to S20, the Sources tab of the coverage sheet
            "title": "TEXT NOT NULL",
            "publisher": "TEXT",
            "date_text": "TEXT",
            "url": "TEXT NOT NULL",
        },
    ),
    Table(
        "s2_peer_site",
        ("site_id",),
        {
            "site_id": "TEXT NOT NULL",  # PS-01 to PS-47, the Peer sites tab
            "company": "TEXT NOT NULL",
            "site": "TEXT NOT NULL",
            "country": "TEXT",
            "region_id": "TEXT NOT NULL",  # Danaher region column
            "evidence": "TEXT",
            "source_id": "TEXT NOT NULL",
            "confidence": "TEXT NOT NULL",  # H, M, L
        },
    ),
    Table(
        "s2_peer_family",
        ("site_id", "family"),
        {
            "site_id": "TEXT NOT NULL",
            "family": "TEXT NOT NULL",
            "partial": "INTEGER NOT NULL",  # 1 where the sheet marks the family as partial
        },
    ),
    Table(
        "s2_cyt_site",
        ("site_id",),
        {
            "site_id": "TEXT NOT NULL",  # ST01 to ST51, the Sites tab of the site register
            "site": "TEXT NOT NULL",
            "country": "TEXT",
            "region_id": "TEXT NOT NULL",  # Danaher reporting region
            "site_type": "TEXT",
            "activities": "TEXT",
            "presence": "TEXT",
            "heritage": "TEXT",
            "evidence": "TEXT",
            "linked_entities": "TEXT",
            "stages_made": "TEXT",  # Value-chain stages made here
            "stage_evidence": "TEXT",
            "source_id": "TEXT NOT NULL",  # S19 (the register) unless a primary URL is given
            "primary_url": "INTEGER NOT NULL",  # 1 where the register gives a primary source URL
            "source_quote": "TEXT",
            "source_date": "TEXT",
            "service_region": "TEXT",  # step 8 evidence for the site's region, if any
            "service_status": "TEXT",  # Made or Partial
            "service_quote": "TEXT",
            "confidence": "TEXT NOT NULL",  # H, M, L
        },
    ),
    Table(
        "s2_grid",
        ("company_id", "region_id", "family"),
        {
            "company_id": "TEXT NOT NULL",
            "region_id": "TEXT NOT NULL",
            "family": "TEXT NOT NULL",  # product family or Service; ? cells are not stored
            "status": "TEXT NOT NULL",  # Made, Partial, Not made
            "confidence": "TEXT NOT NULL",  # best confidence of the rows behind the cell
            "source_id": "TEXT NOT NULL",
        },
    ),
    Table(
        "s2_biotech_sales",
        ("region_id",),
        {
            "region_id": "TEXT NOT NULL",
            "value_m": "REAL NOT NULL",  # Biotechnology sales, Q1 2026, USD m (Danaher 10-Q)
            "period": "TEXT NOT NULL",
            "quote": "TEXT NOT NULL",
            "source_id": "TEXT NOT NULL",
            "confidence": "TEXT NOT NULL",
        },
    ),
    Table(
        "s2_market_size",
        ("id",),
        {
            "id": "TEXT NOT NULL",
            "estimate": "TEXT",
            "value_usd_bn": "REAL",
            "year": "INTEGER",
            "publisher": "TEXT",
            "scope": "TEXT",
            "share_figures": "TEXT",
            "use_on_tile": "TEXT",
            "quote": "TEXT",
            "source_id": "TEXT",
            "confidence": "TEXT",
        },
    ),
    Table(
        "s2_supplier_revenue",
        ("id",),
        {
            "id": "TEXT NOT NULL",
            "company": "TEXT",
            "reported_unit": "TEXT",
            "revenue_reported_m": "TEXT",
            "currency": "TEXT",
            "revenue_usd_m": "REAL",  # NULL when the sheet gives no number
            "share_of_pool": "TEXT",
            "growth_reported": "TEXT",
            "scope": "TEXT",
            "quote": "TEXT",
            "source_id": "TEXT",
            "confidence": "TEXT",
        },
    ),
    Table(
        "step_family_map",
        ("step", "product_family"),
        {
            "step": "TEXT NOT NULL",
            "product_family": "TEXT NOT NULL",
        },
    ),
    Table(
        "cluster_fact",
        ("fact_id",),
        {
            "fact_id": "TEXT NOT NULL",
            "cluster_id": "TEXT NOT NULL",
            "cluster": "TEXT NOT NULL",
            "country": "TEXT NOT NULL",
            "metric": "TEXT NOT NULL",
            "value": "REAL",
            "unit": "TEXT",
            "as_of": "TEXT",
            "scope": "TEXT",  # cluster, city-wide, capacity or n/a
            "confidence": "TEXT NOT NULL",
            "evidence": "TEXT",
            "source_title": "TEXT",
            "source_id": "TEXT",
        },
    ),
    Table(
        "cdmo_site",
        ("site_id",),
        {
            "site_id": "TEXT NOT NULL",
            "cdmo": "TEXT NOT NULL",
            "city": "TEXT NOT NULL",
            "country": "TEXT NOT NULL",
            "capacity_l": "REAL",
            "status": "TEXT",
            "as_of": "TEXT",
            "confidence": "TEXT NOT NULL",
            "evidence": "TEXT",
            "source_title": "TEXT",
        },
    ),
    Table(
        "market_signal",
        ("indicator_id",),
        {
            "indicator_id": "TEXT NOT NULL",
            "geography": "TEXT NOT NULL",
            "indicator": "TEXT NOT NULL",
            "value": "REAL",
            "unit": "TEXT",
            "customer_segment": "TEXT",
            "period": "TEXT",
            "direction": "TEXT",  # up, down or none
            "confidence": "TEXT NOT NULL",
            "evidence": "TEXT",
            "source_title": "TEXT",
        },
    ),
    Table(
        "country_demand",
        ("country",),
        {
            "country": "TEXT NOT NULL",
            "region": "TEXT NOT NULL",
            "nature_index_share_2024": "REAL",
            "fda_drug_sites_fy2024": "INTEGER",
            "trial_registrations_since_2019": "INTEGER",
            "cdmo_biologics_sites": "INTEGER",
            "cdmo_capacity_l": "REAL",
            "demand_score": "REAL",
            "segments_with_evidence": "INTEGER",
            "confidence": "TEXT NOT NULL",
        },
    ),
    Table(
        "country_barrier_index",
        ("country",),
        {
            "country": "TEXT NOT NULL",
            "lpi_customs_score_2023": "REAL",
            "customs_friction_1_5": "REAL",
            "tariff_applied_pct": "REAL",
            "tariff_year": "INTEGER",
            "tariff_score_1_5": "REAL",
            "local_preference_1_5": "REAL",
            "regulatory_friction_1_5": "REAL",
            "geopolitical_risk_1_5": "REAL",
            "tbi_2025_score": "REAL",  # Tholos Trade Barrier Index 2025, lower is better (not 1-5)
            "barrier_index": "REAL",
            "barrier_scores_available": "INTEGER",
            "confidence": "TEXT NOT NULL",
        },
    ),
    Table(
        "demand_burden",
        ("country",),
        {
            "country": "TEXT NOT NULL",
            "map_region": "TEXT",
            "new_cancer_cases_2022": "TEXT",
            "diabetes_adults_2024_m": "TEXT",
            "dalys_2021_m": "TEXT",
            "cancer_source_title": "TEXT",
            "cancer_source_url": "TEXT",
            "diabetes_source_url": "TEXT",
            "confidence": "TEXT",
            "note": "TEXT",
        },
    ),
    Table(
        "demand_pipeline",
        ("medicine_type", "metric"),
        {
            "medicine_type": "TEXT NOT NULL",
            "metric": "TEXT NOT NULL",
            "value": "TEXT",
            "previous_value": "TEXT",
            "period": "TEXT",
            "source_title": "TEXT",
            "source_url": "TEXT",
            "confidence": "TEXT",
            "evidence": "TEXT",
        },
    ),
    Table(
        "demand_approval",
        ("regulator", "metric"),
        {
            "regulator": "TEXT NOT NULL",
            "metric": "TEXT NOT NULL",
            "value": "TEXT",
            "period": "TEXT",
            "source_title": "TEXT",
            "source_url": "TEXT",
            "confidence": "TEXT",
            "evidence": "TEXT",
        },
    ),
    Table(
        "demand_expiry",
        ("drug",),
        {
            "drug": "TEXT NOT NULL",
            "owner": "TEXT",
            "type": "TEXT",
            "event": "TEXT",
            "year": "TEXT",
            "source_title": "TEXT",
            "source_url": "TEXT",
            "confidence": "TEXT",
            "evidence": "TEXT",
        },
    ),
    Table(
        "demand_policy",
        ("item",),
        {
            "item": "TEXT NOT NULL",
            "label": "TEXT",
            "what_it_says": "TEXT",
            "effect_on_biologics_demand": "TEXT",
            "date": "TEXT",
            "source_title": "TEXT",
            "source_url": "TEXT",
            "confidence": "TEXT",
            "evidence": "TEXT",
        },
    ),
    Table(
        "demand_top_drug",
        ("drug",),
        {
            "drug": "TEXT NOT NULL",
            "rank": "TEXT",
            "company": "TEXT",
            "sales_fy2025_usd_bn": "TEXT",
            "type": "TEXT",
            "disease_area": "TEXT",
            "bioprocess_use": "TEXT",
            "source_title": "TEXT",
            "source_url": "TEXT",
            "confidence": "TEXT",
            "evidence": "TEXT",
        },
    ),
    Table(
        "demand_capacity",
        ("kind", "company"),
        {
            "kind": "TEXT NOT NULL",
            "company": "TEXT NOT NULL",
            "pledge_or_capacity": "TEXT",
            "unit": "TEXT",
            "period": "TEXT",
            "includes": "TEXT",
            "biologics_relevance": "TEXT",
            "announced": "TEXT",
            "source_title": "TEXT",
            "source_url": "TEXT",
            "confidence": "TEXT",
            "evidence": "TEXT",
        },
    ),
    Table(
        "demand_product_use",
        ("medicine_type",),
        {
            "medicine_type": "TEXT NOT NULL",
            "chromatography_resins": "TEXT",
            "filtration": "TEXT",
            "single_use_bioreactors_bags": "TEXT",
            "cell_culture_media": "TEXT",
            "cell_gene_therapy_tools": "TEXT",
            "rationale": "TEXT",
            "confidence": "TEXT",
        },
    ),
    Table(
        "tech_eos",
        ("id",),
        {
            "id": "TEXT NOT NULL",
            "product": "TEXT",
            "where_used": "TEXT",
            "estate_evidence": "TEXT",
            "estate_confidence": "TEXT",
            "support_milestone": "TEXT",
            "milestone_date_text": "TEXT",
            "next_milestone": "TEXT",
            "status_text": "TEXT",
            "vendor_date_quote": "TEXT",
            "source_ids": "TEXT",
            "date_confidence": "TEXT",
            "date_value": "TEXT",
            "date_precision": "TEXT",
            "is_floor": "INTEGER",
            "date_text": "TEXT",
            "source_note": "TEXT",
            "show_on_tile": "TEXT",  # sheet column M: only "Yes" rows are on tile 1
            "reason": "TEXT",
            "tile_note": "TEXT",
        },
    ),
    Table(
        "tech_incidents",
        ("id",),
        {
            "id": "TEXT NOT NULL",
            "date_text": "TEXT",
            "vendor": "TEXT",
            "product": "TEXT",
            "watchlist_id": "TEXT",
            "type": "TEXT",
            "what_happened": "TEXT",
            "vendor_statement": "TEXT",
            "tier_a_count": "TEXT",
            "tier_b_count": "TEXT",
            "product_match": "TEXT",
            "type_for_score": "TEXT",
            "estate_confidence": "TEXT",
            "action": "TEXT",
            "evidence_quote": "TEXT",
            "source_ids": "TEXT",
            "row_kind": "TEXT",
            "date_value": "TEXT",
            "source_note": "TEXT",
        },
    ),
    Table(
        "tech_watchlist",
        ("watch_id",),
        {
            "watch_id": "TEXT NOT NULL",
            "vendor": "TEXT",
            "products_in_estate": "TEXT",
            "operating_company": "TEXT",
            "estate_evidence_ids": "TEXT",
            "estate_confidence": "TEXT",
            "news_keywords": "TEXT",
            "feed_ids": "TEXT",
            "notes": "TEXT",
            "source_note": "TEXT",
        },
    ),
    Table(
        "tech_feeds",
        ("feed_id",),
        {
            "feed_id": "TEXT NOT NULL",
            "tier": "TEXT",
            "source": "TEXT",
            "what_it_gives": "TEXT",
            "endpoint": "TEXT",
            "format": "TEXT",
            "refresh": "TEXT",
            "watch_ids": "TEXT",
            "reachable_from_workspace": "TEXT",
            "notes": "TEXT",
            "source_note": "TEXT",
        },
    ),
    Table(
        "tech_integrations",
        ("id",),
        {
            "id": "TEXT NOT NULL",
            "system": "TEXT",
            "readiness_group": "TEXT",
            "interfaces_available": "TEXT",
            "estate_evidence": "TEXT",
            "estate_confidence": "TEXT",
            "vendor_interface_evidence": "TEXT",
            "source_ids": "TEXT",
            "capability_confidence": "TEXT",
            "notes": "TEXT",
            "source_note": "TEXT",
        },
    ),
    Table(
        "tech_adoption",
        ("id",),
        {
            "id": "TEXT NOT NULL",
            "technology": "TEXT",
            "level": "TEXT",
            "signal": "TEXT",
            "signal_date_text": "TEXT",
            "who": "TEXT",
            "evidence_quote": "TEXT",
            "source_ids": "TEXT",
            "confidence": "TEXT",
            "gartner_trend_link": "TEXT",
            "source_note": "TEXT",
        },
    ),
    Table(
        "tech_gartner",
        ("id",),
        {
            "id": "TEXT NOT NULL",
            "trend": "TEXT",
            "cytiva_danaher_signal": "TEXT",
            "release_date": "TEXT",
            "publisher": "TEXT",
            "evidence": "TEXT",
            "source_ids": "TEXT",
            "confidence": "TEXT",
            "source_note": "TEXT",
        },
    ),
    Table(
        "tech_implications",
        ("id",),
        {
            "id": "TEXT NOT NULL",
            "hypothesis": "TEXT",
            "based_on": "TEXT",
            "confirm_or_refute": "TEXT",
            "area": "TEXT",
            "confidence": "TEXT",
            "source_note": "TEXT",
        },
    ),
    Table(
        "tech_estate_evidence",
        ("id",),
        {
            "id": "TEXT NOT NULL",
            "system": "TEXT",
            "operating_company": "TEXT",
            "evidence_quote": "TEXT",
            "source_ids": "TEXT",
            "seen_date": "TEXT",
            "confidence": "TEXT",
            "source_note": "TEXT",
        },
    ),
    Table(
        "tech_sources",
        ("id",),
        {
            "id": "TEXT NOT NULL",
            "title": "TEXT",
            "publisher": "TEXT",
            "date_text": "TEXT",
            "url": "TEXT",
            "notes": "TEXT",
            "tier": "TEXT",
            "source_note": "TEXT",
        },
    ),
    Table(
        "tech_row_sources",
        ("row_type", "row_id", "source_id"),
        {
            "row_type": "TEXT NOT NULL",
            "row_id": "TEXT NOT NULL",
            "source_id": "TEXT NOT NULL",
        },
    ),
    Table(
        "screen_notes",
        ("tab", "label", "text"),
        {
            "tab": "TEXT NOT NULL",
            "label": "TEXT NOT NULL",
            "text": "TEXT NOT NULL",
        },
    ),
    Table(
        "market_estimate",
        ("scope", "year", "source_url"),
        {
            "scope": "TEXT NOT NULL",
            "year": "INTEGER NOT NULL",
            "size_usd": "REAL NOT NULL",
        },
    ),
    Table(
        "gmp_site",
        ("site_id",),
        {
            "site_id": "TEXT NOT NULL",
            "name": "TEXT",
            "country": "TEXT",
            "lat": "REAL",
            "lon": "REAL",
            "cluster": "TEXT",
        },
    ),
    Table(
        "country_barrier",
        ("country", "factor"),
        {
            "country": "TEXT NOT NULL",
            "factor": "TEXT NOT NULL",
            "score": "INTEGER NOT NULL",
        },
    ),
    Table(
        "disease_burden",
        ("country", "disease_area", "year"),
        {
            "country": "TEXT NOT NULL",
            "disease_area": "TEXT NOT NULL",
            "year": "INTEGER NOT NULL",
            "dalys": "REAL",
            "cases": "REAL",
        },
    ),
    Table(
        "clinical_trial",
        ("nct_id",),
        {
            "nct_id": "TEXT NOT NULL",
            "modality": "TEXT",
            "phase": "TEXT",
            "sponsor_country": "TEXT",
            "status": "TEXT",
        },
    ),
    Table(
        "approval",
        ("product", "agency", "approval_date"),
        {
            "product": "TEXT NOT NULL",
            "agency": "TEXT NOT NULL",
            "approval_date": "TEXT NOT NULL",
        },
    ),
    Table(
        "patent_expiry",
        ("product", "expiry_year"),
        {
            "product": "TEXT NOT NULL",
            "expiry_year": "INTEGER NOT NULL",
        },
    ),
    Table(
        "drug_sales",
        ("drug", "year"),
        {
            "drug": "TEXT NOT NULL",
            "company_id": "TEXT",
            "disease_area": "TEXT",
            "year": "INTEGER NOT NULL",
            "sales_usd": "REAL",
        },
    ),
    Table(
        "capacity_pledge",
        ("company_id", "location", "announced_date"),
        {
            "company_id": "TEXT NOT NULL",
            "location": "TEXT NOT NULL",
            "announced_date": "TEXT NOT NULL",
            "investment_usd": "REAL",
            "status": "TEXT",
        },
    ),
    Table(
        "policy_event",
        ("event", "country", "event_date"),
        {
            "event": "TEXT NOT NULL",
            "country": "TEXT",
            "event_date": "TEXT NOT NULL",
        },
    ),
    Table(
        "modality_product_map",
        ("modality", "product_line"),
        {
            "modality": "TEXT NOT NULL",
            "product_line": "TEXT NOT NULL",
            "level": "TEXT NOT NULL",
        },
    ),
    Table(
        "layoff_year",
        ("company_id", "year"),
        {
            "company_id": "TEXT NOT NULL",
            "year": "INTEGER NOT NULL",
            "announced": "TEXT NOT NULL",  # Yes (tick), No (cross), Unknown (to collect)
            "note": "TEXT",
        },
    ),
    Table(
        "lifecycle_date",
        ("product", "event"),
        {
            "product": "TEXT NOT NULL",
            "event": "TEXT NOT NULL",
            "event_date": "TEXT NOT NULL",
        },
    ),
    Table(
        "integration_tier",
        ("system",),
        {
            "system": "TEXT NOT NULL",
            "tier": "TEXT NOT NULL",
        },
    ),
    Table(
        "adoption_signal",
        ("technology",),
        {
            "technology": "TEXT NOT NULL",
            "level": "TEXT NOT NULL",
        },
    ),
    # Screen 5: applications ranked by size and complexity (research sheet, rows 2 to 14).
    Table(
        "tech_apps",
        ("name",),
        {
            "name": "TEXT NOT NULL",
            "rank_no": "INTEGER",
            "area": "TEXT",
            "domain": "TEXT",
            "size_score": "INTEGER",
            "complexity_score": "INTEGER",
            "score": "INTEGER",
            "basis": "TEXT",
            "scoring_confidence": "TEXT",
        },
    ),
    # Screen 6 (China): from the research sheet, saved as CSV under data/china/. Amounts in USD
    # in the app; RMB is kept with the rate used (cny_usd_rate).
    Table(
        "cn_source",
        ("id",),
        {
            "id": "TEXT NOT NULL",
            "title": "TEXT",
            "publisher": "TEXT",
            "date_text": "TEXT",
            "source_kind": "TEXT",
            "notes": "TEXT",
        },
    ),
    Table(
        "cn_company",
        ("company_id",),
        {
            "company_id": "TEXT NOT NULL",
            "name_en": "TEXT NOT NULL",
            "name_cn": "TEXT",
            "listing": "TEXT",
            "exchange_code": "TEXT",
            "ownership_status": "TEXT",
            "main_business": "TEXT",
            "products_checked": "TEXT",
            "source_note": "TEXT",
            "confidence": "TEXT NOT NULL",
        },
    ),
    Table(
        "cn_coverage",
        ("company_id", "family"),
        {
            "company_id": "TEXT NOT NULL",
            "family": "TEXT NOT NULL",  # sheet code: Med, SU, Res, Filt, Fill, Gen, Sys, Anl
            "status": "TEXT NOT NULL",  # Made, Partial or Not made (absent = to collect)
            "evidence_id": "TEXT",
            "confidence": "TEXT",  # H, M, L: of the row or site behind the cell
        },
    ),
    Table(
        "cn_coverage_evidence",
        ("evidence_id",),
        {
            "evidence_id": "TEXT NOT NULL",
            "company_id": "TEXT NOT NULL",
            "family": "TEXT NOT NULL",
            "status": "TEXT NOT NULL",
            "evidence": "TEXT",
            "source_note": "TEXT",
            "source_date": "TEXT",
            "confidence": "TEXT NOT NULL",
        },
    ),
    Table(
        "cn_financial",
        ("id",),
        {
            "id": "TEXT NOT NULL",
            "company_id": "TEXT NOT NULL",
            "company": "TEXT NOT NULL",
            "code": "TEXT",
            "period": "TEXT NOT NULL",
            "revenue_rmb_m": "REAL",
            "revenue_usd_m": "REAL",
            "cny_usd_rate": "REAL",  # the assumed rate used for the USD column
            "revenue_yoy_pct": "REAL",
            "gross_margin_pct": "REAL",
            "rd_to_revenue_pct": "REAL",
            "net_profit_rmb_m": "REAL",
            "basis": "TEXT",
            "source_note": "TEXT",
            "confidence": "TEXT NOT NULL",
            "note": "TEXT",
        },
    ),
    Table(
        "cn_vendor",
        ("id",),
        {
            "id": "TEXT NOT NULL",
            "vendor_en": "TEXT NOT NULL",
            "vendor_cn": "TEXT",
            "code": "TEXT",
            "supplies": "TEXT",
            "to_danaher_company": "TEXT",
            "relationship": "TEXT",
            "evidence": "TEXT",
            "source_note": "TEXT",
            "confidence": "TEXT NOT NULL",
        },
    ),
    Table(
        "cn_opportunity",
        ("id",),
        {
            "id": "TEXT NOT NULL",
            "opportunity": "TEXT NOT NULL",
            "why": "TEXT",
            "product_lines": "TEXT",
            "evidence_label": "TEXT NOT NULL",  # Fact, Signal or Hypothesis
            "evidence": "TEXT",
            "source_note": "TEXT",
            "source_date": "TEXT",
            "confidence": "TEXT NOT NULL",
        },
    ),
    Table(
        "cn_implication",
        ("id",),
        {
            "id": "TEXT NOT NULL",
            "hypothesis": "TEXT NOT NULL",
            "based_on": "TEXT",
            "confirm_or_refute": "TEXT",
            "area": "TEXT",
            "confidence": "TEXT NOT NULL",
        },
    ),
    Table(
        "cn_headline",
        ("id",),
        {
            "id": "TEXT NOT NULL",
            "metric": "TEXT NOT NULL",
            "value_text": "TEXT NOT NULL",
            "value_num": "REAL",
            "unit": "TEXT",
            "period": "TEXT",
            "show_on_tile": "TEXT",
            "evidence_label": "TEXT NOT NULL",
            "evidence": "TEXT",
            "source_note": "TEXT",
            "confidence": "TEXT NOT NULL",
        },
    ),
)

# Operational tables: not part of the data model.
RUN_TABLE = "refresh_run"
CHANGE_TABLE = "change_log"

RUN_COLUMNS: dict[str, str] = {
    "run_id": "INTEGER PRIMARY KEY AUTOINCREMENT",
    "trigger": "TEXT NOT NULL",  # scheduled or manual
    "started_at": "TEXT NOT NULL",
    "finished_at": "TEXT",
    "status": "TEXT NOT NULL",  # running, succeeded, failed
    "rows_written": "INTEGER NOT NULL DEFAULT 0",
    "rows_unverified": "INTEGER NOT NULL DEFAULT 0",
    "error": "TEXT",
}

CHANGE_COLUMNS: dict[str, str] = {
    "change_id": "INTEGER PRIMARY KEY AUTOINCREMENT",
    "run_id": "INTEGER NOT NULL",
    "table_name": "TEXT NOT NULL",
    "row_key": "TEXT NOT NULL",
    "action": "TEXT NOT NULL",  # insert or update
    "old_values": "TEXT",  # JSON
    "new_values": "TEXT",  # JSON
    "changed_at": "TEXT NOT NULL",
}


def table_by_name(name: str) -> Table:
    for table in TABLES:
        if table.name == name:
            return table
    raise KeyError(f"Unknown table: {name}")
