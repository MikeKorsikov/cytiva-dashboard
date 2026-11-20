"""Competitor coverage (screen 2): the seed sheets, the grid, the step rule and the sales tab.

Reads the exports in data/coverage/sheet/ (no network, no live sheet calls).
"""

from src.ingest import store
from src.ingest.coverage import (
    FAMILIES,
    HG,
    JP,
    NA,
    WE,
    load_coverage,
    parse_families,
    stage_families,
)
from src.metrics import coverage as cm

REGIONS = [NA, WE, HG, JP]
COMPANIES = ["Cytiva", "Thermo Fisher", "Sartorius", "Repligen", "Avantor", "Merck KGaA"]

# The sheet's T4 (Cytiva families made, of 8) and T2 (Cytiva steps 1-7 made, step 8 excluded).
CYTIVA_FAMILIES_MADE = [6, 5, 2, 0]
CYTIVA_STEPS_LOCAL = [4, 2, 1, 0]


def _load(tmp_path):
    conn = store.connect(tmp_path / "app.db")
    store.create_schema(conn)
    run_id = store.start_run(conn, "manual")
    report: list[str] = []
    accepted = load_coverage(conn, run_id, report)
    return conn, accepted, report


def _cells(conn):
    return cm.grid_cells(conn)


def test_load_counts_match_the_sheet_tabs(tmp_path):
    conn, accepted, report = _load(tmp_path)
    counts = {
        t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        for t in ["s2_source", "s2_peer_site", "s2_cyt_site", "s2_grid", "s2_biotech_sales"]
    }
    assert counts == {
        "s2_source": 20,  # S01 to S20
        "s2_peer_site": 47,  # PS-01 to PS-47
        "s2_cyt_site": 51,  # ST01 to ST51
        "s2_grid": 73,  # every grid cell that is not ?
        "s2_biotech_sales": 4,
    }
    assert report == []  # T1 matches the register rule (reference check, no differences)
    assert accepted >= sum(counts.values())


def test_loader_is_idempotent(tmp_path):
    conn, _, _ = _load(tmp_path)
    before = {
        t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        for t in [
            "s2_source",
            "s2_peer_site",
            "s2_peer_family",
            "s2_cyt_site",
            "s2_grid",
            "s2_biotech_sales",
        ]
    }
    load_coverage(conn, store.start_run(conn, "manual"), [])
    after = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in before}
    assert before == after


def test_known_values_from_the_sheet(tmp_path):
    conn, _, _ = _load(tmp_path)
    cells = _cells(conn)
    assert cells[("Thermo Fisher", NA, "Media")]["status"] == "Made"
    assert cells[("Sartorius", HG, "Resins")]["status"] == "Partial"
    assert cells[("Cytiva", NA, "Resins")]["status"] == "Partial"  # Muskegon, not yet producing
    assert cells[("Cytiva", WE, "Analytical")]["status"] == "Partial"  # hypothesis only
    assert cells[("Cytiva", NA, "Analytical")]["status"] == "Not made"


def test_every_cell_and_site_is_sourced(tmp_path):
    conn, _, _ = _load(tmp_path)
    assert all(c["source_url"].startswith("https://") for c in _cells(conn).values())
    urls = [r[0] for r in conn.execute("SELECT source_url FROM s2_peer_site")]
    assert all(u.startswith("https://") for u in urls)


def test_cytiva_family_and_step_counts_match_the_sheet(tmp_path):
    conn, _, _ = _load(tmp_path)
    cells = _cells(conn)
    families = [
        sum(1 for f in FAMILIES if cells.get(("Cytiva", r, f), {}).get("status") == "Made")
        for r in REGIONS
    ]
    steps = cm.step_cells(cells)
    local = [
        sum(
            1
            for (co, reg, step), c in steps.items()
            if co == "Cytiva" and reg == r and not step.startswith("8.") and c["status"] == "Made"
        )
        for r in REGIONS
    ]
    assert families == CYTIVA_FAMILIES_MADE
    assert local == CYTIVA_STEPS_LOCAL


def test_step_eight_follows_the_service_column_and_is_question_mark_for_peers(tmp_path):
    conn, _, _ = _load(tmp_path)
    steps = cm.step_cells(_cells(conn))
    cytiva = {r: steps[("Cytiva", r, "8. Service and support")]["status"] for r in REGIONS}
    assert cytiva == {NA: "Made", WE: "Made", HG: "Made", JP: "Partial"}
    peer_step8 = [
        v["status"] for k, v in steps.items() if k[0] != "Cytiva" and k[2].startswith("8.")
    ]
    assert peer_step8 and set(peer_step8) == {"?"}


def test_biotech_sales_share_is_computed_from_the_four_regions(tmp_path):
    conn, _, _ = _load(tmp_path)
    sales = cm.biotech_sales(conn)
    assert {r: s["value_m"] for r, s in sales.items()} == {
        NA: 524.0,
        WE: 726.0,
        HG: 490.0,
        JP: 57.0,
    }
    assert round(sales[NA]["share"], 1) == 29.2
    assert round(sales[JP]["share"], 1) == 3.2
    assert sales[NA]["total_m"] == 1797.0


