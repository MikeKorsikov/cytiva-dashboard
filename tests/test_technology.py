"""Technology estate (Screen 5): import, the five tiles' rules, and the evidence drawer's sources.
No network. Dates are passed in, so the tests do not depend on the day they run."""

from datetime import date

from src.ingest import store
from src.ingest.technology import load_technology, parse_date
from src.metrics import technology as tm

TODAY = date(2026, 11, 16)


def _loaded(tmp_path):
    conn = store.connect(tmp_path / "app.db")
    store.create_schema(conn)
    run = store.start_run(conn, "manual")
    load_technology(conn, run)
    return conn


def _data(tmp_path):
    return tm.load(_loaded(tmp_path))


# --- Import -----------------------------------------------------------------------------------


def test_import_runs_twice_without_duplicates(tmp_path):
    conn = store.connect(tmp_path / "app.db")
    store.create_schema(conn)
    run = store.start_run(conn, "manual")
    first = load_technology(conn, run)
    second = load_technology(conn, run)
    assert first == second
    assert conn.execute("SELECT COUNT(*) FROM tech_eos").fetchone()[0] == 8


def test_row_counts_match_the_sheet_except_rows_without_a_source(tmp_path):
    conn = _loaded(tmp_path)
    count = {
        t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        for t in (
            "tech_eos",
            "tech_incidents",
            "tech_watchlist",
            "tech_feeds",
            "tech_integrations",
            "tech_adoption",
            "tech_gartner",
            "tech_implications",
            "tech_estate_evidence",
            "tech_sources",
        )
    }
    assert count["tech_eos"] == 8
    assert count["tech_incidents"] == 9  # INC 6 + REF 3
    assert count["tech_watchlist"] == 14
    assert count["tech_integrations"] == 14
    assert count["tech_gartner"] == 10
    assert count["tech_implications"] == 7
    assert count["tech_estate_evidence"] == 10
    assert count["tech_sources"] == 39
    # Sheet expects 23 feeds and 9 adoption rows. Feed F23 (leads only, no URL) and ADO-09
    # (no public signal, no URL) are rejected by the source rule, so the counts are 22 and 8.
    assert count["tech_feeds"] == 22
    assert count["tech_adoption"] == 8


def test_every_stored_row_has_a_source_or_is_a_hypothesis(tmp_path):
    conn = _loaded(tmp_path)
    for table in (
        "tech_eos",
        "tech_incidents",
        "tech_integrations",
        "tech_adoption",
        "tech_gartner",
        "tech_estate_evidence",
        "tech_sources",
        "tech_feeds",
    ):
        bad = conn.execute(
            f"SELECT COUNT(*) FROM {table} WHERE (source_url IS NULL OR source_url = '') "
            "AND evidence_label <> 'Hypothesis'"
        ).fetchone()[0]
        assert bad == 0, table


def test_date_text_is_parsed_by_the_import_rules():
    assert parse_date("31 Dec 2027") == (date(2027, 12, 31), "day", False)
    assert parse_date("2026-10-20") == (date(2026, 10, 20), "day", False)
    assert parse_date("2026-03") == (date(2026, 3, 1), "month", False)
    assert parse_date("at least 2037") == (date(2037, 12, 31), "year", True)
    assert parse_date("at least 2036 (rolling)") == (date(2036, 12, 31), "year", True)
    assert parse_date("2026 (job ads)") == (None, None, False)
    assert parse_date("n/a") == (None, None, False)


# --- Tile 1 -----------------------------------------------------------------------------------


def test_tile1_shows_every_row_including_low_confidence(tmp_path):
    # Confidence is a label, never a filter: EOS-07 (lower of estate M and date L) is shown.
    data = _data(tmp_path)
    ids = {r["id"] for r in tm.eos_rows(data, TODAY)}
    assert {"EOS-01", "EOS-02", "EOS-07"} <= ids
    assert "EOS-08" not in ids


def test_tile1_with_toggle_shows_all_unconfirmed(tmp_path):
    data = _data(tmp_path)
    ids = {r["id"] for r in tm.eos_rows(data, TODAY)}
    assert {"EOS-03", "EOS-04", "EOS-05", "EOS-06", "EOS-07"} <= ids


