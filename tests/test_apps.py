"""Screen 5 applications ranking: loaded from the applications sheet (ranking tab), no URL."""

import pytest

from src.ingest import store
from src.ingest.technology import DATA_DIR, load_apps


@pytest.fixture
def conn(tmp_path):
    connection = store.connect(tmp_path / "app.db")
    store.create_schema(connection)
    yield connection
    connection.close()


def test_every_ranked_application_is_loaded_as_hypothesis(conn):
    with (DATA_DIR / "sheet" / "ranking.csv").open(encoding="utf-8") as handle:
        expected = sum(1 for _ in handle) - 1
    assert expected == 120
    run_id = store.start_run(conn, "manual")
    assert load_apps(conn, run_id) == expected
    row = conn.execute(
        "SELECT rank_no, score, evidence_label, source_url FROM tech_apps WHERE name = ?",
        ("Oracle E-Business Suite",),
    ).fetchone()
    assert (row["rank_no"], row["score"]) == (1, 10)
    assert row["evidence_label"] == "Hypothesis"
    assert row["source_url"] == ""
    confidences = {r[0] for r in conn.execute("SELECT scoring_confidence FROM tech_apps")}
    assert confidences <= {"H", "M", "L"}
