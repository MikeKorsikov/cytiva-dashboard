"""Tests for curated rankings. No network access."""

import pytest

from src.ingest import rankings, store
from src.metrics import overview


@pytest.fixture
def conn(tmp_path):
    connection = store.connect(tmp_path / "app.db")
    store.create_schema(connection)
    yield connection
    connection.close()


FORBES_URL = "https://www.forbes.com/lists/global2000/"


def test_no_mockup_rankings_are_stored(conn):
    # The sheet's T1 Rankings tab holds no values yet (every rank is To collect), so nothing
    # is loaded until the ranks are taken from the Forbes list itself.
    run_id = store.start_run(conn, "manual")
    assert rankings.load_curated_rankings(conn, run_id) == 0
    assert conn.execute("SELECT COUNT(*) FROM ranking").fetchone()[0] == 0


def test_removed_mockup_rows_are_cleared_on_reload(conn):
    run_id = store.start_run(conn, "manual")
    conn.execute(
        "INSERT INTO ranking (company_id, ranking, year, value, source_url, source_type, "
        "published_date, evidence_label, loaded_at, verification_status) VALUES "
        "('Danaher', ?, 2026, '267', ?, 'curated', '2026-11-08', 'Fact', '2026-11-08', 'passed')",
        (rankings.GLOBAL_2000, FORBES_URL),
    )
    rankings.load_curated_rankings(conn, run_id)
    assert conn.execute("SELECT COUNT(*) FROM ranking").fetchone()[0] == 0


def test_ranking_table_shows_none_until_collected(conn):
    run_id = store.start_run(conn, "manual")
    rankings.load_curated_rankings(conn, run_id)
    table = {r["company"]: r for r in overview.ranking_table(conn, rankings.GLOBAL_2000)}
    assert table["Danaher"]["2026"] is None
    assert table["Danaher"]["2025"] is None
    assert table["Repligen"]["2026"] is None
    assert "Eppendorf" not in table


def test_merck_group_rank_is_shown_like_danaher_group():
    assert "Merck KGaA" in overview.RANKING_COMPANIES
    assert "Danaher" in overview.RANKING_COMPANIES
