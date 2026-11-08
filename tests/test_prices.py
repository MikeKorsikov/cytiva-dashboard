"""Tests for the share-price loader. No network access: Yahoo Finance is replaced by fixtures."""

import pandas as pd
import pytest

from src.ingest import prices, store


def _days(n: int, start: str = "2026-01-01") -> pd.DatetimeIndex:
    return pd.date_range(start, periods=n, freq="D")


def test_listed_peers_are_the_shortlist():
    tickers = {p.ticker for p in prices.LISTED_PEERS}
    companies = {p.company for p in prices.LISTED_PEERS}
    assert "Eppendorf" not in companies
    assert "Getinge" not in companies
    # The Merck KGaA group price is shown (group level); the segment is used for financials.
    assert "Merck Life Science" not in companies
    assert "Merck KGaA (group)" in companies
    assert tickers == {"DHR", "TMO", "SRT3.DE", "RGEN", "AVTR", "MRK.DE"}
    assert {p.currency for p in prices.LISTED_PEERS} <= {"USD", "EUR"}


def test_to_usd_applies_same_day_rate():
    days = _days(2)
    local = pd.Series([100.0, 110.0], index=days)
    fx = pd.Series([1.1, 1.2], index=days)
    assert list(prices.to_usd(local, fx)) == pytest.approx([110.0, 132.0])


def test_to_usd_forward_fills_missing_fx_days():
    local = pd.Series([100.0, 110.0, 120.0], index=_days(3))
    fx = pd.Series([1.1], index=_days(1))  # only the first day has a rate
    assert list(prices.to_usd(local, fx)) == pytest.approx([110.0, 121.0, 132.0])


def test_to_usd_without_fx_returns_local_values():
    local = pd.Series([100.0, 110.0], index=_days(2))
    assert list(prices.to_usd(local, None)) == [100.0, 110.0]


def test_usd_fx_is_identity():
    assert prices.fx_to_usd("USD").empty  # no rate needed; to_usd returns local values


def test_summarise_metrics():
    usd = pd.Series([100.0, 150.0, 120.0, 200.0, 180.0])
    result = prices.summarise(usd)
    assert result["last_close_usd"] == 180.0
    assert result["change_12m_pct"] == pytest.approx(80.0)
    assert result["high_52w"] == 200.0
    assert result["low_52w"] == 100.0
    assert result["position_in_range"] == pytest.approx(0.8)


def test_summarise_empty_series():
    result = prices.summarise(pd.Series(dtype=float))
    assert result["last_close_usd"] is None
    assert result["position_in_range"] is None


def test_fetch_history_error_names_the_ticker(tmp_path, monkeypatch):
    class EmptyTicker:
        def __init__(self, _symbol):
            pass

        def history(self, **_kwargs):
            return pd.DataFrame()

    monkeypatch.setattr(prices, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(prices.yf, "Ticker", EmptyTicker)
    with pytest.raises(prices.PriceError, match="no prices for DHR"):
        prices.fetch_history("DHR", use_cache=False)


@pytest.fixture
def conn(tmp_path):
    connection = store.connect(tmp_path / "app.db")
    store.create_schema(connection)
    yield connection
    connection.close()


def test_load_share_prices_writes_usd_rows(conn, monkeypatch):
    days = _days(3)
    frames = {
        peer.ticker: pd.DataFrame({"Close": [100.0, 101.0, 102.0]}, index=days)
        for peer in prices.LISTED_PEERS
    }
    monkeypatch.setattr(prices, "fetch_history", lambda ticker, *a, **k: frames[ticker])
    monkeypatch.setattr(
        prices, "fx_to_usd", lambda currency, *a, **k: pd.Series([2.0, 2.0, 2.0], index=days)
    )
    run_id = store.start_run(conn, "manual")

    written = prices.load_share_prices(conn, run_id)

    assert written == 3 * len(prices.LISTED_PEERS)
    row = conn.execute(
        "SELECT close_usd, close_local, currency, source_url, verification_status "
        "FROM share_price_daily WHERE ticker = 'DHR' AND price_date = '2026-01-01'"
    ).fetchone()
    assert row["close_usd"] == pytest.approx(200.0)
    assert row["close_local"] == pytest.approx(100.0)
    assert row["currency"] == "USD"
    assert row["source_url"] == "https://finance.yahoo.com/quote/DHR/history"
    assert row["verification_status"] == "passed"


def test_load_share_prices_is_idempotent(conn, monkeypatch):
    days = _days(2)
    frame = pd.DataFrame({"Close": [100.0, 101.0]}, index=days)
    monkeypatch.setattr(prices, "fetch_history", lambda ticker, *a, **k: frame)
    monkeypatch.setattr(prices, "fx_to_usd", lambda currency, *a, **k: None)
    run_id = store.start_run(conn, "manual")

    prices.load_share_prices(conn, run_id)
    first_changes = conn.execute("SELECT COUNT(*) FROM change_log").fetchone()[0]
    prices.load_share_prices(conn, run_id)
    second_changes = conn.execute("SELECT COUNT(*) FROM change_log").fetchone()[0]

    assert second_changes == first_changes  # no new change rows for identical data


def test_calendar_days_handles_mixed_exchange_offsets():
    index = ["2026-03-27 00:00:00+01:00", "2026-03-30 00:00:00+02:00"]  # DST change in between
    days = prices.calendar_days(index)
    assert [d.date().isoformat() for d in days] == ["2026-03-27", "2026-03-30"]
