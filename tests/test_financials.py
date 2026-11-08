"""Tests for the EDGAR annual financials loader. No network access: facts are fixtures."""

import pytest

from src.ingest import edgar, financials, store


def _row(val, start, end, filed, accn="0000001-26-000001", form="10-K", fp="FY"):
    return {
        "val": val,
        "start": start,
        "end": end,
        "filed": filed,
        "accn": accn,
        "form": form,
        "fp": fp,
    }


def test_annual_values_keeps_full_year_10k_only():
    facts = {
        "facts": {
            "us-gaap": {
                "Revenues": {
                    "units": {
                        "USD": [
                            _row(100.0, "2025-01-01", "2025-12-31", "2026-02-10"),
                            _row(
                                25.0, "2025-10-01", "2025-12-31", "2026-02-10"
                            ),  # quarter: ignored
                            _row(
                                999.0, "2025-01-01", "2025-12-31", "2026-05-01", form="10-Q"
                            ),  # not 10-K
                        ]
                    }
                }
            }
        }
    }
    values = financials.annual_values(facts, ("Revenues",))
    assert values == {
        2025: {
            "value": 100.0,
            "end": "2025-12-31",
            "filed": "2026-02-10",
            "accn": "0000001-26-000001",
        }
    }


def test_annual_values_keeps_latest_filing_for_a_year():
    facts = {
        "facts": {
            "us-gaap": {
                "Revenues": {
                    "units": {
                        "USD": [
                            _row(100.0, "2024-01-01", "2024-12-31", "2025-02-10", accn="A"),
                            _row(
                                105.0, "2024-01-01", "2024-12-31", "2026-02-10", accn="B"
                            ),  # restated later
                        ]
                    }
                }
            }
        }
    }
    assert financials.annual_values(facts, ("Revenues",))[2024]["value"] == 105.0


def test_annual_values_uses_first_concept_that_has_data():
    facts = {
        "facts": {
            "us-gaap": {
                "Revenues": {"units": {"USD": []}},
                "SalesRevenueNet": {
                    "units": {"USD": [_row(7.0, "2025-01-01", "2025-12-31", "2026-02-10")]}
                },
            }
        }
    }
    values = financials.annual_values(facts, ("Revenues", "SalesRevenueNet"))
    assert values[2025]["value"] == 7.0


def test_gross_profit_derived_when_not_reported():
    facts = {
        "facts": {
            "us-gaap": {
                "RevenueFromContractWithCustomerExcludingAssessedTax": {
                    "units": {"USD": [_row(1000.0, "2025-01-01", "2025-12-31", "2026-02-10")]}
                },
                "CostOfRevenue": {
                    "units": {"USD": [_row(400.0, "2025-01-01", "2025-12-31", "2026-02-10")]}
                },
            }
        }
    }
    gross = financials._metric_by_year(facts)["gross_profit"]
    assert gross[2025]["value"] == pytest.approx(600.0)


def test_free_cash_flow_is_operating_cash_flow_minus_capex():
    facts = {
        "facts": {
            "us-gaap": {
                "NetCashProvidedByUsedInOperatingActivities": {
                    "units": {"USD": [_row(5000.0, "2025-01-01", "2025-12-31", "2026-02-10")]}
                },
                "PaymentsToAcquirePropertyPlantAndEquipment": {
                    "units": {"USD": [_row(1000.0, "2025-01-01", "2025-12-31", "2026-02-10")]}
                },
            }
        }
    }
    fcf = financials._metric_by_year(facts)["free_cash_flow"]
    assert fcf[2025]["value"] == pytest.approx(4000.0)


@pytest.fixture
def conn(tmp_path):
    connection = store.connect(tmp_path / "app.db")
    store.create_schema(connection)
    yield connection
    connection.close()


def test_load_edgar_financials_writes_company_and_metric_rows(conn, monkeypatch):
    facts = {
        "facts": {
            "us-gaap": {
                "RevenueFromContractWithCustomerExcludingAssessedTax": {
                    "units": {
                        "USD": [
                            _row(
                                1000.0,
                                "2025-01-01",
                                "2025-12-31",
                                "2026-02-10",
                                accn="0001-26-000001",
                            )
                        ]
                    }
                },
                "GrossProfit": {
                    "units": {
                        "USD": [
                            _row(
                                600.0,
                                "2025-01-01",
                                "2025-12-31",
                                "2026-02-10",
                                accn="0001-26-000001",
                            )
                        ]
                    }
                },
            }
        }
    }
    monkeypatch.setattr(edgar, "cik_for_ticker", lambda ticker: 123)
    monkeypatch.setattr(edgar, "fetch_company_facts", lambda cik: facts)
    run_id = store.start_run(conn, "manual")

    written = financials.load_edgar_financials(conn, run_id)

    assert written == 2 * len(financials.US_PEERS)
    company = conn.execute(
        "SELECT name, reporting_standard FROM company WHERE company_id = 'DHR'"
    ).fetchone()
    assert (company["name"], company["reporting_standard"]) == ("Danaher", "US GAAP")
    metric = conn.execute(
        "SELECT value_usd, currency, source_url, verification_status FROM financial_metric "
        "WHERE company_id = 'DHR' AND metric = 'revenue' AND fiscal_year = 2025"
    ).fetchone()
    assert metric["value_usd"] == pytest.approx(1000.0)
    assert metric["currency"] == "USD"
    assert metric["source_url"] == "https://www.sec.gov/Archives/edgar/data/123/000126000001/"
    assert metric["verification_status"] == "passed"


def test_gross_profit_above_revenue_is_unverified(conn, monkeypatch):
    facts = {
        "facts": {
            "us-gaap": {
                "RevenueFromContractWithCustomerExcludingAssessedTax": {
                    "units": {"USD": [_row(1000.0, "2025-01-01", "2025-12-31", "2026-02-10")]}
                },
                "GrossProfit": {
                    "units": {"USD": [_row(1200.0, "2025-01-01", "2025-12-31", "2026-02-10")]}
                },
            }
        }
    }
    monkeypatch.setattr(edgar, "cik_for_ticker", lambda ticker: 123)
    monkeypatch.setattr(edgar, "fetch_company_facts", lambda cik: facts)
    run_id = store.start_run(conn, "manual")
    financials.load_edgar_financials(conn, run_id)
    status = conn.execute(
        "SELECT verification_status FROM financial_metric "
        "WHERE company_id = 'DHR' AND metric = 'gross_profit'"
    ).fetchone()["verification_status"]
    assert status == "unverified"
