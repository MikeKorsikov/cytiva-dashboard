"""Demand drivers (Screen 4): the sheet's rows load with source URLs, and the screen's figures
are read from them. No network."""

from src.ingest import store
from src.ingest.demand import load_demand
from src.metrics import demand as dm


def _loaded(tmp_path):
    conn = store.connect(tmp_path / "app.db")
    store.create_schema(conn)
    run = store.start_run(conn, "manual")
    load_demand(conn, run)
    return conn


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
        )
    }
    assert count == {
        "demand_burden": 19,
        "demand_pipeline": 8,
        "demand_approval": 8,
        "demand_expiry": 4,
        "demand_policy": 6,
        "demand_top_drug": 15,
        "demand_capacity": 16,
    }
    # Ocrevus has no source yet, so it is rejected, not stored.
    assert (
        conn.execute("SELECT COUNT(*) FROM demand_expiry WHERE drug LIKE 'Ocrevus%'").fetchone()[0]
        == 0
    )


def test_every_stored_row_has_a_source_url(tmp_path):
    conn = _loaded(tmp_path)
    for table in (
        "demand_burden",
        "demand_pipeline",
        "demand_approval",
        "demand_expiry",
        "demand_policy",
        "demand_top_drug",
        "demand_capacity",
    ):
        missing = conn.execute(
            f"SELECT COUNT(*) FROM {table} WHERE source_url IS NULL OR source_url = ''"
        ).fetchone()[0]
        assert missing == 0, table


def test_burden_is_ranked_by_one_source_cancer_cases(tmp_path):
    data = dm.load(_loaded(tmp_path))
    top = [r["country"] for r in dm.top_burden(data, 3)]
    assert top == ["China", "United States", "India"]


def test_headline_totals_match_the_sheet(tmp_path):
    data = dm.load(_loaded(tmp_path))
    assert dm.mab_sales_top15(data) == 99.82  # sheet: 99.8
    assert dm.pledges_total(data) == 286.8  # sheet: 286.8
    fda = dm.fda_biologics_2025(data)
    assert (fda["cder"], fda["cber"], fda["total"]) == (12, 6, 18)  # sheet: 18
    assert dm.pipeline_totals(data)["total"]["value"] == "4487"


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
