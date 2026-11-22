"""Screen 1 (overview) from the research sheet: every tab reads through its map, the M&A rows
come from the sheet's T2 tab, and the Clario check holds. No network."""

from src.ingest import company_deals, rankings, store
from src.ingest.sheet_headers import DATA_ROOT, OVERVIEW_TABS, read_tab


def _conn(tmp_path):
    conn = store.connect(tmp_path / "app.db")
    store.create_schema(conn)
    return conn


def test_every_overview_tab_reads_through_its_map():
    for key in OVERVIEW_TABS:
        read_tab(DATA_ROOT / key)


def test_sheet_mna_rows_are_the_six_deals_not_deal_talk():
    deals = company_deals.sheet_deals()
    assert [d["id"] for d in deals] == ["MA-01", "MA-02", "MA-03", "MA-04", "MA-05", "MA-06"]
    assert all(d["headline"].startswith(d["acquirer"]) for d in deals)


def test_clario_check_completed_on_24_march_2026_from_s18(tmp_path):
    """Clario check: MA-04 Thermo Fisher to acquire Clario completed 2026-03-24 (S18)."""
    conn = _conn(tmp_path)
    run_id = store.start_run(conn, "manual")
    company_deals.load_company_deals(conn, run_id)
    row = conn.execute(
        "SELECT status, completed_date, value_text, source_url, announced_date FROM deal "
        "WHERE acquirer = 'Thermo Fisher' AND headline LIKE '%Clario%'"
    ).fetchone()
    assert row["status"] == "announced"  # the tile counts announced deals
    assert row["completed_date"] == "2026-03-24"
    assert row["announced_date"] == "2025-10-29"
    assert row["source_url"].startswith("https://www.businesswire.com/news/home/20260324")
    assert "8.875" in row["value_text"]


def test_pending_and_blank_completion_leave_completed_date_empty(tmp_path):
    conn = _conn(tmp_path)
    run_id = store.start_run(conn, "manual")
    company_deals.load_company_deals(conn, run_id)
    completed = dict(
        conn.execute("SELECT headline, completed_date FROM deal WHERE category = 'M&A'").fetchall()
    )
    assert completed["Merck KGaA to acquire Bio-Techne"] is None
    solventum = "Thermo Fisher to acquire Solventum purification and filtration business"
    assert completed[solventum] is None


def test_company_deal_reload_replaces_the_old_literal_rows(tmp_path):
    conn = _conn(tmp_path)
    conn.execute(
        "INSERT INTO deal (acquirer, announced_date, category, headline, status, source_url, "
        "source_type, evidence_label, loaded_at, verification_status) VALUES "
        "('Danaher', '2024-08-19', 'M&A', 'Danaher acquires Genedata AG', 'announced', "
        "'https://example.com/x', 'document', 'Fact', '2026-11-22', 'passed')"
    )
    run_id = store.start_run(conn, "manual")
    company_deals.load_company_deals(conn, run_id)
    assert (
        conn.execute(
            "SELECT COUNT(*) FROM deal WHERE headline = 'Danaher acquires Genedata AG'"
        ).fetchone()[0]
        == 0
    )


def test_rankings_sheet_has_no_values_so_every_rank_is_to_collect(tmp_path):
    conn = _conn(tmp_path)
    run_id = store.start_run(conn, "manual")
    assert rankings.load_curated_rankings(conn, run_id) == 0
    rows = read_tab(DATA_ROOT / "overview" / "sheet" / "t1_rankings.csv").rows["rankings"]
    ranked = [r for r in rows if r["id"].startswith("RK-")]
    assert len(ranked) == 6
    for r in ranked:
        assert all(r[f] == "" for f in rankings.VALUE_COLUMNS)


def test_mna_counts_match_the_sheet_count_rows(tmp_path):
    """The tile's counts (as of 18 Nov 2026, the sheet's date) equal the sheet's own counts."""
    from datetime import date

    from src.metrics import deals as deal_metrics

    conn = _conn(tmp_path)
    run_id = store.start_run(conn, "manual")
    company_deals.load_company_deals(conn, run_id)
    rows = read_tab(DATA_ROOT / "overview" / "sheet" / "t2_ma.csv").loose
    sheet = {r[0]: (int(r[1]), int(r[2])) for r in rows if len(r) >= 3 and r[0] in PEERS}
    assert len(sheet) == len(PEERS)
    for company, (last_12m, in_list) in sheet.items():
        counts = deal_metrics.deal_counts(conn, company, date(2026, 11, 18))
        assert counts["M&A"]["last_12m"] == last_12m, company
        assert counts["M&A"]["last_5y"] == in_list, company


PEERS = ("Danaher", "Thermo Fisher", "Sartorius", "Repligen", "Avantor", "Merck KGaA")
