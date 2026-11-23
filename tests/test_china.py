"""Screen 6 (China): loader rules from the live tabs, USD conversion, the register-derived Cytiva
row, the step rule and the headline tiles. No network."""

from __future__ import annotations

import sqlite3

import pytest

from src.ingest import store
from src.ingest.china import CHINA_SHEET_URL, CNY_USD_RATE, load_china
from src.metrics import china as cm

EXPECTED_COUNTS = {
    "cn_source": 46,
    "cn_company": 19,  # C00 to C18
    "cn_coverage_evidence": 35,  # CE-01 to CE-35
    "cn_financial": 12,  # F-00 to F-09 (F-03b and F-08b included)
    "cn_vendor": 5,  # V01 to V05; V06 is removed in the sheet
    "cn_opportunity": 6,  # O-01 to O-06
    "cn_implication": 5,  # I-01 to I-05
    "cn_headline": 12,  # H-01 to H-12; H-12 is stored, never shown
}


@pytest.fixture
def conn(tmp_path):
    connection = store.connect(tmp_path / "test.db")
    store.create_schema(connection)
    run_id = store.start_run(connection, "manual")
    load_china(connection, run_id)
    yield connection
    connection.close()


def test_every_sheet_row_is_stored(conn):
    for table, expected in EXPECTED_COUNTS.items():
        assert conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == expected, table


def test_load_report_lists_only_the_known_differences(tmp_path):
    # The Cytiva grid differences are reference checks; V06 is removed on purpose.
    connection = store.connect(tmp_path / "report.db")
    store.create_schema(connection)
    report: list[str] = []
    load_china(connection, store.start_run(connection, "manual"), report)
    connection.close()
    for line in report:
        assert line.startswith(("grid C00", "V06")), line


def test_sourced_rows_have_https_urls(conn):
    assert (
        conn.execute(
            "SELECT COUNT(*) FROM cn_financial WHERE source_url NOT LIKE 'https://%'"
        ).fetchone()[0]
        == 0
    )
    assert (
        conn.execute(
            "SELECT COUNT(*) FROM cn_coverage WHERE source_url NOT LIKE 'https://%'"
        ).fetchone()[0]
        == 0
    )


def test_hypotheses_carry_the_sheet_link_and_the_hypothesis_label(conn):
    rows = conn.execute("SELECT evidence_label, source_url FROM cn_implication").fetchall()
    assert all(
        r["evidence_label"] == "Hypothesis" and r["source_url"] == CHINA_SHEET_URL for r in rows
    )


def test_rmb_converted_at_the_stored_rate(conn):
    row = conn.execute("SELECT * FROM cn_financial WHERE id = 'F-01'").fetchone()
    assert row["revenue_usd_m"] == pytest.approx(924.7 / CNY_USD_RATE, abs=0.05)
    assert row["cny_usd_rate"] == CNY_USD_RATE


def test_danaher_china_is_derived_from_the_headline(conn):
    data = cm.load(conn)
    assert cm.danaher_china_usd_m(data) == pytest.approx(2700.0)
    danaher = next(r for r in cm.financial_rows(data) if r["company_id"] == "C00")
    assert danaher["revenue_usd_m_shown"] == pytest.approx(2700.0)


def test_basis_sentence_is_built_from_h01_and_h02(conn):
    data = cm.load(conn)
    sentence = cm.basis_sentence(data)
    assert "11% of $24.6bn" in sentence
    assert "labelled as derived" in sentence


def test_basis_sentence_is_empty_when_h01_is_missing(conn):
    data = cm.load(conn)
    data.headline.pop("H-01")
    assert cm.basis_sentence(data) == ""


def test_f00_growth_is_not_disclosed_and_shows_n_d(conn):
    row = conn.execute("SELECT * FROM cn_financial WHERE id = 'F-00'").fetchone()
    assert row["revenue_yoy_pct"] is None


