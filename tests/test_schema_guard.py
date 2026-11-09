"""Schema guard: a stale table layout is migrated in place and its rows are kept (CD-44)."""

from src.ingest import store

OLD_DEAL_TABLE = """
CREATE TABLE deal (
    acquirer TEXT NOT NULL,
    announced_date TEXT NOT NULL,
    headline TEXT NOT NULL,
    published_date TEXT,
    source_url TEXT,
    source_type TEXT,
    loaded_at TEXT,
    evidence_label TEXT,
    verification_status TEXT,
    PRIMARY KEY (acquirer, announced_date, headline)
)
"""


def _columns(conn, table):
    return {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}


def test_stale_table_gets_new_columns_and_keeps_sourced_rows(tmp_path):
    conn = store.connect(tmp_path / "app.db")
    conn.execute(OLD_DEAL_TABLE)
    conn.execute(
        "INSERT INTO deal VALUES ('Danaher', '2026-02-18', 'Danaher buys Masimo', NULL, "
        "'https://example.com/a', 'news', '2026-02-18T00:00:00', 'Signal', 'passed')"
    )
    changes = store.create_schema(conn)
    deal = next(c for c in changes if c["table"] == "deal")
    assert {"category", "value_usd", "status"} <= set(deal["added_columns"])
    assert "category" in _columns(conn, "deal")
    rows = conn.execute("SELECT headline, source_url FROM deal").fetchall()
    assert [(r["headline"], r["source_url"]) for r in rows] == [
        ("Danaher buys Masimo", "https://example.com/a")
    ]


def test_rows_without_a_source_are_dropped_and_counted(tmp_path):
    conn = store.connect(tmp_path / "app.db")
    conn.execute(OLD_DEAL_TABLE)
    conn.execute(
        "INSERT INTO deal VALUES ('Danaher', '2026-02-18', 'Sourced', NULL, "
        "'https://example.com/a', 'news', '2026-02-18T00:00:00', 'Signal', 'passed')"
    )
    conn.execute(
        "INSERT INTO deal VALUES ('Danaher', '2026-02-19', 'Unsourced', NULL, "
        "NULL, 'news', '2026-02-19T00:00:00', 'Signal', 'passed')"
    )
    deal = next(c for c in store.create_schema(conn) if c["table"] == "deal")
    assert (deal["rows_before"], deal["rows_after"]) == (2, 1)
    assert [r["headline"] for r in conn.execute("SELECT headline FROM deal")] == ["Sourced"]


def test_current_layout_is_left_alone(tmp_path):
    conn = store.connect(tmp_path / "app.db")
    store.create_schema(conn)
    assert store.create_schema(conn) == []


def test_migration_is_recorded_in_the_change_log(tmp_path):
    conn = store.connect(tmp_path / "app.db")
    conn.execute(OLD_DEAL_TABLE)
    changes = store.create_schema(conn)
    run_id = store.start_run(conn, "manual")
    for change in changes:
        store.log_migration(conn, run_id, change)
    logged = conn.execute(
        "SELECT COUNT(*) FROM change_log WHERE action = 'migrated' AND table_name = 'deal'"
    ).fetchone()[0]
    assert logged == 1
