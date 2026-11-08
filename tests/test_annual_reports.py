"""Tests for reading IFRS annual report figures. No network: report pages are fixtures."""

import pytest

from src.ingest import annual_reports as ar
from src.ingest import store


@pytest.mark.parametrize(
    ("line", "label", "expected"),
    [
        ("Sales revenue [9] 3,538.1 3,380.7", "Sales revenue", (3538.1, 3380.7)),
        ("Cost of sales [10] –1,901.3 –1,856.3", "Cost of sales", (-1901.3, -1856.3)),
        ("Net sales 2, 3 34,969 34,759", "Net sales", (34969.0, 34759.0)),
        ("Gross profit 16,654 16,153", "Gross profit", (16654.0, 16153.0)),
        (
            "Investments in intangible assets and tangible assets 9, 10 -1,314 -1,309",
            "Investments in intangible assets and tangible assets",
            (-1314.0, -1309.0),
        ),
    ],
)
def test_values_on_line(line, label, expected):
    assert ar.values_on_line(line, label) == pytest.approx(expected)


def test_missing_label_raises():
    with pytest.raises(ar.ReportError, match="not found"):
        ar.values_on_line("Net sales 34,969 34,759", "Gross profit")


def test_positions_pick_ifrs_columns_in_adjusted_table():
    # Merck Life Science reconciliation: IFRS 2025, adjustment, adjusted 2025, IFRS 2024, ...
    line = "Net sales  8,980  –  8,980  8,916  –  8,916  0.7%"
    assert ar.values_on_line(line, "Net sales", (0, 2)) == (8980.0, 8916.0)
    gross = "Gross profit   4,755  40  4,795  4,766  25  4,791  0.1%"
    assert ar.values_on_line(gross, "Gross profit", (0, 3)) == (4755.0, 4766.0)


def test_positions_out_of_range_raise():
    with pytest.raises(ar.ReportError, match="too few values"):
        ar.values_on_line("Net sales 8,980", "Net sales", (0, 2))


SARTORIUS_INCOME = (
    "Statement of Profit or Loss\nSales revenue [9] 3,538.1 3,380.7\n"
    "Cost of sales [10] –1,901.3 –1,856.3\nGross profit on sales 1,636.7 1,524.4\n"
    "Attributable to: Equity holders of Sartorius AG 154.9 84.0"
)
SARTORIUS_CASH = (
    "Statement of Cash Flows\nCash flow from operating activities 837.0 976.2\n"
    "Investments in intangible and tangible assets [15][16] –441.9 –409.9"
)
MERCK_LS_RECONCILIATION = (
    "Life Science\nReconciliation EBITDA pre\n"
    "Net sales  8,980  –  8,980  8,916  –  8,916  0.7%\n"
    "Cost of sales   -4,225  40  -4,185  -4,150  25  -4,125  1.4%\n"
    "Gross profit   4,755  40  4,795  4,766  25  4,791  0.1%\n"
    "Operating result (EBIT) 1  1,467  1,507"
)


@pytest.fixture
def conn(tmp_path):
    connection = store.connect(tmp_path / "app.db")
    store.create_schema(connection)
    yield connection
    connection.close()


def _report(company_id):
    return next(r for r in ar.REPORTS if r.company_id == company_id)


def test_load_annual_reports_converts_to_usd_at_average_rate(conn, monkeypatch):
    sartorius = _report("Sartorius")
    merck = _report("Merck Life Science")
    pages = {
        "Sartorius": {
            sartorius.income_page: SARTORIUS_INCOME,
            sartorius.cash_flow_page: SARTORIUS_CASH,
        },
        "Merck Life Science": {merck.income_page: MERCK_LS_RECONCILIATION},
    }
    rates = {"EUR": {2025: 1.1302, 2024: 1.0532}}
    monkeypatch.setattr(ar, "pdf_pages", lambda report: pages[report.company_id])
    monkeypatch.setattr(ar, "fx_by_year", lambda currency: rates[currency])
    run_id = store.start_run(conn, "manual")

    ar.load_annual_reports(conn, run_id)

    row = conn.execute(
        "SELECT value_local, value_usd, currency FROM financial_metric "
        "WHERE company_id = 'Sartorius' AND metric = 'revenue' AND fiscal_year = 2025"
    ).fetchone()
    assert row["value_local"] == pytest.approx(3_538_100_000.0)
    assert row["value_usd"] == pytest.approx(3_538_100_000.0 * 1.1302)
    assert row["currency"] == "EUR"
    status = conn.execute(
        "SELECT verification_status FROM financial_metric "
        "WHERE company_id = 'Sartorius' AND metric = 'gross_profit' AND fiscal_year = 2025"
    ).fetchone()["verification_status"]
    assert status == "passed"


def test_merck_life_science_is_a_segment_with_revenue_and_gross_profit_only(conn, monkeypatch):
    merck = _report("Merck Life Science")
    sartorius = _report("Sartorius")
    pages = {
        "Sartorius": {
            sartorius.income_page: SARTORIUS_INCOME,
            sartorius.cash_flow_page: SARTORIUS_CASH,
        },
        "Merck Life Science": {merck.income_page: MERCK_LS_RECONCILIATION},
    }
    monkeypatch.setattr(ar, "pdf_pages", lambda report: pages[report.company_id])
    monkeypatch.setattr(ar, "fx_by_year", lambda currency: {2025: 1.1302, 2024: 1.0532})
    run_id = store.start_run(conn, "manual")

    ar.load_annual_reports(conn, run_id)

    revenue = conn.execute(
        "SELECT value_local, value_usd FROM financial_metric "
        "WHERE company_id = 'Merck Life Science' AND metric = 'revenue' AND fiscal_year = 2025"
    ).fetchone()
    assert revenue["value_local"] == pytest.approx(8_980_000_000.0)
    assert revenue["value_usd"] == pytest.approx(8_980_000_000.0 * 1.1302)
    gross_2024 = conn.execute(
        "SELECT value_local FROM financial_metric "
        "WHERE company_id = 'Merck Life Science' AND metric = 'gross_profit' AND fiscal_year = 2024"
    ).fetchone()["value_local"]
    assert gross_2024 == pytest.approx(4_766_000_000.0)
    level = conn.execute(
        "SELECT group_or_segment FROM company WHERE company_id = 'Merck Life Science'"
    ).fetchone()["group_or_segment"]
    assert level == "segment"
    # The segment reports no net income or cash flow, so none are stored (shown as n/d).
    count = conn.execute(
        "SELECT COUNT(*) FROM financial_metric WHERE company_id = 'Merck Life Science' "
        "AND metric IN ('net_income', 'operating_cash_flow', 'capex')"
    ).fetchone()[0]
    assert count == 0
