"""Layoffs tile (screen 1) from the sheet's T6 Layoffs tab. No network."""

from src.ingest import store
from src.ingest.overview_sheet import load_overview_sheet
from src.ingest.sheet_headers import DATA_ROOT, read_tab
from src.metrics import overview

LAYOFFS_FILE = DATA_ROOT / "overview" / "sheet" / "layoffs.csv"


def _rows():
    return [r for r in read_tab(LAYOFFS_FILE).rows["layoffs"] if r["id"].startswith("LO-")]


def _loaded(tmp_path):
    conn = store.connect(tmp_path / "app.db")
    store.create_schema(conn)
    load_overview_sheet(conn, store.start_run(conn, "manual"))
    return conn


def test_every_row_has_a_source_and_a_known_mark():
    rows = _rows()
    assert len(rows) == 18
    for r in rows:
        assert r["url"].startswith("https://")
        assert r["mark"] in {"Yes", "No", "Unknown"}
        assert r["evidence"]
        assert 2024 <= int(r["year"]) <= 2026


def test_no_company_year_is_entered_twice():
    keys = [(r["company"], r["year"]) for r in _rows()]
    assert len(keys) == len(set(keys))


def test_fact_badge_follows_the_rule_h_and_primary():
    # H confidence and a Primary source type: LO-03, LO-11, LO-12 and LO-13.
    fact = [r["id"] for r in _rows() if r["confidence"] == "H" and r["source_type"] == "Primary"]
    assert fact == ["LO-03", "LO-11", "LO-12", "LO-13"]


def test_loaded_badges_and_marks(tmp_path):
    conn = _loaded(tmp_path)
    facts = conn.execute(
        "SELECT company_id, year FROM layoff_year WHERE evidence_label = 'Fact' ORDER BY 1, 2"
    ).fetchall()
    assert len(facts) == 4
    # LO-01 is M confidence (an official monitor): Signal, not Fact.
    label = conn.execute(
        "SELECT evidence_label FROM layoff_year WHERE company_id = 'Thermo Fisher' AND year = 2026"
    ).fetchone()[0]
    assert label == "Signal"
    thermo = next(r for r in overview.layoff_marks(conn) if r["company"] == "Thermo Fisher")
    assert thermo["years"][2026]["mark"] == "Yes"


def test_layoff_marks_follow_peer_order(tmp_path):
    conn = _loaded(tmp_path)
    names = [row["company"] for row in overview.layoff_marks(conn)]
    assert names == sorted(names, key=lambda n: overview.PEER_ORDER.index(n))


def test_missing_table_shows_nothing_rather_than_failing(tmp_path):
    # A database built before the layoffs table existed must still render the Overview.
    conn = store.connect(tmp_path / "old.db")
    assert overview.layoff_marks(conn) == []
