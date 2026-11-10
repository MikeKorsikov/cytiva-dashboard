"""Competitor coverage (screen 2): evidence file, derived families and steps. No network."""

from collections import Counter, defaultdict

from src.ingest import store
from src.ingest.coverage import (
    FAMILIES,
    HG,
    JP,
    NA,
    WE,
    derive_cells,
    load_coverage,
    read_evidence,
)
from src.metrics import coverage as coverage_metrics

REGIONS = [NA, WE, HG, JP]
COMPANIES = ["Cytiva", "Thermo Fisher", "Sartorius", "Repligen", "Avantor", "Merck KGaA"]

# Totals from the research file's Grid ("Makes (of 8)") and Steps ("Steps covered") rows.
SHEET_MAKES = {
    "Cytiva": [6, 6, 1, 0],  # +1 Western Europe media (E013, public Cytiva FAQ)
    "Thermo Fisher": [6, 3, 2, 0],  # NA genomic Service only (E022); WE ligands not resins (E109)
    "Sartorius": [3, 5, 5, 0],  # HGM monoliths not resins (E051)
    "Repligen": [
        5,
        2,
        2,
        0,
    ],  # WE media To confirm (E059); ligands/columns/Avitide not resins (E055, E060)
    "Avantor": [1, 1, 1, 0],
    "Merck KGaA": [3, 5, 3, 0],  # NA genomic Service only (E075); NA resins To confirm (E074)
}
SHEET_STEPS = {
    "Cytiva": [5, 5, 1, 1],
    "Thermo Fisher": [6, 3, 1, 1],  # AND rule, steps 2/3/5 per diagram (10 Nov 2026)
    "Sartorius": [3, 4, 5, 1],
    "Repligen": [4, 1, 2, 1],
    "Avantor": [1, 1, 1, 1],
    "Merck KGaA": [2, 4, 2, 1],
}


def _cells():
    return derive_cells(read_evidence())


def _as_dict(cells):
    return {(c["company_id"], c["region_id"], c["product_family"]): c for c in cells}


def test_evidence_file_has_every_row_and_known_values():
    rows = read_evidence()
    assert len(rows) == 109
    assert {r["status"] for r in rows} <= {"Made", "Partial", "To confirm", "Service only"}
    assert {r["confidence"] for r in rows} <= {"H", "M", "L"}
    assert all(r["url"].startswith("https://") for r in rows)


def test_each_derived_cell_is_unique_and_sourced():
    cells = _cells()
    keys = [(c["company_id"], c["region_id"], c["product_family"]) for c in cells]
    assert len(keys) == len(set(keys))
    assert all(c["source_url"].startswith("https://") for c in cells)


def test_family_counts_match_the_research_file():
    d = _as_dict(_cells())
    for company in COMPANIES:
        got = [
            sum(1 for f in FAMILIES if d.get((company, region, f), {}).get("status") == "Made")
            for region in REGIONS
        ]
        assert got == SHEET_MAKES[company], company


def test_step_counts_match_the_research_file():
    steps = coverage_metrics.step_cells(_as_dict(_cells()))
    made = defaultdict(int)
    for (company, region, _step), cell in steps.items():
        if cell["status"] == "Made":
            made[(company, region)] += 1
    for company in COMPANIES:
        got = [made[(company, region)] for region in REGIONS]
        assert got == SHEET_STEPS[company], company


def test_cytiva_north_america_resins_is_partial_and_step_four_is_partial():
    d = _as_dict(_cells())
    assert d[("Cytiva", NA, "Resins")]["status"] == "Partial"
    steps = coverage_metrics.step_cells(d)
    assert steps[("Cytiva", NA, "4. Downstream processing")]["status"] == "Partial"


def test_leads_only_are_not_stored(tmp_path):
    # Cytiva Western Europe analytics is only a lead ("To confirm"): no cell is stored.
    d = _as_dict(_cells())
    assert ("Cytiva", WE, "Analytical") not in d


def test_load_stores_evidence_and_cells(tmp_path):
    conn = store.connect(tmp_path / "app.db")
    store.create_schema(conn)
    run_id = store.start_run(conn, "manual")
    written = load_coverage(conn, run_id)
    assert written == len(_cells())
    assert conn.execute("SELECT COUNT(*) FROM footprint_evidence").fetchone()[0] == 109
    cells = coverage_metrics.footprint_cells(conn)
    assert cells[("Thermo Fisher", NA, "Media")]["status"] == "Made"
    assert Counter(c["status"] for c in cells.values())["Partial"] >= 1


def test_public_source_is_preferred_over_research_sheet():
    cells = _as_dict(_cells())
    # Cells that have any public evidence link to it, not to the research file.
    public_rows = {
        (r["company_id"], r["region_id"], r["product_family"])
        for r in read_evidence()
        if "docs.google.com/spreadsheets" not in r["url"]
        and r["status"] in ("Made", "Partial")
        and r["product_family"] in FAMILIES
    }
    for key in public_rows:
        assert "docs.google.com/spreadsheets" not in cells[key]["source_url"] or key[0] == "Cytiva"


def test_marks_linked_to_research_sheets_are_not_rendered_as_links():
    from src.app.shells import _footprint_matrix

    html = _footprint_matrix(_as_dict(_cells()))
    assert "docs.google.com/spreadsheets" not in html
