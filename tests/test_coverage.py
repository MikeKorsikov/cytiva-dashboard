"""Competitor coverage matrix (screen 2). No network: the cells are curated and sourced."""

from src.ingest import store
from src.ingest.coverage import CELLS, COMPANIES, FAMILIES, load_coverage
from src.metrics import coverage as coverage_metrics

STATUSES = {"Made", "Partial", "Not made"}


def test_every_cell_is_sourced_and_uses_a_known_status_and_family():
    for company, _region, family, status, url, _note in CELLS:
        assert company in COMPANIES
        assert family in FAMILIES
        assert status in STATUSES
        assert url.startswith("https://")


def test_no_cell_is_entered_twice():
    keys = [(c, r, f) for c, r, f, *_ in CELLS]
    assert len(keys) == len(set(keys))


def test_loaded_cells_are_returned_and_others_are_to_collect(tmp_path):
    conn = store.connect(tmp_path / "app.db")
    store.create_schema(conn)
    run_id = store.start_run(conn, "manual")
    assert load_coverage(conn, run_id) == len(CELLS)
    cells = coverage_metrics.footprint_cells(conn)
    assert cells[("Repligen", "North America", "Resins")]["status"] == "Made"
    # A cell with no source is not stored, so it reads as "to collect".
    assert ("Thermo Fisher", "North America", "Resins") not in cells
