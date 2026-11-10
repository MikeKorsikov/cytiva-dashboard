"""Bioprocessing revenue and market size for the market share tile (Competitor coverage, Tile 3).

Entered by hand from company releases and free public summaries. Each row carries the source
URL, the wording the source uses, its confidence mark and, where a currency conversion is
needed, the FX rate and its source. Nothing is estimated here: a value the sources do not give
is stored as "not_disclosed" with no number. Forecast years are rejected.

Value kinds:
- reported: stated in the source as a figure.
- rounded: the source states a rounded figure (for example "EUR 3.8 billion").
- at_least: the source states a floor (for example "over $6B").
- not_disclosed: the company does not disclose the figure separately; no number is stored.
"""

from __future__ import annotations

import sqlite3

from src.ingest import store

VALUE_KINDS = ("reported", "rounded", "at_least", "not_disclosed")
CONFIDENCE = ("H", "M", "L")
FORECAST_CUTOFF_YEAR = 2025  # the latest completed fiscal year used by the tile

SARTORIUS_RELEASE = (
    "https://www.sartorius.com/en/company/newsroom/corporate-news/"
    "preliminary-full-year-results-2025-sartorius-group-1793940"
)
REPLIGEN_RELEASE = (
    "https://investors.repligen.com/press-releases/news-details/2026/"
    "Repligen-Reports-Fourth-Quarter-and-Full-Year-2025-Financial-Results-and-Provides-2026-"
    "Guidance/default.aspx"
)
MERCK_RELEASE = "https://www.emdgroup.com/en/news/q4-2025-05-03-2026"
DANAHER_SUMMARY = (
    "https://quartr.com/events/danaher-corporation-dhr-corporate-presentation_33n0UmzL"
)
ECB_FX_SOURCE = (
    "https://www.suomenpankki.fi/en/statistics/interest-rates-and-exchange-rates/"
    "exchange-rates/average-annual-exchange-rates-for-the-year-2025/"
)
GMI_SOURCE = "https://www.gminsights.com/industry-analysis/bioprocessing-equipment-market"
REPLIGEN_PRESENTATION = (
    "https://s205.q4cdn.com/906585988/files/doc_presentations/2026/Mar/10/"
    "Repligen-RGEN-Investor-Presentation-March-2026.pdf"
)

# EUR to USD, ECB reference rate, 2025 annual average (USD per EUR).
FX_EUR_2025 = 1.1300

