"""Customer clusters (Screen 3): the sheet's rows load with source URLs, and the screen's figures
are read from them. No network."""

from src.ingest import store
from src.ingest.clusters import load_clusters
from src.metrics import clusters as cm


def _loaded(tmp_path):
    conn = store.connect(tmp_path / "app.db")
    store.create_schema(conn)
    run = store.start_run(conn, "manual")
    load_clusters(conn, run)
    return conn


def test_every_stored_row_has_a_source_url(tmp_path):
    conn = _loaded(tmp_path)
    for table in (
        "cluster_fact",
        "cdmo_site",
        "market_signal",
        "country_demand",
        "country_barrier_index",
    ):
        missing = conn.execute(
            f"SELECT COUNT(*) FROM {table} WHERE source_url IS NULL OR source_url = ''"
        ).fetchone()[0]
        assert missing == 0, table


def test_row_counts_match_the_sheet(tmp_path):
    conn = _loaded(tmp_path)
    count = {
        t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        for t in (
            "cluster_fact",
            "cdmo_site",
            "market_signal",
            "country_demand",
            "country_barrier_index",
        )
    }
    assert count == {
        "cluster_fact": 30,
        "cdmo_site": 35,
        "market_signal": 13,
        "country_demand": 28,
        "country_barrier_index": 11,
    }


def test_placeholder_rows_without_a_figure_are_not_stored(tmp_path):
    conn = _loaded(tmp_path)
    assert conn.execute("SELECT COUNT(*) FROM cluster_fact WHERE value IS NULL").fetchone()[0] == 0


def test_density_ranking_uses_cluster_scope_counts(tmp_path):
    data = cm.load(_loaded(tmp_path))
    rows = cm.density_rows(data)
    assert rows[0]["hub"].startswith("Suzhou")
    assert rows[0]["count"] == 3800
    by_hub = {r["hub_id"]: r for r in rows}
    # Beijing uses the Daxing base (cluster scope), not the city-wide count.
    assert by_hub["CN-BEIJING"]["count"] == 800
    # Shanghai has only a city-wide count, and says so.
    assert by_hub["CN-SHANGHAI"]["scope"] == "city-wide"
    # Boston, Research Triangle and Songdo have no density count in the sheet.
    unscored = {h["hub_id"] for h in cm.all_hubs(data) if h["count"] is None}
    assert unscored == {"US-BOSTON", "US-RTP", "KR-SONGDO"}


def test_barrier_index_averages_the_three_shown_dimensions(tmp_path):
    data = cm.load(_loaded(tmp_path))
    brazil = next(c for c in data.countries if c["country"] == "Brazil")
    # Customs 5.0 and tariff 5 are present; local content is not assessed. Two scores present.
    assert brazil["barrier_scores_available"] == 2
    assert abs(brazil["barrier_index"] - 5.0) < 1e-9


def test_tholos_index_is_stored_and_not_averaged(tmp_path):
    data = cm.load(_loaded(tmp_path))
    india = next(c for c in data.countries if c["country"] == "India")
    assert abs(india["tbi_2025_score"] - 5.72) < 1e-9
    # India: customs 4.7, tariff 5, local content 4 -> 4.57 (TBI not included).
    assert abs(india["barrier_index"] - round((4.7 + 5 + 4) / 3, 2)) < 1e-9


def test_barrier_table_is_sorted_highest_first(tmp_path):
    data = cm.load(_loaded(tmp_path))
    indexes = [c["barrier_index"] for c in data.countries]
    assert indexes == sorted(indexes, reverse=True)


def test_tariff_scores_follow_the_stated_rule(tmp_path):
    data = cm.load(_loaded(tmp_path))
    score = {c["country"]: c["tariff_score_1_5"] for c in data.countries}
    assert score["India"] == 5  # 16.0 percent
    assert score["China"] == 3  # 7.5 percent
    assert score["United States"] == 1  # 3.3 percent


def test_directional_signals_are_the_ones_that_state_a_change(tmp_path):
    data = cm.load(_loaded(tmp_path))
    directional = cm.directional_signals(data)
    assert len(directional) == 6
    assert {s["direction"] for s in directional} == {"up", "down"}


