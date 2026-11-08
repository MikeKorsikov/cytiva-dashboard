"""Tests for reading income statement values from a 10-K. No network access."""

import pytest

from src.ingest import tenk_text as tenk

# Excerpt in the shape of Thermo Fisher's income statement (USD millions, most recent year first).
STATEMENT = (
    "Total revenues 44,556 42,879 42,857 Costs and operating expenses: "
    "Cost of product revenues 13,405 12,523 13,168 "
    "Cost of service revenues 12,913 12,654 12,589 "
    "Selling, general and administrative expenses 8,732 8,400 8,300"
)


def test_row_values_reads_three_years_in_order():
    assert tenk.row_values(STATEMENT, "Total revenues") == [44556.0, 42879.0, 42857.0]


def test_row_values_handles_negative_brackets():
    text = "Other income (expense) (12) (7) 3"
    assert tenk.row_values(text, "Other income (expense)") == [-12.0, -7.0, 3.0]


def test_row_values_missing_label_raises():
    with pytest.raises(tenk.TenKError, match="not found"):
        tenk.row_values(STATEMENT, "Gross profit")


def test_cost_of_sales_sums_rows_in_usd():
    labels = tenk.COST_OF_SALES_LABELS["TMO"]
    cost = tenk.cost_of_sales_by_year(STATEMENT, labels, [2025, 2024, 2023])
    assert cost[2025] == pytest.approx((13_405 + 12_913) * 1_000_000)
    assert cost[2024] == pytest.approx((12_523 + 12_654) * 1_000_000)
    assert cost[2023] == pytest.approx((13_168 + 12_589) * 1_000_000)


def test_gross_profit_matches_thermo_fisher_2025_margin():
    labels = tenk.COST_OF_SALES_LABELS["TMO"]
    years = [2025, 2024, 2023]
    revenue = tenk.revenue_by_year(STATEMENT, years)
    cost = tenk.cost_of_sales_by_year(STATEMENT, labels, years)
    gross_2025 = revenue[2025] - cost[2025]
    assert gross_2025 == pytest.approx(18_238 * 1_000_000)
    assert gross_2025 / revenue[2025] * 100 == pytest.approx(40.9, abs=0.05)


def test_document_url_uses_accession_folder():
    filing = {"accession": "0000097745-26-000018", "primary_document": "tmo-20251231.htm"}
    assert tenk.document_url(97745, filing) == (
        "https://www.sec.gov/Archives/edgar/data/97745/000009774526000018/tmo-20251231.htm"
    )
