"""Overview M&A counts: the sheet's verified deals only. Feed deals are listed, never counted.
No network."""

from datetime import date

from src.ingest import company_deals, store
from src.ingest.overview_sheet import load_overview_sheet
from src.metrics import overview

AS_OF = date(2026, 11, 22)


def _loaded(tmp_path):
    conn = store.connect(tmp_path / "app.db")
    store.create_schema(conn)
    run = store.start_run(conn, "manual")
    company_deals.load_company_deals(conn, run)
    load_overview_sheet(conn, run)
    return conn


def _feed_deal(conn, acquirer, day, headline, category="M&A"):
    conn.execute(
        "INSERT INTO deal (acquirer, announced_date, category, headline, status, source_url, "
        "source_type, evidence_label, loaded_at, verification_status) VALUES (?, ?, ?, ?, "
        "'announced', 'https://news.google.com/rss/articles/x', 'news', 'Signal', "
        "'2026-11-22', 'passed')",
        (acquirer, day, category, headline),
    )


def _row(rows, company):
    return next(r for r in rows if r["company"] == company)


def test_m_and_a_12m_is_the_sheets_verified_deals(tmp_path):
    conn = _loaded(tmp_path)
    ma = overview.ma_activity(conn, AS_OF)
    # Sheet T2 M&A, as its own count rows say: Danaher 1, Merck KGaA 1, Repligen 1, others 0.
    assert _row(ma, "Danaher")["M&A 12m"] == 1
    assert _row(ma, "Merck KGaA")["M&A 12m"] == 1
    assert _row(ma, "Repligen")["M&A 12m"] == 1
    assert _row(ma, "Thermo Fisher")["M&A 12m"] == 0


def test_the_five_year_and_other_columns_are_to_collect(tmp_path):
    conn = _loaded(tmp_path)
    for r in overview.ma_activity(conn, AS_OF):
        assert r["M&A 5y"] is None
        assert r["Licensing 12m"] is None and r["Licensing 5y"] is None
        assert r["Collaboration 12m"] is None and r["Collaboration 5y"] is None


def test_a_feed_deal_is_not_counted_but_is_listed(tmp_path):
    conn = _loaded(tmp_path)
    _feed_deal(conn, "Danaher", "2026-10-01", "Danaher buys a company - Trade press")
    conn.commit()
    assert _row(overview.ma_activity(conn, AS_OF), "Danaher")["M&A 12m"] == 1  # unchanged
    signals = overview.feed_deal_signals(conn, AS_OF)
    assert [s["headline"] for s in signals["shown"]] == ["Danaher buys a company - Trade press"]


def test_feed_signals_outside_twelve_months_are_not_listed(tmp_path):
    conn = _loaded(tmp_path)
    _feed_deal(conn, "Thermo Fisher", "2021-12-08", "Old feed deal")
    conn.commit()
    assert overview.feed_deal_signals(conn, AS_OF)["shown"] == []


def test_no_sheet_deals_means_to_collect(tmp_path):
    conn = store.connect(tmp_path / "empty.db")
    store.create_schema(conn)
    _feed_deal(conn, "Danaher", "2026-10-01", "Feed only")
    conn.commit()
    assert all(r["M&A 12m"] is None for r in overview.ma_activity(conn, AS_OF))
