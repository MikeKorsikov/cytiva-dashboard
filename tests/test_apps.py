"""Screen 5 applications ranking: loaded from the applications sheet (ranking tab), no URL."""

import csv

import pytest

from src.ingest import store
from src.ingest.technology import APPS_NOTES_TAB, DATA_DIR, load_apps


@pytest.fixture
def conn(tmp_path):
    connection = store.connect(tmp_path / "app.db")
    store.create_schema(connection)
    yield connection
    connection.close()


def test_applications_notes_tab_goes_to_screen_notes(conn):
    with (DATA_DIR / "sheet" / "notes.csv").open(encoding="utf-8", newline="") as handle:
        expected = sum(1 for _ in csv.DictReader(handle))
    assert expected == 37
    run_id = store.start_run(conn, "manual")
    load_apps(conn, run_id)
    count = conn.execute(
        "SELECT COUNT(*) FROM screen_notes WHERE tab = ?", (APPS_NOTES_TAB,)
    ).fetchone()[0]
    assert count == expected
    label = conn.execute(
        "SELECT label FROM screen_notes WHERE tab = ? AND text LIKE 'Master inventory%'",
        (APPS_NOTES_TAB,),
    ).fetchone()
    assert label["label"] == "Role of this file"


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
