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


SARTORIUS_INCOME = (
    "Statement of Profit or Loss\nSales revenue [9] 3,538.1 3,380.7\n"
    "Cost of sales [10] –1,901.3 –1,856.3\nGross profit on sales 1,636.7 1,524.4\n"
    "Attributable to: Equity holders of Sartorius AG 154.9 84.0"
)
SARTORIUS_CASH = (
    "Statement of Cash Flows\nCash flow from operating activities 837.0 976.2\n"
    "Investments in intangible and tangible assets [15][16] –441.9 –409.9"
)
GETINGE_INCOME = (
    "Consolidated income statement\nNet sales 2, 3 34,969 34,759\n"
    "Cost of goods sold 4 -18,315 -18,606\nGross profit 16,654 16,153\n"
    "Parent Company's shareholders 2,258 1,638"
)
GETINGE_CASH = (
    "Consolidated cash flow statement\nCash flow from operating activities 3,949 4,577\n"
    "Investments in intangible assets and tangible assets 9, 10 -1,314 -1,309"
)


@pytest.fixture
def conn(tmp_path):
    connection = store.connect(tmp_path / "app.db")
    store.create_schema(connection)
    yield connection
    connection.close()


def test_load_annual_reports_converts_to_usd_at_average_rate(conn, monkeypatch):
    pages = {
        "Sartorius": {
            ar.REPORTS[0].income_page: SARTORIUS_INCOME,
            ar.REPORTS[0].cash_flow_page: SARTORIUS_CASH,
        },
        "Getinge": {
            ar.REPORTS[1].income_page: GETINGE_INCOME,
            ar.REPORTS[1].cash_flow_page: GETINGE_CASH,
        },
    }
    rates = {"EUR": {2025: 1.1302, 2024: 1.0532}, "SEK": {2025: 0.1022, 2024: 0.0913}}
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
    capex = conn.execute(
        "SELECT value_local FROM financial_metric "
        "WHERE company_id = 'Getinge' AND metric = 'capex' AND fiscal_year = 2025"
    ).fetchone()["value_local"]
    assert capex == pytest.approx(1_314_000_000.0)  # outflow stored as a positive amount
    status = conn.execute(
        "SELECT verification_status FROM financial_metric "
        "WHERE company_id = 'Sartorius' AND metric = 'gross_profit' AND fiscal_year = 2025"
    ).fetchone()["verification_status"]
    assert status == "passed"
