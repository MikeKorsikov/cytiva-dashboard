"""Tests for the Overview screen data functions. The screen's tables come from the research sheet
(src/ingest/overview_sheet.py), loaded into a temporary database. No network."""

from datetime import date

import pytest

from src.domain.confidence import row_label
from src.ingest import store
from src.ingest.overview_sheet import load_overview_sheet
from src.metrics import overview


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "app.db"
    conn = store.connect(path)
    store.create_schema(conn)
    load_overview_sheet(conn, store.start_run(conn, "manual"))
    conn.close()
    return overview.connect_readonly(path)


def _financials(db) -> dict:
    return {r["company"]: r for r in overview.peer_financials(db)}


def test_peer_financials_are_the_sheet_figures(db):
    dhr = _financials(db)["Danaher"]
    assert dhr["fiscal_year"] == "FY2025"
    assert dhr["revenue_usd"] == pytest.approx(24568.0e6)
    assert dhr["growth_pct"] == pytest.approx(3.0)
    assert dhr["gross_margin_pct"] == pytest.approx(59.1135)
    assert dhr["fcf_usd"] == pytest.approx(5293.0e6)  # USD reporter: local = USD


def test_sartorius_fcf_in_usd_uses_the_sheets_own_rate(db):
    # Sheet: FCF 395.1 EUR m; revenue 3,997.94 USD m over 3,538 EUR m (the sheet's rate, 1.13).
    srt = _financials(db)["Sartorius"]
    assert srt["fcf_usd"] == pytest.approx(395.1 * 3997.94 / 3538 * 1e6, rel=1e-6)


def test_merck_group_is_named_without_the_suffix(db):
    assert "Merck KGaA" in _financials(db)
    assert "Merck KGaA (group)" not in _financials(db)


def test_peer_medians_match_the_sheet_medians(db):
    rows = overview.peer_financials(db)
    assert overview.peer_median(rows, "growth_pct") == pytest.approx(3.9)  # sheet: 3.9
    assert overview.peer_median(rows, "gross_margin_pct") == pytest.approx(46.2691)  # sheet


def test_basis_per_row_follows_confidence_and_primary_source(db):
    labels = {c: r["evidence_label"] for c, r in _financials(db).items()}
    assert labels["Danaher"] == "Fact"  # H, primary (company release)
    assert labels["Merck KGaA"] == "Fact"  # H, primary (company release)
    assert (
        labels["Sartorius"] == "Signal"
    )  # M: gross profit, net income and cash flow are secondary


def test_sheet_news_is_the_seed_per_company(db):
    items = overview.sheet_news(db)
    assert len(items) == 7
    danaher = next(n for n in items if n["company"] == "Danaher")
    assert danaher["headline"] == "Danaher completes acquisition of Masimo"
    assert danaher["tag"] == "M&A"
    assert danaher["evidence_label"] == "Signal"  # trade press


def test_attention_items_carry_their_sheet_labels(db):
    items = {a["id"]: a for a in overview.attention_items(db)}
    assert sorted(items) == ["AT-01", "AT-02", "AT-03", "AT-04", "AT-05"]
    assert items["AT-01"]["action"] == "ACT"
    assert items["AT-01"]["review_by"] == "2026-12-31"
    # the badge is derived from the sheet's Confidence and Source type (23 Nov 2026 decision)
    badges = {k: row_label(a["confidence"], a["source_type_text"]) for k, a in items.items()}
    assert badges == {
        "AT-01": "Signal",
        "AT-02": "Signal",
        "AT-03": "Signal",
        "AT-04": "Fact",
        "AT-05": "Fact",
    }
    assert {a["evidence_label"] for a in items.values()} == {"Derived"}


def test_implications_are_hypotheses(db):
    items = overview.implications(db)
    assert [i["id"] for i in items] == ["I-01", "I-02", "I-03"]
    assert all(i["evidence_label"] == "Hypothesis" for i in items)


def test_ma_activity_is_none_until_deals_are_loaded(db):
    rows = overview.ma_activity(db, date(2026, 11, 8))
    assert all(r["M&A 12m"] is None and r["Licensing 5y"] is None for r in rows)


def test_peer_median_excludes_the_subject():
    rows = [
        {"company": "Danaher", "gross_margin_pct": 59.1},
        {"company": "Thermo Fisher", "gross_margin_pct": 40.9},
        {"company": "Repligen", "gross_margin_pct": 52.3},
        {"company": "Avantor", "gross_margin_pct": None},
    ]
    assert overview.peer_median(rows, "gross_margin_pct") == pytest.approx(46.6)


def test_best_and_weakest_respect_direction():
    rows = [
        {"company": "A", "growth_pct": 5.0},
        {"company": "B", "growth_pct": -2.0},
        {"company": "C", "growth_pct": None},
    ]
    assert overview.best_worst(rows, "growth_pct") == {"A": "best", "B": "weakest"}


def test_best_worst_needs_two_values():
    assert overview.best_worst([{"company": "A", "growth_pct": 1.0}], "growth_pct") == {}


@pytest.fixture
def feed_db(tmp_path):
    """The feed tables, filled as the price and news feeds fill them."""
    path = tmp_path / "feed.db"
    conn = store.connect(path)
    store.create_schema(conn)
    run_id = store.start_run(conn, "manual")
    load_overview_sheet(conn, run_id)  # the sheet's seed news (fallback)
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
    for url, day, headline in [
        ("https://news.example.com/old", "2026-10-01", "Old news"),
        ("https://news.example.com/new", "2026-11-05", "New news"),
    ]:
        store.upsert(
            conn,
            run_id,
            "news_item",
            {
                **source,
                "url": url,
                "company_id": "Danaher",
                "item_date": day,
                "tag": "M&A",
                "headline": headline,
                "summary": "A",
                "source_type": "news",
                "evidence_label": "Signal",
                "published_date": day,
            },
        )
    conn.close()
    reader = overview.connect_readonly(path)
    yield reader
    reader.close()


def test_share_price_summary_from_the_feed(feed_db):
    dhr = next(p for p in overview.share_prices(feed_db) if p["ticker"] == "DHR")
    assert dhr["last_close_usd"] == pytest.approx(150.0)
    assert dhr["change_12m_pct"] == pytest.approx(50.0)
    assert dhr["as_of"] == "2026-11-06"


def test_share_prices_without_feed_data_are_none(feed_db):
    tmo = next(p for p in overview.share_prices(feed_db) if p["ticker"] == "TMO")
    assert tmo["last_close_usd"] is None


def test_feed_news_is_newest_first(feed_db):
    danaher = [n for n in overview.latest_news(feed_db) if n["company"] == "Danaher"]
    assert danaher[0]["headline"] == "New news"
    assert danaher[0]["evidence_label"] == "Signal"


def test_news_column_uses_the_seed_only_where_the_feed_is_empty(feed_db):
    by_company = {n["company"]: n for n in overview.news_for_screen(feed_db)}
    assert by_company["Danaher"]["seed"] is False
    assert by_company["Danaher"]["headline"] == "New news"
    # Cytiva has no feed item in this database, so the sheet's seed item is shown and marked.
    assert by_company["Cytiva"]["seed"] is True
