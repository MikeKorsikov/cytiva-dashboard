"""Demand drivers (Screen 4): the sheet's tabs load through their header maps with source URLs,
and the screen's figures are read from the stored rows. No network."""

import pytest

from src.ingest import sheet_headers, store
from src.ingest.demand import check_t2_header, load_demand
from src.ingest.sheet_headers import SECTION_TABS, read_tab
from src.metrics import demand as dm

SHEET = sheet_headers.DATA_ROOT / "demand" / "sheet"
SOURCED_TABLES = (
    "demand_burden",
    "demand_pipeline",
    "demand_approval",
    "demand_expiry",
    "demand_policy",
    "demand_top_drug",
    "demand_capacity",
)


def _loaded(tmp_path):
    conn = store.connect(tmp_path / "app.db")
    store.create_schema(conn)
    run = store.start_run(conn, "manual")
    load_demand(conn, run)
    return conn


def _data(tmp_path):
    return dm.load(_loaded(tmp_path))


def test_row_counts_match_the_sheet_and_unsourced_rows_are_rejected(tmp_path):
    conn = _loaded(tmp_path)
    count = {
        t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        for t in (
            "demand_burden",
            "demand_pipeline",
            "demand_approval",
            "demand_expiry",
            "demand_policy",
            "demand_top_drug",
            "demand_capacity",
            "demand_product_use",
        )
    }
    assert count == {
        "demand_burden": 20,  # T1: 20 countries
        "demand_pipeline": 14,  # T3 first table; the HQ-region table is read, not stored
        "demand_approval": 10,  # T4 approvals (2025 and 2026 to date)
        "demand_expiry": 4,  # T4 biosimilar wave: 5 rows, Ocrevus rejected (no source)
        "demand_policy": 6,  # T5
        "demand_top_drug": 15,  # T6 top 15
        "demand_capacity": 16,  # T7: 13 pledges and 3 built sites
        "demand_product_use": 5,  # T8, Hypothesis
    }
    # Ocrevus has no source yet, so it is rejected, not stored.
    assert (
        conn.execute("SELECT COUNT(*) FROM demand_expiry WHERE drug LIKE 'Ocrevus%'").fetchone()[0]
        == 0
    )


def test_every_stored_sourced_row_has_a_source_url(tmp_path):
    conn = _loaded(tmp_path)
    for table in SOURCED_TABLES:
        missing = conn.execute(
            f"SELECT COUNT(*) FROM {table} WHERE source_url IS NULL OR source_url = ''"
        ).fetchone()[0]
        assert missing == 0, table


def test_burden_ranking_matches_the_sheet_t2_ranking(tmp_path):
    data = _data(tmp_path)
    ours = [r["country"] for r in dm.top_burden(data, 10)]
    assert ours == check_t2_header()[:10]
    assert ours[:3] == ["China", "United States", "India"]


def test_burden_map_has_every_country_with_a_2024_count(tmp_path):
    data = _data(tmp_path)
    assert len(dm.map_points(data)) == 20


def test_headline_totals_match_the_sheet(tmp_path):
    data = _data(tmp_path)
    assert dm.mab_sales_top15(data) == 99.82  # sheet: 99.822
    assert dm.pledges_total(data) == 286.8  # sheet: 286.8
    fda = dm.fda_biologics_2025(data)
    assert (fda["cder"], fda["cber"], fda["total"]) == (12, 6, 18)  # sheet: 18
    assert dm._num(dm.pipeline_totals(data)["total"]["value"]) == 4487  # sheet: "4,487"


def test_fda_2025_ignores_the_2026_year_to_date_rows(tmp_path):
    data = _data(tmp_path)
    periods = {r["period"] for r in data.approvals if r["regulator"] == "FDA CDER"}
    assert "1 Jan to 13 Nov 2026" in periods
    assert dm.fda_biologics_2025(data)["cder"] == 12


def test_pipeline_bars_and_other_counts_are_split(tmp_path):
    data = _data(tmp_path)
    comparable = dm.pipeline_totals(data)["rows"]
    assert len(comparable) == 4  # gene, cell, RNA and the total
    assert len(dm.other_pipeline(data)) == 10