# Revenue and growth rows. Money in millions of the stated currency.
# (company_id, metric, fiscal_period, value, currency, value_kind, basis, confidence,
#  disclosure, source_title, source_url, fx_rate, fx_source_url, note)
REVENUE_OBSERVATIONS: tuple[tuple, ...] = (
    (
        "Danaher",
        "bioprocessing_revenue",
        "FY2025",
        6000,
        "USD",
        "at_least",
        None,
        "M",
        "Bioprocessing revenue exceeds $6B (2025), over 80% from monoclonal antibodies",
        "Danaher corporate presentation summary (Quartr)",
        DANAHER_SUMMARY,
        1.0,
        None,
        "Secondary summary of the company presentation; the Danaher filing giving the exact "
        "figure was not found. Stored as a floor.",
    ),
    (
        "Sartorius",
        "bioprocessing_revenue",
        "FY2025",
        2865,
        "EUR",
        "reported",
        None,
        "H",
        "Sales revenue rose by 9.5 percent in constant currencies (reported: 6.5 percent) "
        "to 2,865 million euros",
        "Sartorius preliminary full-year results 2025, Bioprocess Solutions",
        SARTORIUS_RELEASE,
        FX_EUR_2025,
        ECB_FX_SOURCE,
        "Bioprocess Solutions division. Includes consumables and equipment.",
    ),
    (
        "Merck KGaA",
        "bioprocessing_revenue",
        "FY2025",
        3800,
        "EUR",
        "rounded",
        None,
        "M",
        "Process Solutions: net sales of EUR 3.8 billion in 2025",
        "Merck KGaA Q4 2025 results, Process Solutions",
        MERCK_RELEASE,
        FX_EUR_2025,
        ECB_FX_SOURCE,
        "Process Solutions includes non-biologics pharma manufacturing materials. The annual "
        "report table gives EUR 3,785m (secondary summary). The release page could not be "
        "read directly.",
    ),
    (
        "Repligen",
        "bioprocessing_revenue",
        "FY2025",
        738,
        "USD",
        "reported",
        None,
        "H",
        "bringing our full year 2025 revenue to $738 million, compared to $634 million",
        "Repligen Q4 and full-year 2025 results",
        REPLIGEN_RELEASE,
        1.0,
        None,
        "Pure-play bioprocessing: total revenue.",
    ),
    # Growth, as disclosed for FY2025.
    (
        "Sartorius",
        "bioprocessing_growth",
        "FY2025",
        9.5,
        "%",
        "reported",
        "constant_currency",
        "H",
        "Sales revenue rose by 9.5 percent in constant currencies",
        "Sartorius preliminary full-year results 2025, Bioprocess Solutions",
        SARTORIUS_RELEASE,
        None,
        None,
        None,
    ),
    (
        "Merck KGaA",
        "bioprocessing_growth",
        "FY2025",
        10.7,
        "%",
        "reported",
        "organic",
        "M",
        "Process Solutions grew organically by 10.7% year-on-year",
        "Merck KGaA Q4 2025 results, Process Solutions",
        MERCK_RELEASE,
        None,
        None,
        "Secondary summary of the release; the release page could not be read directly.",
    ),
    (
        "Repligen",
        "bioprocessing_growth",
        "FY2025",
        14.0,
        "%",
        "reported",
        "organic",
        "H",
        "14% organic in FY25",
        "Repligen Q4 and full-year 2025 results",
        REPLIGEN_RELEASE,
        None,
        None,
        None,
    ),
    (
        "Danaher",
        "bioprocessing_growth",
        "FY2025",
        None,
        "%",
        "not_disclosed",
        None,
        "L",
        "Bioprocessing growth is given by segment and product, not as one figure",
        "Danaher Q4 and full-year 2025 results",
        DANAHER_SUMMARY,
        None,
        None,
        "No single FY2025 bioprocessing growth figure was found in a primary document. Shown as "
        "to collect.",
    ),
)

# Market size denominators. Values in USD billions.
# (scope, base_year, value_usd_bn, value_kind, definition, confidence, disclosure,
#  source_title, source_url, note)
MARKET_SIZES: tuple[tuple, ...] = (
    (
        "narrow_company_defined",
        2025,
        20.0,
        "at_least",
        "Global bioprocessing market as framed by Repligen (company definition)",
        "M",
        "$20B+ global bioprocessing market",
        "Repligen investor presentation, March 2026",
        REPLIGEN_PRESENTATION,
        "Taken from secondary summaries of the presentation. The base year is not stated in "
        "them; 2025 is assumed. Addressable market figures differ between summaries ($12bn, "
        "$13bn), so they are not used.",
    ),
    (
        "broad_third_party",
        2025,
        48.1,
        "reported",
        "Bioprocessing equipment market (GMI). Equipment only; consumables and reagents are "
        "excluded",
        "M",
        "The global bioprocessing equipment market was valued at USD 48.1 billion in 2025",
        "Global Market Insights, bioprocessing equipment market (published August 2026)",
        GMI_SOURCE,
        "Base year 2025 (a completed year, not a forecast). Scope differs from the supplier "
        "numerators, which include consumables.",
    ),
)


