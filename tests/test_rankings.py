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


def test_curated_rankings_are_loaded_with_source_and_date(conn):
    run_id = store.start_run(conn, "manual")
    assert rankings.load_curated_rankings(conn, run_id) == len(rankings.CURATED_RANKINGS)
    row = conn.execute(
        "SELECT value, source_url, source_type, published_date FROM ranking "
        "WHERE company_id = 'Thermo Fisher' AND year = 2026"
    ).fetchone()
    assert row["value"] == "155"
    assert row["source_url"] == rankings.GLOBAL_2000_URL
    assert row["source_type"] == "curated"
    assert row["published_date"] == rankings.ENTERED_ON


def test_ranking_table_shows_none_for_unranked_companies(conn):
    run_id = store.start_run(conn, "manual")
    rankings.load_curated_rankings(conn, run_id)
    table = {r["company"]: r for r in overview.ranking_table(conn, rankings.GLOBAL_2000)}
    assert table["Danaher"]["2026"] == "267"
    assert table["Danaher"]["2025"] == "241"
    assert table["Repligen"]["2026"] is None
    assert table["Eppendorf"]["2025"] is None


def test_merck_group_is_not_in_the_ranking_table():
    assert "Merck KGaA" not in overview.RANKING_COMPANIES