def test_headline_tiles_are_h01_and_h04_only(conn):
    data = cm.load(conn)
    tiles = {t["id"]: t for t in cm.tiles(data)}
    assert set(tiles) == {"H-01", "H-04"}
    assert tiles["H-01"]["value_num"] == 11.0
    assert tiles["H-04"]["value_num"] == 8.0
    assert tiles["H-04"]["confidence"] == "M"  # SIGNAL: a secondary summary


def test_h12_is_stored_but_never_on_a_tile(conn):
    row = conn.execute("SELECT show_on_tile FROM cn_headline WHERE id = 'H-12'").fetchone()
    assert row["show_on_tile"].startswith("No")
    assert all(t["id"] != "H-12" for t in cm.tiles(cm.load(conn)))


def test_cytiva_china_row_comes_from_the_register(conn):
    cells = {
        (r["company_id"], r["family"]): dict(r)
        for r in conn.execute("SELECT * FROM cn_coverage WHERE company_id = 'C00'")
    }
    assert cells[("C00", "SU")]["status"] == "Made"
    assert cells[("C00", "SU")]["evidence_id"] == "ST43"
    assert cells[("C00", "SU")]["confidence"] == "H"
    assert cells[("C00", "Sys")]["status"] == "Not made"
    assert cells[("C00", "Med")]["status"] == "Not made"


def test_only_china_sites_count_for_cytiva(conn):
    # ST47 (Incheon, Korea) evidences filtration, but it is not in China: Filtration is not made.
    cells = {
        (r["company_id"], r["family"]): r["status"]
        for r in conn.execute(
            "SELECT company_id, family, status FROM cn_coverage WHERE company_id = 'C00'"
        )
    }
    assert cells[("C00", "Filt")] == "Not made"


def test_cytiva_step_three_is_partial_and_step_eight_is_made_from_ce35(conn):
    steps = cm.load(conn).steps
    assert steps[("C00", "China", "3. Upstream processing")]["status"] == "Partial"
    step8 = steps[("C00", "China", "8. Service and support")]
    assert step8["status"] == "Made"
    assert step8["source_url"].startswith("https://")


def test_cytiva_single_use_row_follows_the_badge_rule(conn):
    # The Cytiva single-use row cites a register site (ST43). The register's Sources tab is not
    # exported, so no source type is known and the row is SIGNAL under the FACT rule (H alone is
    # not enough). Decision for the owner: give the register sources a Type, or keep SIGNAL.
    from src.app.design import row_badge  # noqa: F401  (the display path is covered in test_badges)
    from src.domain.confidence import row_label

    row = conn.execute(
        "SELECT confidence, source_url FROM cn_coverage WHERE company_id = 'C00' AND family = 'SU'"
    ).fetchone()
    assert row_label(row["confidence"], "") == "Signal"
    assert row_label(row["confidence"], "Primary") == "Fact"


def test_challengers_have_no_step_eight(conn):
    steps = cm.load(conn).steps
    assert steps[("C07", "China", "8. Service and support")]["status"] == "?"


def test_duoning_step_three_is_made(conn):
    steps = cm.load(conn).steps
    assert steps[("C07", "China", "3. Upstream processing")]["status"] == "Made"


def test_load_returns_none_before_the_tables_exist(tmp_path):
    connection = sqlite3.connect(tmp_path / "old.db")
    connection.row_factory = sqlite3.Row
    try:
        assert cm.load(connection) is None
    finally:
        connection.close()


def test_secondary_source_is_never_fact_even_at_high_confidence(conn):
    data = cm.load(conn)
    # S26 is a secondary company news item, so an H row citing it is SIGNAL, not FACT.
    assert "FACT" not in cm.badge(data, "H", "S26, S27", "https://example.com/x")
    # S01 is the 10-K (primary): an H row citing it is FACT.
    assert "FACT" in cm.badge(data, "H", "S01, S02", "https://www.sec.gov/x.htm")
