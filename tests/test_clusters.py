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
        "cdmo_site": 34,
        "market_signal": 13,
        "country_demand": 21,
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


def test_barrier_index_averages_the_scores_present(tmp_path):
    data = cm.load(_loaded(tmp_path))
    brazil = next(c for c in data.countries if c["country"] == "Brazil")
    # Customs 5.0, tariff 5 (12.0 percent), regulatory 4; three scores present.
    assert brazil["barrier_scores_available"] == 3
    assert abs(brazil["barrier_index"] - round((5.0 + 5 + 4) / 3, 2)) < 1e-9


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