def test_local_colour_follows_the_mvp_legend():
    local = {"North America": 4, "High-growth markets": 0, "Western Europe": 5}
    assert cm.local_colour("North America", local)[1] == "partly local"
    assert cm.local_colour("High-growth markets", local)[1] == "imported"
    assert cm.local_colour("Western Europe", local)[1] == "mostly local"


def test_headline_tiles_follow_the_stated_rules(tmp_path):
    data = cm.load(_loaded(tmp_path))
    h = cm.headline_tiles(data)
    assert h["densest"]["hub_id"] == "CN-SUZHOU"
    # High-growth markets make 0 of 7 steps, so the largest hub with no local supply is Suzhou.
    assert h["gap"]["hub_id"] == "CN-SUZHOU" and h["gap_steps"] == 0
    # Golden Triangle is the largest hub whose country index is below 2.0.
    assert h["entry"]["hub_id"] == "UK-GOLDEN"
    assert h["entry_index"] < cm.LOW_BARRIER
    assert (h["rising"], h["falling"]) == (4, 2)


# --- Screen 3: the legacy exception and the sheet tabs ----------------------------------------

import csv as _csv  # noqa: E402

from src.ingest import clusters as _clusters  # noqa: E402
from src.ingest.sheet_headers import HEADER_MAPS  # noqa: E402

_SHEET = _clusters.SHEET_DIR
_LEGACY_TOKENS = {
    "country_barriers.csv": ("tholos", "tariff applied", "tariff year", "tariff score"),
    "market_signals.csv": ("direction",),
    "clusters.csv": ("scope",),
}


def _headers(name: str) -> list[str]:
    with (_SHEET / name).open(encoding="utf-8", newline="") as handle:
        return next(_csv.reader(handle))


def test_legacy_exception_ends_once_the_sheet_has_the_columns():
    # LEGACY (22 Nov 2026): Tholos, applied tariff, tariff score, direction and scope are read from
    # the old CSVs until they are added to the seed sheet. This test fails when they are added:
    # then move them into the sheet's maps, delete the legacy files, and remove this exception.
    for name, tokens in _LEGACY_TOKENS.items():
        found = [h for h in _headers(name) if any(t in h.lower() for t in tokens)]
        assert not found, (
            f"{name} now has {found}: move these into the sheet, delete the legacy CSV and "
            "remove the LEGACY exception (docs/phase0-screen3-legacy.md)"
        )


def test_every_screen3_tab_is_read_through_a_header_map():
    for name in (
        "clusters.csv",
        "cdmo_sites.csv",
        "market_signals.csv",
        "country_barriers.csv",
        "demand_by_country.csv",
        "demand_by_region.csv",
        "research_institutions.csv",
        "data_sources.csv",
    ):
        assert f"clusters/sheet/{name}" in HEADER_MAPS, name


def test_sheet_barrier_index_and_display_flag_are_stored_beside_the_app_average(tmp_path):
    conn = _loaded(tmp_path)
    china = conn.execute(
        "SELECT barrier_index, sheet_barrier_index, sheet_scores_available, display_on_tile, "
        "legacy_fields FROM country_barrier_index WHERE country = 'China'"
    ).fetchone()
    # The app averages customs (3.8), tariff (3, legacy) and local (5): 3.93. The sheet's own
    # average uses four dimensions and gives 4.5. Both are kept; the screen shows the app's.
    assert abs(china["barrier_index"] - 3.93) < 1e-9
    assert abs(china["sheet_barrier_index"] - 4.5) < 1e-9
    assert china["sheet_scores_available"] == 4
    assert china["display_on_tile"] == "Index"
    assert "tbi_2025_score" in china["legacy_fields"]


def test_partial_index_notice_comes_from_the_sheet(tmp_path):
    conn = _loaded(tmp_path)
    notice = dict(
        conn.execute("SELECT country, display_on_tile FROM country_barrier_index").fetchall()
    )
    assert notice["United States"] == "Partial index: 1 of 5 scores"


def test_percent_values_are_numbers_not_placeholders(tmp_path):
    conn = _loaded(tmp_path)
    value = conn.execute("SELECT value FROM cluster_fact WHERE fact_id = 'F005'").fetchone()[0]
    assert value == 17.0
    market = conn.execute("SELECT value FROM market_signal WHERE indicator_id = 'M06'").fetchone()[
        0
    ]
    assert market == 27.0