# --- The step rule (approved definition, one helper for screens 2 and 6) -----------------


def _cell(status):
    return {"status": status, "source_url": "https://example.com"}


def _grid(**families):
    return {("Co", "R", fam): _cell(status) for fam, status in families.items()}


def test_step_rule_all_made_is_made():
    cells = _grid(Analytical="Made")
    assert cm.step_cells(cells)[("Co", "R", "1. Research tools")]["status"] == "Made"


def test_step_rule_any_unknown_is_question_mark_even_with_partial():
    # Genomic has no stored cell (it is ?), so step 2 is ? even though Media is Made.
    cells = _grid(Media="Made", **{"Single-use": "Partial"})
    steps = cm.step_cells(cells)
    assert steps[("Co", "R", "2. Cell line and process dev.")]["status"] == "?"


def test_step_rule_some_made_or_partial_is_partial():
    cells = _grid(Media="Made", **{"Single-use": "Not made"})
    assert cm.step_cells(cells)[("Co", "R", "3. Upstream processing")]["status"] == "Partial"


def test_step_rule_otherwise_not_made():
    cells = _grid(Filling="Not made")
    assert (
        cm.step_cells(cells)[("Co", "R", "5. Formulation and fill-finish")]["status"] == "Not made"
    )


def test_step_three_no_longer_needs_filtration():
    cells = _grid(Media="Made", **{"Single-use": "Made", "Filtration": "Not made"})
    assert cm.step_cells(cells)[("Co", "R", "3. Upstream processing")]["status"] == "Made"


def test_step_two_needs_single_use():
    cells = _grid(Genomic="Made", Media="Made", **{"Single-use": "Not made"})
    assert cm.step_cells(cells)[("Co", "R", "2. Cell line and process dev.")]["status"] == "Partial"


def test_step_eight_is_made_only_with_a_made_service_row():
    cells = _grid(Service="Made")
    assert cm.step_cells(cells)[("Co", "R", "8. Service and support")]["status"] == "Made"
    cells = _grid(Media="Made")
    assert cm.step_cells(cells)[("Co", "R", "8. Service and support")]["status"] == "?"


# --- Parsing helpers --------------------------------------------------------------------


def test_families_cell_parses_partial_and_lists():
    assert parse_families("Single-use (partial)") == [("Single-use", True)]
    assert parse_families("Single-use; Systems") == [("Single-use", False), ("Systems", False)]
    assert parse_families("Filtration; Single-use") == [
        ("Filtration", False),
        ("Single-use", False),
    ]


def test_register_stages_map_to_families():
    assert stage_families(
        "Chromatography resins; Process hardware and Discovery and analytics"
    ) == {"Resins", "Systems", "Analytical"}
    assert stage_families("Hypothesis") == set()


def test_no_code_refers_to_the_research_file_url():
    import pathlib

    research_url = "docs.google.com/spreadsheets/d/1C1vMJ"
    for path in pathlib.Path("src").rglob("*.py"):
        assert research_url not in path.read_text(encoding="utf-8"), path


def test_marks_on_google_sheet_links_are_not_rendered_as_links(tmp_path):
    from src.app.shells import _footprint_matrix

    conn, _, _ = _load(tmp_path)
    html = _footprint_matrix(_cells(conn))
    assert "docs.google.com/spreadsheets" not in html


def test_hypothesis_only_stage_is_evidenced_nowhere():
    from src.ingest.coverage import site_evidence

    assert site_evidence("Discovery and analytics (to confirm)", "Hypothesis") == (
        set(),
        {"Analytical"},
    )


def test_mixed_evidence_counts_only_the_evidenced_part():
    from src.ingest.coverage import site_evidence

    stages = "Chromatography resins; Process hardware and Discovery and analytics (to confirm)"
    evidence = "Evidenced: public source (resins); hypothesis (others)"
    evidenced, hypothesis = site_evidence(stages, evidence)
    assert evidenced == {"Resins"}
    assert hypothesis == {"Systems", "Analytical"}


def test_site_not_yet_producing_is_detected():
    from src.ingest.coverage import is_producing

    assert not is_producing("Chromatography resins (from 2028)")
    assert not is_producing("Filtration (start 2026)")
    assert is_producing("Single-use and bioreactors")


def test_register_notes_and_primary_urls_are_loaded(tmp_path):
    conn, _, _ = _load(tmp_path)
    notes = conn.execute("SELECT COUNT(*) FROM screen_notes WHERE tab = 'Sites (register)'")
    assert notes.fetchone()[0] == 3
    assert (
        conn.execute("SELECT COUNT(*) FROM s2_cyt_site WHERE primary_url = 1").fetchone()[0] == 10
    )
