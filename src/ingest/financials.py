"""Annual financials for US peers, from SEC EDGAR XBRL company facts (CD-3, screen 1).

Only full-year values from 10-K filings are used. Where a year appears in more than one
filing, the most recently filed value is kept. Each metric tries its XBRL concepts in order
and uses the first one the company reports. All values are USD (US filers).
"""

from __future__ import annotations

import sqlite3
from datetime import date

from src.ingest import edgar, store
from src.ingest.checks import check_range, check_segment_within_group
from src.metrics.fundamentals import free_cash_flow

KEEP_YEARS = 3  # latest fiscal years stored per company


# (ticker, company name). Company id is the ticker.
US_PEERS: tuple[tuple[str, str], ...] = (
    ("DHR", "Danaher"),
    ("TMO", "Thermo Fisher"),
    ("RGEN", "Repligen"),
    ("AVTR", "Avantor"),
)

# metric -> XBRL concepts in order of preference (us-gaap taxonomy)
CONCEPTS: dict[str, tuple[str, ...]] = {
    "revenue": (
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
        "SalesRevenueNet",
    ),
    "gross_profit": ("GrossProfit",),
    "cost_of_revenue": ("CostOfRevenue", "CostOfGoodsAndServicesSold"),
    "net_income": ("NetIncomeLoss",),
    "operating_cash_flow": ("NetCashProvidedByUsedInOperatingActivities",),
    "capex": ("PaymentsToAcquirePropertyPlantAndEquipment",),
    "sga_expense": ("SellingGeneralAndAdministrativeExpense",),
}


def _days(start: str, end: str) -> int:
    return (date.fromisoformat(end) - date.fromisoformat(start)).days


def annual_values(facts: dict, concepts: tuple[str, ...]) -> dict[int, dict]:
    """Full-year 10-K values by fiscal year.

    Concepts are tried in order, and each year takes the first concept that reports it. A
    company can switch concept between years (Repligen reports revenue under two concepts).

    Returns {fiscal_year: {"value", "end", "filed", "accn"}}. Fiscal year is the calendar
    year of the period end. Quarterly and cumulative periods are ignored.
    """
    us_gaap = facts.get("facts", {}).get("us-gaap", {})
    found: dict[int, dict] = {}
    for concept in concepts:
        units = us_gaap.get(concept, {}).get("units", {}).get("USD", [])
        by_year: dict[int, dict] = {}
        for row in units:
            if row.get("form") != "10-K" or row.get("fp") != "FY":
                continue
            start, end = row.get("start"), row.get("end")
            if not start or not end or not 350 <= _days(start, end) <= 380:
                continue
            year = int(end[:4])
            current = by_year.get(year)
            if current is None or row["filed"] > current["filed"]:
                by_year[year] = {
                    "value": float(row["val"]),
                    "end": end,
                    "filed": row["filed"],
                    "accn": row["accn"],
                }
        for year, item in by_year.items():
            found.setdefault(year, item)
    return found


def _metric_by_year(facts: dict) -> dict[str, dict[int, dict]]:
    values = {metric: annual_values(facts, concepts) for metric, concepts in CONCEPTS.items()}
    # Gross profit: if not reported, derive it from revenue and cost of revenue.
    if not values["gross_profit"]:
        derived = {}
        for year, rev in values["revenue"].items():
            cost = values["cost_of_revenue"].get(year)
            if cost:
                derived[year] = {
                    "value": rev["value"] - cost["value"],
                    "end": rev["end"],
                    "filed": max(rev["filed"], cost["filed"]),
                    "accn": rev["accn"],
                }
        values["gross_profit"] = derived
    # Free cash flow: operating cash flow minus capex, where both are reported.
    fcf = {}
    for year, ocf in values["operating_cash_flow"].items():
        capex = values["capex"].get(year)
        if capex:
            amount = free_cash_flow(ocf["value"], capex["value"])
            fcf[year] = {
                "value": amount,
                "end": ocf["end"],
                "filed": max(ocf["filed"], capex["filed"]),
                "accn": ocf["accn"],
            }
    values["free_cash_flow"] = fcf
    return values


def _filing_url(cik: int, accn: str) -> str:
    return f"https://www.sec.gov/Archives/edgar/data/{cik}/{accn.replace('-', '')}/"


def load_edgar_financials(conn: sqlite3.Connection, run_id: int) -> int:
    """Load company rows and annual USD metrics for each US peer. Returns rows written."""
    written = 0
    for ticker, name in US_PEERS:
        cik = edgar.cik_for_ticker(ticker)
        facts = edgar.fetch_company_facts(cik)
        company_row = {
            "company_id": ticker,
            "name": name,
            "ticker": ticker,
            "country": "US",
            "reporting_standard": "US GAAP",
            "fiscal_year_end": "12-31",
            "group_or_segment": "group",
            "source_url": f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}",
            "source_type": "API",
            "published_date": None,
            "evidence_label": "Fact",
        }
        store.upsert(conn, run_id, "company", company_row)

        metrics = _metric_by_year(facts)
        latest_years = sorted({y for m in metrics.values() for y in m})[-KEEP_YEARS:]
        for year in latest_years:
            revenue = metrics["revenue"].get(year)
            for metric, by_year in metrics.items():
                item = by_year.get(year)
                if item is None or item["value"] is None:
                    continue
                problems = []
                if metric == "revenue":
                    problems += check_range("revenue", item["value"], 0.0, 1e12)
                if metric == "gross_profit" and revenue:
                    problems += check_segment_within_group(
                        "gross_profit", item["value"], revenue["value"]
                    )
                row = {
                    "company_id": ticker,
                    "fiscal_year": year,
                    "metric": metric,
                    "value_usd": item["value"],
                    "value_local": item["value"],
                    "currency": "USD",
                    "source_url": _filing_url(cik, item["accn"]),
                    "source_type": "API",
                    "published_date": item["filed"],
                    "evidence_label": "Fact",
                }
                status = store.upsert(
                    conn, run_id, "financial_metric", row, extra_problems=problems
                )
                if status != "rejected":
                    written += 1
    return written
