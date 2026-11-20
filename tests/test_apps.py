"""Screen 5 applications ranking: loaded from the research sheet rows 2 to 14, no URL."""

import pytest

from src.ingest import store
from src.ingest.technology import DATA_DIR, load_apps


@pytest.fixture
def conn(tmp_path):
    connection = store.connect(tmp_path / "app.db")
    store.create_schema(connection)
    yield connection
    connection.close()


def test_thirteen_applications_are_loaded_as_hypothesis(conn):
    with (DATA_DIR / "apps.csv").open(encoding="utf-8") as handle:
        expected = sum(1 for _ in handle) - 1
    assert expected == 13
    run_id = store.start_run(conn, "manual")
    assert load_apps(conn, run_id) == expected
    row = conn.execute(
        "SELECT rank_no, score, evidence_label, source_url FROM tech_apps WHERE name = ?",
        ("Oracle E-Business Suite",),
    ).fetchone()
    assert (row["rank_no"], row["score"]) == (1, 10)
    assert row["evidence_label"] == "Hypothesis"
    assert row["source_url"] == ""
