"""Customer clusters (Screen 3): the sheet's rows load with source URLs, and the screen's
figures are read from them. No network."""

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
        "cluster_fact": 20,
        "cdmo_site": 34,
        "market_signal": 12,
        "country_demand": 21,
        "country_barrier_index": 11,
    }


def test_placeholder_row_without_a_figure_is_not_stored(tmp_path):
    conn = _loaded(tmp_path)
    assert (
        conn.execute("SELECT COUNT(*) FROM cluster_fact WHERE fact_id = 'F020'").fetchone()[0] == 0
    )


def test_kpis_come_from_the_sheet(tmp_path):
    data = cm.load(_loaded(tmp_path))
    k = cm.kpis(data)
    assert k["cdmo_sites"] == 34
    assert k["largest_cluster"]["cluster"] == "Songdo Incheon"
    assert k["largest_cluster"]["value"] == 1035000
    assert k["clusters_with_facts"] == 9


def test_barrier_table_is_sorted_and_skips_unscored_countries(tmp_path):
    data = cm.load(_loaded(tmp_path))
    rows = cm.barrier_table(data)
    indexes = [r["barrier_index"] for r in rows]
    assert indexes == sorted(indexes, reverse=True)
    assert all(r["barrier_index"] is not None for r in rows)
    assert len(rows) == 11


def test_demand_is_ordered_by_score(tmp_path):
    data = cm.load(_loaded(tmp_path))
    assert data.countries[0]["country"] == "United States"
