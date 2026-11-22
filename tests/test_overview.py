"""Tests for the Overview screen data functions. The screen's tables come from the research sheet
(src/ingest/overview_sheet.py), loaded into a temporary database. No network."""

from datetime import date

import pytest

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


def test_price_list_is_awaiting_feed_until_the_feed_runs(db):
    rows = overview.price_rows(db)
    assert [r["ticker"] for r in rows] == ["DHR", "TMO", "SRT3.DE", "RGEN", "AVTR", "MRK.DE"]
    assert all(r["last_close"] is None and r["state"] == "awaiting feed" for r in rows)


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


def test_latest_news_is_the_sheet_seed_per_company(db):
    items = overview.latest_news(db)
    assert len(items) == 7
    danaher = next(n for n in items if n["company"] == "Danaher")
    assert danaher["headline"] == "Danaher completes acquisition of Masimo"
    assert danaher["tag"] == "M&A"
    assert danaher["evidence_label"] == "Signal"  # trade press


def test_attention_items_carry_their_sheet_labels(db):
    items = {a["id"]: a for a in overview.attention_items(db)}
    assert sorted(items) == ["AT-01", "AT-02", "AT-03", "AT-04", "AT-05"]
    assert items["AT-01"]["action"] == "ACT"
    assert items["AT-01"]["evidence_label"] == "Fact"
    assert items["AT-02"]["evidence_label"] == "Signal"
    assert items["AT-01"]["review_by"] == "2026-12-31"


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
