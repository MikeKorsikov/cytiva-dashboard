"""Danaher FY2025 10-K acquisition statements on the Overview M&A tile. No network."""

from datetime import date

from src.ingest import store
from src.ingest.company_deals import DANAHER_10K_URL, DEAL_VALUE_USD_M, load_company_deals
from src.metrics import deals as deal_metrics


def _loaded(tmp_path):
    conn = store.connect(tmp_path / "app.db")
    store.create_schema(conn)
    run = store.start_run(conn, "manual")
    load_company_deals(conn, run)
    return conn


def test_abcam_value_is_the_10k_price(tmp_path):
    conn = _loaded(tmp_path)
    value = conn.execute(
        "SELECT value_usd FROM deal WHERE acquirer = 'Danaher' AND announced_date = '2023-12-06'"
    ).fetchone()[0]
    assert value == DEAL_VALUE_USD_M[("Danaher", "2023-12-06")] * 1_000_000 == 5.6e9


def test_no_danaher_acquisition_is_dated_2025(tmp_path):
    conn = _loaded(tmp_path)
    n = conn.execute(
        "SELECT COUNT(*) FROM deal WHERE acquirer = 'Danaher' AND category = 'M&A' "
        "AND announced_date BETWEEN '2025-01-01' AND '2025-12-31'"
    ).fetchone()[0]
    assert n == 0  # the 10-K: no acquisitions in 2025


def test_10k_notes_are_stored_with_the_10k_link_and_not_counted(tmp_path):
    conn = _loaded(tmp_path)
    notes = conn.execute(
        "SELECT text, source_url FROM screen_notes WHERE tab = 'Overview M&A'"
    ).fetchall()
    assert len(notes) == 3
    assert all(n["source_url"] == DANAHER_10K_URL for n in notes)
    assert any("$558 million" in n["text"] for n in notes)
    # The three 2024 businesses are not dated individually, so no deal rows are added for them.
    assert (
        conn.execute(
            "SELECT COUNT(*) FROM deal WHERE acquirer = 'Danaher' AND announced_date LIKE '2024-%' "
            "AND category = 'M&A'"
        ).fetchone()[0]
        == 1
    )  # Genedata only


def test_twelve_month_count_as_of_today(tmp_path):
    conn = _loaded(tmp_path)
    counts = deal_metrics.deal_counts(conn, "Danaher", date(2026, 11, 17))
    assert counts["M&A"]["last_12m"] == 2  # Masimo (Feb 2026) and StatLab (Sep 2026)
