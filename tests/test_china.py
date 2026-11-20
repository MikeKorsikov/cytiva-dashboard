"""Screen 6 (China): loader rules, USD conversion and the coverage step rule."""

from __future__ import annotations

import csv
import sqlite3

import pytest

from src.ingest import store
from src.ingest.china import CNY_USD_RATE, DATA_DIR, load_china
from src.metrics import china as cm

CSV_TABLES = {
    "sources.csv": "cn_source",
    "companies.csv": "cn_company",
    "coverage_grid.csv": "cn_coverage",
    "coverage_evidence.csv": "cn_coverage_evidence",
    "financials.csv": "cn_financial",
    "vendors.csv": "cn_vendor",
    "opportunities.csv": "cn_opportunity",
    "implications.csv": "cn_implication",
    "headline.csv": "cn_headline",
}


def _csv_count(name: str) -> int:
    with (DATA_DIR / name).open(encoding="utf-8", newline="") as handle:
        return sum(1 for _ in csv.DictReader(handle))


@pytest.fixture
def conn(tmp_path):
    connection = store.connect(tmp_path / "test.db")
    store.create_schema(connection)
    run_id = store.start_run(connection, "manual")
    load_china(connection, run_id)
    yield connection
    connection.close()


def test_every_csv_row_is_stored(conn):
    for name, table in CSV_TABLES.items():
        stored = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        assert stored == _csv_count(name), table


def test_sourced_rows_have_https_urls_and_hypotheses_do_not(conn):
    unsourced = conn.execute(
        "SELECT COUNT(*) FROM cn_financial WHERE source_url NOT LIKE 'https://%'"
    ).fetchone()[0]
    assert unsourced == 0
    hyp = conn.execute("SELECT evidence_label, source_url FROM cn_implication").fetchall()
    assert all(r["evidence_label"] == "Hypothesis" and r["source_url"] == "" for r in hyp)


def test_rmb_converted_at_the_stored_rate(conn):
    row = conn.execute("SELECT * FROM cn_financial WHERE id = 'F-01'").fetchone()
    assert row["revenue_usd_m"] == pytest.approx(924.7 / CNY_USD_RATE, abs=0.05)
    assert row["cny_usd_rate"] == CNY_USD_RATE


def test_danaher_china_is_derived_from_the_headline(conn):
    data = cm.load(conn)
    assert cm.danaher_china_usd_m(data) == pytest.approx(2700.0)
    danaher = next(r for r in cm.financial_rows(data) if r["company_id"] == "C00")
    assert danaher["revenue_usd_m_shown"] == pytest.approx(2700.0)


def test_headline_tiles_use_the_sheet_labels(conn):
    data = cm.load(conn)
    tiles = {t["id"]: t for t in cm.tiles(data)}
    assert tiles["H-01"]["value_num"] == 11.0
    assert tiles["H-01"]["evidence_label"] == "Fact"
    assert tiles["H-04"]["value_num"] == 8.0
    assert tiles["H-04"]["evidence_label"] == "Signal"


def test_steps_follow_the_and_rule(conn):
    steps = cm.load(conn).steps
    # Duoning has Media, Single-use, Filtration and Systems: step 3 needs all three of
    # Media, Single-use and Filtration, so it is Made.
    assert steps[("C07", "China", "3. Upstream processing")]["status"] == "Made"
    # Cytiva has single-use and no media cell. The shared rule (approved): any unknown family
    # makes the step ?, not Partial. Media for Cytiva China has no row, so step 3 is ?.
    assert steps[("C00", "China", "3. Upstream processing")]["status"] == "?"
    # Nothing is shown as Not made without evidence: service has no China row.
    assert steps[("C07", "China", "8. Service and support")]["status"] == "?"


def test_load_returns_none_before_the_tables_exist(tmp_path):
    connection = sqlite3.connect(tmp_path / "old.db")
    connection.row_factory = sqlite3.Row
    try:
        assert cm.load(connection) is None
    finally:
        connection.close()
