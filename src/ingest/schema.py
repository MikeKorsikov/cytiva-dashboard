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
    Table(
        "footprint",
        ("company_id", "region_id", "product_family"),
        {
            "company_id": "TEXT NOT NULL",
            "region_id": "TEXT NOT NULL",
            "product_family": "TEXT NOT NULL",
            "status": "TEXT NOT NULL",  # Made, Partial, Not made
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
        "estate_item",
        ("product",),
        {
            "product": "TEXT NOT NULL",
            "where_used": "TEXT",
            "vendor_support_status": "TEXT",
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
    Table(
        "incident",
        ("vendor", "incident_date", "title"),
        {
            "vendor": "TEXT NOT NULL",
            "incident_date": "TEXT NOT NULL",
            "title": "TEXT NOT NULL",
            "incident_type": "TEXT",
            "cve": "TEXT",
            "estate_link": "TEXT",
            "relevance": "TEXT",
        },
    ),
    # Screen 6 (China): Chinese challengers and Danaher's China vendors. Amounts in USD.
    Table(
        "challenger_coverage",
        ("company", "product_family", "step_or_family"),
        {
            "company": "TEXT NOT NULL",
            "product_family": "TEXT NOT NULL",
            "step_or_family": "TEXT NOT NULL",
            "status": "TEXT NOT NULL",  # Made, Partial, Not made
        },
    ),
    Table(
        "cn_financial",
        ("company", "stock_code", "fiscal_year", "metric"),
        {
            "company": "TEXT NOT NULL",
            "stock_code": "TEXT",
            "fiscal_year": "INTEGER NOT NULL",
            "metric": "TEXT NOT NULL",
            "value_usd": "REAL",
            "value_local": "REAL",
            "currency": "TEXT",  # local currency code, e.g. CNY
            "cny_usd_rate": "REAL",  # annual average rate used for conversion
        },
    ),
    Table(
        "vendor_link",
        ("vendor", "danaher_company", "supplies"),
        {
            "vendor": "TEXT NOT NULL",
            "danaher_company": "TEXT NOT NULL",
            "supplies": "TEXT NOT NULL",
            "confirmed": "TEXT NOT NULL",  # confirmed or to confirm
            "since": "TEXT",
            "used_outside_china": "TEXT",  # yes, no or unknown
        },
    ),
    Table(
        "opportunity",
        ("title",),
        {
            "title": "TEXT NOT NULL",
            "reason": "TEXT",
            "product_lines": "TEXT",
            "evidence_label": "TEXT",
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
