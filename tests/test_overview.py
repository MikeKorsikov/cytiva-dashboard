"""Tests for the Overview screen data functions. Uses a temporary database; no network."""

from datetime import date

import pytest

from src.ingest import store
from src.metrics import overview


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "app.db"
    conn = store.connect(path)
    store.create_schema(conn)
    run_id = store.start_run(conn, "manual")
    source = {"source_url": "https://example.com/x", "source_type": "API", "evidence_label": "Fact"}
    for day, close in [("2025-11-07", 100.0), ("2026-11-06", 150.0)]:
        store.upsert(
            conn,
            run_id,
            "share_price_daily",
            {
                **source,
                "ticker": "DHR",
                "price_date": day,
                "close_usd": close,
                "close_local": close,
                "currency": "USD",
                "published_date": day,
            },
        )
    for year, rev, gross, net, ocf, capex in [
        (2024, 1000.0, 580.0, 120.0, 300.0, 50.0),
        (2025, 1100.0, 650.0, 165.0, 400.0, 60.0),
    ]:
        for metric, value in [
            ("revenue", rev),
            ("gross_profit", gross),
            ("net_income", net),
            ("operating_cash_flow", ocf),
            ("capex", capex),
        ]:
            store.upsert(
                conn,
                run_id,
                "financial_metric",
                {
                    **source,
                    "company_id": "DHR",
                    "fiscal_year": year,
                    "metric": metric,
                    "value_usd": value,
                    "value_local": value,
                    "currency": "USD",
                    "published_date": "2026-02-10",
                },
            )
    store.upsert(
        conn,
        run_id,
        "company",
        {
            **source,
            "company_id": "DHR",
            "name": "Danaher",
            "ticker": "DHR",
            "country": "US",
            "reporting_standard": "US GAAP",
            "fiscal_year_end": "12-31",
            "group_or_segment": "group",
            "published_date": None,
        },
    )
    store.upsert(
        conn,
        run_id,
        "news_item",
        {
            **source,
            "url": "https://news.example.com/old",
            "company_id": "Danaher",
            "item_date": "2026-10-01",
            "tag": "Results",
            "headline": "Old news",
            "summary": "A",
            "source_type": "news",
            "evidence_label": "Signal",
            "published_date": "2026-10-01",
        },
    )
    store.upsert(
        conn,
        run_id,
        "news_item",
        {
            **source,
            "url": "https://news.example.com/new",
            "company_id": "Danaher",
            "item_date": "2026-11-05",
            "tag": "M&A",
            "headline": "New news",
            "summary": "B",
            "source_type": "news",
            "evidence_label": "Signal",
            "published_date": "2026-11-05",
        },
    )
    conn.close()
    return overview.connect_readonly(path)


def test_share_price_summary(db):
    dhr = next(p for p in overview.share_prices(db) if p["ticker"] == "DHR")
    assert dhr["last_close_usd"] == pytest.approx(150.0)
    assert dhr["change_12m_pct"] == pytest.approx(50.0)
    assert dhr["as_of"] == "2026-11-06"
    assert dhr["position_in_range"] == pytest.approx(1.0)


def test_share_prices_without_data_are_none(db):
    tmo = next(p for p in overview.share_prices(db) if p["ticker"] == "TMO")
    assert tmo["last_close_usd"] is None
    assert tmo["as_of"] is None


def test_financial_table_latest_year_with_growth_and_margins(db):
    dhr = next(r for r in overview.financial_table(db) if r["company"] == "Danaher")
    assert dhr["fiscal_year"] == 2025
    assert dhr["revenue_usd"] == pytest.approx(1100.0)
    assert dhr["growth_pct"] == pytest.approx(10.0)
    assert dhr["gross_margin_pct"] == pytest.approx(650.0 / 1100.0 * 100)
    assert dhr["net_margin_pct"] == pytest.approx(165.0 / 1100.0 * 100)
    assert dhr["fcf_usd"] == pytest.approx(340.0)


def test_financial_table_missing_company_is_none(db):
    tmo = next(r for r in overview.financial_table(db) if r["company"] == "TMO")
    assert tmo["revenue_usd"] is None
    assert tmo["gross_margin_pct"] is None


def test_latest_news_newest_first(db):
    danaher = [n for n in overview.latest_news(db) if n["company"] == "Danaher"]
    assert danaher[0]["headline"] == "New news"
    assert danaher[0]["tag"] == "M&A"


def test_ma_activity_is_none_until_deals_are_loaded(db):
    rows = overview.ma_activity(db, date(2026, 11, 8))
    assert all(r["M&A 12m"] is None and r["Licensing 5y"] is None for r in rows)
