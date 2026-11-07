"""Tests for the app database: schema, upserts, change log and refresh runs.

Uses a temporary SQLite file per test. No network access.
"""

import json

import pytest

from src.ingest import refresh, store
from src.ingest.schema import TABLES

GOOD_SOURCE = "https://example.com/annual-report-2025"


@pytest.fixture
def conn(tmp_path):
    connection = store.connect(tmp_path / "app.db")
    store.create_schema(connection)
    yield connection
    connection.close()


@pytest.fixture
def run_id(conn):
    return store.start_run(conn, "manual")


def _revenue_row(value_usd: float) -> dict:
    return {
        "company_id": "DHR",
        "fiscal_year": 2025,
        "metric": "revenue",
        "value_usd": value_usd,
        "value_local": None,
        "currency": "USD",
        "source_url": GOOD_SOURCE,
        "source_type": "document",
        "published_date": "2026-02-01",
        "evidence_label": "Fact",
        "is_sample": False,
    }


def test_schema_creates_every_table(conn):
    names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    for table in TABLES:
        assert table.name in names
    assert {"refresh_run", "change_log"} <= names


def test_schema_is_safe_to_run_twice(conn):
    store.create_schema(conn)  # must not raise


def test_insert_records_change_and_passes(conn, run_id):
    status = store.upsert(conn, run_id, "financial_metric", _revenue_row(24_600.0))
    assert status == "passed"
    row = conn.execute("SELECT verification_status, is_sample FROM financial_metric").fetchone()
    assert row["verification_status"] == "passed"
    assert row["is_sample"] == 0
    change = conn.execute("SELECT action, table_name FROM change_log").fetchone()
    assert (change["action"], change["table_name"]) == ("insert", "financial_metric")


def test_record_without_source_is_rejected_and_not_written(conn, run_id):
    row = _revenue_row(24_600.0) | {"source_url": None}
    status = store.upsert(conn, run_id, "financial_metric", row)
    assert status == "rejected"
    assert conn.execute("SELECT COUNT(*) FROM financial_metric").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM change_log").fetchone()[0] == 0


def test_record_with_insecure_source_is_rejected(conn, run_id):
    row = _revenue_row(24_600.0) | {"source_url": "http://example.com/report"}
    assert store.upsert(conn, run_id, "financial_metric", row) == "rejected"


def test_quote_check_marks_value_not_in_source(conn, run_id):
    row = {
        "company_id": "DHR",
        "fiscal_year": 2025,
        "metric": "revenue",
        "value_usd": 24_600.0,
        "value_local": None,
        "currency": "USD",
        "source_url": GOOD_SOURCE,
        "source_type": "document",
        "published_date": "2026-02-01",
        "evidence_label": "Fact",
        "is_sample": False,
    }
    status = store.upsert(
        conn,
        run_id,
        "financial_metric",
        row,
        source_text="Revenue was 25,000 million",
        quote_columns=("value_usd",),
    )
    assert status == "unverified"


def test_update_only_logs_when_values_change(conn, run_id):
    store.upsert(conn, run_id, "financial_metric", _revenue_row(24_600.0))
    store.upsert(conn, run_id, "financial_metric", _revenue_row(24_600.0))
    assert conn.execute("SELECT COUNT(*) FROM change_log").fetchone()[0] == 1

    store.upsert(conn, run_id, "financial_metric", _revenue_row(24_700.0))
    changes = conn.execute(
        "SELECT action, old_values, new_values FROM change_log ORDER BY change_id"
    ).fetchall()
    assert [c["action"] for c in changes] == ["insert", "update"]
    assert json.loads(changes[1]["old_values"])["value_usd"] == 24_600.0
    assert json.loads(changes[1]["new_values"])["value_usd"] == 24_700.0


def test_refresh_run_with_no_loaders_records_success(tmp_path, monkeypatch):
    monkeypatch.setattr(refresh, "LOADERS", [])
    db = tmp_path / "app.db"
    assert refresh.run(db, "manual") == 0
    conn = store.connect(db)
    run = conn.execute("SELECT trigger, status FROM refresh_run").fetchone()
    conn.close()
    assert (run["trigger"], run["status"]) == ("manual", "succeeded")


def test_refresh_run_records_failure_and_reraises(tmp_path, monkeypatch):
    def broken(conn, run_id):
        raise RuntimeError("source offline")

    monkeypatch.setattr(refresh, "LOADERS", [broken])
    db = tmp_path / "app.db"
    with pytest.raises(RuntimeError, match="source offline"):
        refresh.run(db, "scheduled")
    conn = store.connect(db)
    run = conn.execute("SELECT status, error FROM refresh_run").fetchone()
    conn.close()
    assert run["status"] == "failed"
    assert "source offline" in run["error"]
