"""Tests for the financial KPI calculations. No network access."""

import pytest

from src.metrics.fundamentals import free_cash_flow, margin_pct, yoy_growth_pct


def test_yoy_growth():
    assert yoy_growth_pct(110.0, 100.0) == pytest.approx(10.0)
    assert yoy_growth_pct(90.0, 100.0) == pytest.approx(-10.0)


def test_yoy_growth_missing_or_zero_base_is_none():
    assert yoy_growth_pct(None, 100.0) is None
    assert yoy_growth_pct(110.0, None) is None
    assert yoy_growth_pct(110.0, 0.0) is None


def test_margin_pct():
    assert margin_pct(59.1, 100.0) == pytest.approx(59.1)
    assert margin_pct(25.0, 200.0) == pytest.approx(12.5)


def test_margin_missing_or_zero_revenue_is_none():
    assert margin_pct(None, 100.0) is None
    assert margin_pct(10.0, 0.0) is None


def test_free_cash_flow_subtracts_capex():
    assert free_cash_flow(5_000.0, 1_000.0) == pytest.approx(4_000.0)


def test_free_cash_flow_accepts_negative_capex_sign():
    # Some filings report capex as a negative cash flow; the amount spent is what counts.
    assert free_cash_flow(5_000.0, -1_000.0) == pytest.approx(4_000.0)


def test_free_cash_flow_missing_input_is_none():
    assert free_cash_flow(None, 1_000.0) is None
    assert free_cash_flow(5_000.0, None) is None