def test_bioprocess_flag_reads_the_sheet_text():
    assert dm.bioprocess_flag("Yes: cell culture resins filters") == "Yes"
    assert dm.bioprocess_flag("Partly: purification resins") == "Partly"
    assert dm.bioprocess_flag("No") == "No"
    assert dm.bioprocess_flag(None) == "to collect"


def test_product_matrix_is_loaded_as_hypothesis_without_source(tmp_path):
    conn = _loaded(tmp_path)
    rows = conn.execute(
        "SELECT medicine_type, evidence_label, source_url FROM demand_product_use"
    ).fetchall()
    assert len(rows) == 5
    assert all(r["evidence_label"] == "Hypothesis" for r in rows)
    assert all(not r["source_url"] for r in rows)


def test_mockup_checks_and_summary_rows_go_to_notes_not_to_tables(tmp_path):
    conn = _loaded(tmp_path)
    notes = conn.execute(
        "SELECT tab, text FROM screen_notes WHERE text LIKE 'Mockup check%'"
    ).fetchall()
    assert {r["tab"] for r in notes} >= {"T4 Approvals & expiries", "T6 Biggest drugs"}
    summary = conn.execute(
        "SELECT COUNT(*) FROM screen_notes WHERE tab = 'T6 Biggest drugs' "
        "AND text LIKE 'Top-15 sales from mAbs%'"
    ).fetchone()[0]
    assert summary == 1


def test_changed_from_mockup_is_a_note_not_a_column(tmp_path):
    conn = _loaded(tmp_path)
    count = conn.execute(
        "SELECT COUNT(*) FROM screen_notes WHERE tab = 'T8 Products used' "
        "AND text LIKE '%changed from mockup%'"
    ).fetchone()[0]
    assert count == 2  # the sheet has two "Changed from mockup" entries


def test_every_tab_has_a_section_map():
    for name in (
        "t1_disease_burden.csv",
        "t3_pipeline_by_type.csv",
        "t4_approvals_expiries.csv",
        "t5_policy_funding.csv",
        "t6_biggest_drugs.csv",
        "t7_capacity_pledges.csv",
        "t8_products_used.csv",
        "sources.csv",
    ):
        assert f"demand/sheet/{name}" in SECTION_TABS, name


def _copy_tab(tmp_path, monkeypatch, name, edit):
    """Copy one exported tab under a temporary data root, after applying `edit` to its text."""
    root = tmp_path / "data"
    target = root / "demand" / "sheet"
    target.mkdir(parents=True)
    text = (SHEET / name).read_text(encoding="utf-8")
    (target / name).write_text(edit(text), encoding="utf-8")
    monkeypatch.setattr(sheet_headers, "DATA_ROOT", root)
    return target / name


def test_a_changed_header_fails_the_read(tmp_path, monkeypatch):
    path = _copy_tab(
        tmp_path,
        monkeypatch,
        "t4_approvals_expiries.csv",
        lambda text: text.replace("Regulator,Metric,Value", "Regulator,Measure,Value", 1),
    )
    with pytest.raises(ValueError, match="unmapped headers|missing headers"):
        read_tab(path)


def test_a_missing_section_header_fails_the_read(tmp_path, monkeypatch):
    path = _copy_tab(
        tmp_path,
        monkeypatch,
        "t4_approvals_expiries.csv",
        lambda text: text.replace("\nDrug,Owner,Type", "\nDrugs,Owner,Type", 1),
    )
    with pytest.raises(ValueError, match="section header missing"):
        read_tab(path)


def test_the_sheet_exports_read_through_their_maps():
    for key in SECTION_TABS:
        read_tab(sheet_headers.DATA_ROOT / key)


def test_pipeline_region_table_is_read_and_checked():
    tab = read_tab(SHEET / "t3_pipeline_by_type.csv")
    regions = [r["region"] for r in tab.rows["pipeline_region"]]
    assert regions == ["United States", "China", "Europe and other"]


def test_implications_come_from_the_sheet_as_hypotheses(tmp_path):
    conn = _loaded(tmp_path)
    rows = conn.execute(
        "SELECT id, hypothesis, evidence_label, source_url FROM demand_implication ORDER BY id"
    ).fetchall()
    assert [r["id"] for r in rows] == ["I-01", "I-02"]
    assert rows[0]["hypothesis"] == "Can we report revenue by medicine type?"
    assert all(r["evidence_label"] == "Hypothesis" for r in rows)
    assert all(not r["source_url"] for r in rows)
