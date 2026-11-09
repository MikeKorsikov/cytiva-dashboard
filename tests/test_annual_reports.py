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


def test_positions_pick_columns_in_an_adjusted_table():
    # A table with IFRS and adjusted columns: IFRS 2025, adjustment, adjusted 2025, IFRS 2024, ...
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
# Merck KGaA group, consolidated statements (IFRS, EUR million), lines as printed.
MERCK_GROUP_INCOME = (
    "Consolidated Income Statement\n"
    "Net sales  9  21,102  21,156\n"
    "Cost of sales   10  -8,756  -8,671\n"
    "Gross profit     12,346  12,485\n"
    "Operating result (EBIT) 1    3,601  3,645\n"
    "thereof: attributable to shareholders of Merck KGaA, Darmstadt, Germany   \n"
    "(net income)     2,608  2,777"
)
MERCK_GROUP_CASH = (
    "Consolidated Cash Flow Statement\n"
    "Operating Cash Flow   16  3,932  4,586\n"
    "Payments for investments in intangible assets     -373  -482\n"
    "Proceeds from the disposal of intangible assets     171  18\n"
    "Payments for investments in property, plant and equipment     -1,585  -1,702"
)


@pytest.fixture
def conn(tmp_path):
    connection = store.connect(tmp_path / "app.db")
    store.create_schema(connection)
    yield connection
    connection.close()


def _report(company_id):
    return next(r for r in ar.REPORTS if r.company_id == company_id)


def _pages(sartorius_pages=None, merck_pages=None):
    sartorius = _report("Sartorius")
    merck = _report("Merck KGaA")
    return {
        "Sartorius": sartorius_pages
        or {
            sartorius.income_page: SARTORIUS_INCOME,
            sartorius.cash_flow_page: SARTORIUS_CASH,
        },
        "Merck KGaA": merck_pages
        or {
            merck.income_page: MERCK_GROUP_INCOME,
            merck.cash_flow_page: MERCK_GROUP_CASH,
        },
    }


def test_load_annual_reports_converts_to_usd_at_average_rate(conn, monkeypatch):
    rates = {"EUR": {2025: 1.1302, 2024: 1.0532}}
    pages = _pages()
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


def test_merck_kgaa_is_loaded_at_group_level_with_the_same_metrics_as_peers(conn, monkeypatch):
    pages = _pages()
    monkeypatch.setattr(ar, "pdf_pages", lambda report: pages[report.company_id])
    monkeypatch.setattr(ar, "fx_by_year", lambda currency: {2025: 1.1302, 2024: 1.0532})
    run_id = store.start_run(conn, "manual")

    ar.load_annual_reports(conn, run_id)

    level = conn.execute(
        "SELECT group_or_segment FROM company WHERE company_id = 'Merck KGaA'"
    ).fetchone()["group_or_segment"]
    assert level == "group"
    values = {
        (r["metric"], r["fiscal_year"]): r["value_local"]
        for r in conn.execute(
            "SELECT metric, fiscal_year, value_local FROM financial_metric "
            "WHERE company_id = 'Merck KGaA'"
        )
    }
    assert values[("revenue", 2025)] == pytest.approx(21_102_000_000.0)
    assert values[("gross_profit", 2024)] == pytest.approx(12_485_000_000.0)
    assert values[("net_income", 2025)] == pytest.approx(2_608_000_000.0)
    assert values[("operating_cash_flow", 2025)] == pytest.approx(3_932_000_000.0)
    # Capex is two lines in the statement (intangibles and property, plant and equipment).
    assert values[("capex", 2025)] == pytest.approx((373 + 1585) * 1_000_000.0)
    assert values[("capex", 2024)] == pytest.approx((482 + 1702) * 1_000_000.0)


def test_wrapped_label_is_read_from_its_own_line():
    # The net-income label wraps; the row itself is "(net income)" with two values.
    assert ar.values_on_line(MERCK_GROUP_INCOME, "(net income)") == pytest.approx((2608.0, 2777.0))
