"""Danaher FY2025 10-K acquisition statements on the Overview M&A tile. No network."""

from datetime import date

from src.ingest import store
from src.ingest.company_deals import DANAHER_10K_NOTES, DANAHER_10K_URL, load_company_deals
from src.metrics import deals as deal_metrics


def _loaded(tmp_path):
    conn = store.connect(tmp_path / "app.db")
    store.create_schema(conn)
    run = store.start_run(conn, "manual")
    load_company_deals(conn, run)
    return conn


def test_abcam_is_not_a_deal_row_but_its_price_stays_in_the_10k_note(tmp_path):
    # Abcam (Dec 2023) is not in the sheet's M&A tab, so it is not a deal row. The 10-K price
    # stays in the sourced note on the tile.
    conn = _loaded(tmp_path)
    n = conn.execute(
        "SELECT COUNT(*) FROM deal WHERE acquirer = 'Danaher' AND announced_date = '2023-12-06'"
    ).fetchone()[0]
    assert n == 0
    assert any("$5.6 billion" in note for note in DANAHER_10K_NOTES)


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
    # The sheet has no 2024 Danaher deal row (the 10-K's three 2024 businesses are not dated).
    assert (
        conn.execute(
            "SELECT COUNT(*) FROM deal WHERE acquirer = 'Danaher' AND announced_date LIKE '2024-%' "
            "AND category = 'M&A'"
        ).fetchone()[0]
        == 0
    )


def test_twelve_month_count_as_of_today(tmp_path):
    conn = _loaded(tmp_path)
    counts = deal_metrics.deal_counts(conn, "Danaher", date(2026, 11, 17))
    assert counts["M&A"]["last_12m"] == 1  # Masimo (Feb 2026), as the sheet's count row says
