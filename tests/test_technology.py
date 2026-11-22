"""Technology estate (Screen 5): import, the five tiles' rules, and the evidence drawer's sources.
No network. Dates are passed in, so the tests do not depend on the day they run."""

from datetime import date

import pytest

from src.ingest import store
from src.ingest import technology as tech
from src.ingest.technology import load_technology, parse_date
from src.metrics import technology as tm

TODAY = date(2026, 11, 16)


def _loaded(tmp_path):
    conn = store.connect(tmp_path / "app.db")
    store.create_schema(conn)
    run = store.start_run(conn, "manual")
    load_technology(conn, run)
    tech.load_apps(conn, run)
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
    assert count["tech_estate_evidence"] == 11  # EST-01 to EST-11; the Gap row is a note
    assert count["tech_sources"] == 43  # S01 to S43, from the sheet
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


def test_tile1_shows_only_rows_marked_yes_in_column_m(tmp_path):
    # Show on tile = Yes is the only rule: EOS-01 and EOS-02. EOS-03 to EOS-07 are "No".
    data = _data(tmp_path)
    ids = [r["id"] for r in tm.eos_tile_rows(data, TODAY)]
    assert sorted(ids) == ["EOS-01", "EOS-02"]
    assert "EOS-08" not in ids


def test_tile1_rows_carry_the_tile_note(tmp_path):
    data = _data(tmp_path)
    notes = {r["id"]: r["tile_note"] for r in tm.eos_tile_rows(data, TODAY)}
    assert notes["EOS-01"] == "Standard support; paid to 2030"


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
    # Sheet data: INC-03 (Microsoft 365, corroborated) is scope L (list M, watchlist W12 L), so it
    # is unconfirmed, not shown. Default tile: empty state, four rows awaiting confirmation.
    data = _data(tmp_path)
    exp = tm.exposure(data, TODAY)
    assert exp["shown"] == []
    assert sorted(r["id"] for r in exp["unconfirmed"]) == ["INC-03", "INC-05"]
    assert sorted(r["id"] for r in exp["pending"]) == ["INC-01", "INC-02", "INC-04", "INC-06"]
    inc03 = next(r for r in exp["unconfirmed"] if r["id"] == "INC-03")
    assert inc03["scope_confidence"] == "L"
    assert inc03["app"] == "Microsoft 365 (Teams)"
    assert inc03["match"] == "Exact"


def test_tile2_empty_state_when_the_window_moves_on(tmp_path):
    data = _data(tmp_path)
    exp = tm.exposure(data, date(2026, 12, 20))
    assert exp["shown"] == [] and exp["unconfirmed"] == [] and exp["pending"] == []
    assert tm.PENDING_EMPTY.startswith("No corroborated exposures")


def test_tile2_never_shows_reference_rows(tmp_path):
    data = _data(tmp_path)
    everything = tm.exposure(data, TODAY)
    ids = {r["id"] for r in everything["shown"] + everything["unconfirmed"] + everything["pending"]}
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


def test_gartner_rows_load_once_from_their_own_section(tmp_path):
    conn = store.connect(tmp_path / "app.db")
    store.create_schema(conn)
    run = store.start_run(conn, "manual")
    tech.load_technology(conn, run)
    gartner = [r[0] for r in conn.execute("SELECT id FROM tech_gartner ORDER BY id")]
    assert gartner == [f"G26-{i:02d}" for i in range(1, 11)]
    adoption = [r[0] for r in conn.execute("SELECT id FROM tech_adoption")]
    assert not [i for i in adoption if i.startswith("G26")]
    conn.close()


def test_gap_row_in_estate_evidence_is_a_note_not_a_data_row(tmp_path):
    conn = store.connect(tmp_path / "app.db")
    store.create_schema(conn)
    run = store.start_run(conn, "manual")
    tech.load_technology(conn, run)
    gap_rows = conn.execute("SELECT COUNT(*) FROM tech_estate_evidence WHERE id = 'Gap'")
    assert gap_rows.fetchone()[0] == 0
    note = conn.execute(
        "SELECT label, text FROM screen_notes WHERE tab = 'Estate evidence' AND label = 'Gap'"
    ).fetchone()
    assert note is not None and "Not confirmed" in note["text"]
    conn.close()