def validate_revenue(row: tuple) -> list[str]:
    """Problems with one revenue or growth row. Empty list means the row is acceptable."""
    (
        company,
        metric,
        period,
        value,
        currency,
        kind,
        basis,
        conf,
        disclosure,
        title,
        url,
        fx,
        fx_url,
        _note,
    ) = row
    problems = []
    if not url or not url.startswith("https://"):
        problems.append(f"{company} {metric}: no source URL")
    if conf not in CONFIDENCE:
        problems.append(f"{company} {metric}: confidence {conf!r} is not H, M or L")
    if kind not in VALUE_KINDS:
        problems.append(f"{company} {metric}: value kind {kind!r} is not allowed")
    if not disclosure or not title:
        problems.append(f"{company} {metric}: disclosure text and source title are required")
    year = _fiscal_year(period)
    if year is None or year > FORECAST_CUTOFF_YEAR:
        problems.append(f"{company} {metric}: period {period} is not a completed year")
    if kind == "not_disclosed" and value is not None:
        problems.append(f"{company} {metric}: a not-disclosed row must not carry a value")
    if kind != "not_disclosed" and value is None:
        problems.append(f"{company} {metric}: a value is required")
    if metric == "bioprocessing_revenue" and kind != "not_disclosed":
        if fx is None or (currency != "USD" and not fx_url):
            problems.append(f"{company}: a non-USD value needs an FX rate and its source")
    return problems


def validate_market(row: tuple) -> list[str]:
    scope, year, value, kind, definition, conf, disclosure, title, url, _note = row
    problems = []
    if not url or not url.startswith("https://"):
        problems.append(f"market {scope}: no source URL")
    if year > FORECAST_CUTOFF_YEAR:
        problems.append(f"market {scope}: base year {year} is a forecast year")
    if conf not in CONFIDENCE:
        problems.append(f"market {scope}: confidence {conf!r} is not H, M or L")
    if kind not in VALUE_KINDS or kind == "not_disclosed":
        problems.append(f"market {scope}: value kind {kind!r} is not allowed")
    if value is None or value <= 0:
        problems.append(f"market {scope}: a positive value is required")
    if not definition or not disclosure or not title:
        problems.append(f"market {scope}: definition, disclosure and source title are required")
    return problems


def _fiscal_year(period: str) -> int | None:
    if period.startswith("FY") and period[2:].isdigit():
        return int(period[2:])
    return None


def validate_all() -> list[str]:
    problems = []
    for row in REVENUE_OBSERVATIONS:
        problems.extend(validate_revenue(row))
    for row in MARKET_SIZES:
        problems.extend(validate_market(row))
    return problems


def load_bioprocess_share(conn: sqlite3.Connection, run_id: int) -> int:
    """Store the validated rows. Rows that fail validation are not written."""
    problems = validate_all()
    if problems:
        raise ValueError("bioprocess share rows failed validation: " + "; ".join(problems))
    written = 0
    store.upsert(
        conn,
        run_id,
        "fx_rate",
        {
            "currency": "EUR",
            "period": "2025",
            "rate_type": "average",
            "rate_to_usd": FX_EUR_2025,
        },
    )
    for row in REVENUE_OBSERVATIONS:
        (
            company,
            metric,
            period,
            value,
            currency,
            kind,
            basis,
            conf,
            disclosure,
            title,
            url,
            fx,
            fx_url,
            note,
        ) = row
        value_usd = None if value is None else round(value * (fx or 1.0), 2)
        if metric == "bioprocessing_growth":
            value_usd = None
        store.upsert(
            conn,
            run_id,
            "revenue_observation",
            {
                "company_id": company,
                "metric": metric,
                "fiscal_period": period,
                "value": value,
                "currency": currency,
                "value_usd": value_usd,
                "fx_rate": fx,
                "fx_source_url": fx_url,
                "value_kind": kind,
                "basis": basis,
                "disclosure": disclosure,
                "confidence": conf,
                "source_title": title,
                "note": note,
                "source_url": url,
                "source_type": "document",
                "published_date": None,
                "evidence_label": "Fact" if kind == "reported" else "Signal",
            },
        )
        written += 1
    for row in MARKET_SIZES:
        scope, year, value, kind, definition, conf, disclosure, title, url, note = row
        store.upsert(
            conn,
            run_id,
            "market_size",
            {
                "scope": scope,
                "base_year": year,
                "value_usd_bn": value,
                "value_kind": kind,
                "definition": definition,
                "confidence": conf,
                "disclosure": disclosure,
                "source_title": title,
                "note": note,
                "source_url": url,
                "source_type": "document",
                "published_date": None,
                "evidence_label": "Fact",
            },
        )
        written += 1
    return written