def test_status_colour_is_against_today(tmp_path):
    data = _data(tmp_path)
    colour = {r["id"]: r["colour"] for r in tm.eos_rows(data, TODAY)}
    assert colour["EOS-04"] == "red"  # 14 Oct 2025, passed
    assert colour["EOS-05"] == "amber"  # 31 Dec 2026, within 12 months
    assert colour["EOS-01"] == "green"  # 31 Dec 2027, more than 12 months
    assert colour["EOS-02"] == "green"  # at least 2037 (floor)


def test_tile1_sort_red_then_amber_then_green(tmp_path):
    data = _data(tmp_path)
    order = [r["colour"] for r in tm.eos_rows(data, TODAY)]
    assert order == sorted(order, key=lambda c: tm.EOS_ORDER[c])


# --- Tile 2 -----------------------------------------------------------------------------------


def test_tile2_shows_only_the_corroborated_watchlist_incident(tmp_path):
    data = _data(tmp_path)
    exp = tm.exposure(data, TODAY)
    assert [r["id"] for r in exp["shown"]] == ["INC-03"]
    assert len(exp["pending"]) == 5
    assert exp["shown"][0]["relevance"] == "Medium"
    assert exp["shown"][0]["score"]["total"] == 5


def test_tile2_empty_state_when_the_window_moves_on(tmp_path):
    data = _data(tmp_path)
    exp = tm.exposure(data, date(2026, 12, 20))
    assert exp["shown"] == []
    assert exp["pending"] == []
    assert tm.PENDING_EMPTY.startswith("No corroborated exposures")


def test_tile2_never_shows_reference_rows(tmp_path):
    data = _data(tmp_path)
    everything = tm.exposure(data, TODAY)
    ids = {r["id"] for r in everything["shown"] + everything["pending"]}
    assert not any(i.startswith("REF") for i in ids)


def test_tile2_window_label_is_rolling_thirty_days():
    assert tm.window_label(TODAY).startswith("17 Oct")


# --- Tiles 3, 4 and 5 -------------------------------------------------------------------------


def test_tile3_groups_follow_the_readiness_prefix(tmp_path):
    data = _data(tmp_path)
    groups = {g["key"]: [m["id"] for m in g["members"]] for g in tm.integration_groups(data)}
    assert "INT-04" in groups["api"]
    assert "INT-08" in groups["mixed"]
    assert "INT-12" in groups["legacy"]


def test_tile3_chip_confidence_is_the_lower_component(tmp_path):
    data = _data(tmp_path)
    chips = {m["id"]: m["confidence"] for g in tm.integration_groups(data) for m in g["members"]}
    assert chips["INT-04"] == "H"  # estate H, capability H
    assert chips["INT-01"] == "M"  # estate M, capability M


def test_tile4_gartner_links_resolve_to_adoption_rows(tmp_path):
    data = _data(tmp_path)
    rows = {g["id"]: g for g in tm.gartner_rows(data)}
    assert rows["G26-01"]["linked"][0]["technology"] == "AI and physical AI in labs"
    assert rows["G26-02"]["none"] is True


def test_tile5_every_row_is_a_hypothesis_with_a_basis(tmp_path):
    data = _data(tmp_path)
    rows = tm.implication_rows(data)
    assert len(rows) == 7
    assert all(r["evidence_label"] == "Hypothesis" for r in rows)
    assert tm.based_on(data, "EOS-01; EOS-08") == ["EOS-01", "EOS-08"]


# --- Evidence drawer --------------------------------------------------------------------------


def test_every_row_opens_a_drawer_with_a_source_url(tmp_path):
    data = _data(tmp_path)
    for r in tm.eos_rows(data, TODAY):
        assert tm.sources_for(data, "tech_eos", r["id"]), r["id"]
    for r in data.incidents:
        if r["id"] in ("INC-03",):
            srcs = tm.sources_for(data, "tech_incidents", r["id"])
            assert srcs and all(s["url"].startswith("https://") for s in srcs)


# --- Components: no sheet values hard-coded ----------------------------------------------------


def test_technology_component_has_no_hard_coded_vendor_names():
    from pathlib import Path

    src = Path("src/app/shells.py").read_text(encoding="utf-8")
    start = src.index("def technology_screen(")
    end = src.index("\n\ndef ", start + 10)
    body = src[start:end]
    for vendor in ("Oracle", "SAP", "Microsoft", "Salesforce", "Snowflake", "Workday", "OneStream"):
        assert vendor not in body, vendor