def test_changed_header_fails_the_load(tmp_path, monkeypatch):
    lines = (tech.DATA_DIR / "sheet" / "eos.csv").read_text(encoding="utf-8").splitlines()
    lines[0] = lines[0].replace("Show on tile", "Show on the tile")
    (tmp_path / "sheet").mkdir()
    (tmp_path / "sheet" / "eos.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    monkeypatch.setattr(tech, "DATA_DIR", tmp_path)
    with pytest.raises(ValueError, match="header row changed"):
        tech._rows("sheet/eos.csv")


# --- Tile 2: scope rule, matching, order, empty state (links, not names) ------------------------


def _app(name, vendor, conf, size=3, cx=3):
    return {
        "name": name,
        "vendor": vendor,
        "confidence": conf,
        "size_score": size,
        "complexity_score": cx,
    }


def _scope_data(apps, estate=(), watch=()):
    """A TechData with the rows the scope rule reads. estate and watch are (link, confidence)."""
    return tm.TechData(
        app_list=[
            {"name": a["name"], "vendor": a["vendor"], "confidence": a["confidence"]} for a in apps
        ],
        apps=[
            {
                "name": a["name"],
                "size_score": a["size_score"],
                "complexity_score": a["complexity_score"],
            }
            for a in apps
        ],
        estate_evidence=[{"applications": link, "confidence": c} for link, c in estate],
        watchlist=[{"applications": link, "estate_confidence": c} for link, c in watch],
    )


def test_scope_is_the_list_confidence_when_no_link_applies():
    data = _scope_data(
        [_app("Coupa", "Coupa", "H"), _app("Jaggaer", "Jaggaer", "M"), _app("Boomi", "Boomi", "L")]
    )
    assert {a["name"]: a["scope_confidence"] for a in tm.in_scope_apps(data)} == {
        "Coupa": "H",
        "Jaggaer": "M",
    }


def test_scope_takes_the_lower_of_list_and_linked_estate_evidence():
    # List H, linked estate row L: scope L, so not in scope.
    apps = [_app("Oracle E-Business Suite", "Oracle", "H")]
    assert tm.in_scope_apps(_scope_data(apps, estate=[("Oracle E-Business Suite", "L")])) == []
    # List M, linked estate row H: scope M.
    apps = [_app("Oracle E-Business Suite", "Oracle", "M")]
    data = _scope_data(apps, estate=[("Oracle E-Business Suite", "H")])
    assert tm.in_scope_apps(data)[0]["scope_confidence"] == "M"


def test_scope_takes_the_lower_of_list_and_linked_watchlist():
    apps = [_app("Microsoft 365 (Teams)", "Microsoft", "M")]
    data = _scope_data(apps, watch=[("Microsoft 365 (Teams)", "L")])
    assert tm.in_scope_apps(data) == []  # scope L
    assert [a["scope_confidence"] for a in tm.candidate_apps(data)] == ["L"]


def test_a_name_in_another_link_does_not_count_unless_it_is_listed_exactly():
    # Link cells are exact Names, ";"-separated. "Oracle EBS" is not "Oracle E-Business Suite".
    apps = [_app("Oracle E-Business Suite", "Oracle", "H")]
    data = _scope_data(apps, estate=[("Oracle EBS, Value Chain Planning", "L")])
    assert tm.in_scope_apps(data)[0]["scope_confidence"] == "H"
    data = _scope_data(apps, estate=[("Boomi; Oracle E-Business Suite", "L")])
    assert tm.in_scope_apps(data) == []


def _incident(id_, app_link, match="Exact", when="2026-11-10", tier_b=2):
    return {
        "id": id_,
        "vendor": "X",
        "product": "P",
        "date_value": when,
        "watchlist_id": "W01",
        "type_for_score": "Exploited",
        "product_match": match,
        "application": app_link,
        "tier_a_count": 0,
        "tier_b_count": tier_b,
        "type": "Exploited",
    }


def test_exact_sheet_flag_ranks_above_vendor_flag_then_relevance():
    apps = [
        _app("Oracle E-Business Suite", "Oracle", "H", 5, 5),
        _app("Oracle Fusion Cloud", "Oracle", "H", 3, 4),
    ]
    data = tm.TechData(
        app_list=[
            {"name": a["name"], "vendor": a["vendor"], "confidence": a["confidence"]} for a in apps
        ],
        apps=[
            {
                "name": a["name"],
                "size_score": a["size_score"],
                "complexity_score": a["complexity_score"],
            }
            for a in apps
        ],
        watchlist=[{"watch_id": "W01", "applications": "", "estate_confidence": "H"}],
        incidents=[
            _incident("INC-A", "Oracle Fusion Cloud", match="Vendor"),
            _incident("INC-B", "Oracle E-Business Suite", match="Exact"),
        ],
    )
    out = tm.exposure(data, TODAY)
    assert [r["id"] for r in out["shown"]] == ["INC-B", "INC-A"]  # Exact first


def test_incident_linked_to_no_candidate_app_is_not_a_row():
    data = tm.TechData(
        app_list=[{"name": "Boomi", "vendor": "Boomi", "confidence": "L"}],
        apps=[],
        watchlist=[{"watch_id": "W01", "applications": "", "estate_confidence": "H"}],
        incidents=[_incident("INC-C", "Boomi")],
    )
    out = tm.exposure(data, TODAY)
    assert out["shown"] == [] and out["unconfirmed"] == [] and out["pending"] == []


def test_blank_link_cell_is_not_a_row():
    data = tm.TechData(
        app_list=[{"name": "Boomi", "vendor": "Boomi", "confidence": "H"}],
        apps=[],
        watchlist=[{"watch_id": "W01", "applications": "", "estate_confidence": "H"}],
        incidents=[_incident("INC-D", "")],
    )
    out = tm.exposure(data, TODAY)
    assert out["shown"] == [] and out["unconfirmed"] == [] and out["pending"] == []


def test_corroborated_in_scope_incident_is_shown():
    data = tm.TechData(
        app_list=[{"name": "Coupa", "vendor": "Coupa", "confidence": "H"}],
        apps=[{"name": "Coupa", "size_score": 3, "complexity_score": 3}],
        watchlist=[{"watch_id": "W01", "applications": "", "estate_confidence": "H"}],
        incidents=[_incident("INC-E", "Coupa", tier_b=2)],
    )
    out = tm.exposure(data, TODAY)
    assert [r["id"] for r in out["shown"]] == ["INC-E"]
    assert out["shown"][0]["scope_confidence"] == "H"


def test_tile2_on_the_sheet_data_counts_match_the_links(tmp_path):
    data = _data(tmp_path)
    exp = tm.exposure(data, TODAY)
    assert exp["shown"] == []
    assert len(exp["pending"]) == 4
    assert len(exp["unconfirmed"]) == 2
