"""Refresh robustness: each loader step fails on its own. No network: the loaders are stand-ins."""

import sqlite3

from src.ingest import refresh


def _ok_loader(conn, run_id):
    conn.execute(
        "INSERT INTO company (company_id, name, ticker, country, reporting_standard, "
        "fiscal_year_end, group_or_segment, source_url, source_type, evidence_label, loaded_at, "
        "verification_status) VALUES ('X', 'X', 'X', 'US', 'US GAAP', '12-31', 'group', "
        "'https://example.com/x', 'document', 'Fact', '2026-11-22', 'passed')"
    )
    conn.commit()
    return 1


def _ok_loader_two(conn, run_id):
    conn.execute(
        "INSERT INTO company (company_id, name, ticker, country, reporting_standard, "
        "fiscal_year_end, group_or_segment, source_url, source_type, evidence_label, loaded_at, "
        "verification_status) VALUES ('Z', 'Z', 'Z', 'US', 'US GAAP', '12-31', 'group', "
        "'https://example.com/z', 'document', 'Fact', '2026-11-22', 'passed')"
    )
    conn.commit()
    return 1


def _failing_feed(conn, run_id):
    conn.execute(
        "INSERT INTO company (company_id, name, ticker, country, reporting_standard, "
        "fiscal_year_end, group_or_segment, source_url, source_type, evidence_label, loaded_at, "
        "verification_status) VALUES ('Y', 'Y', 'Y', 'US', 'US GAAP', '12-31', 'group', "
        "'https://example.com/y', 'document', 'Fact', '2026-11-22', 'passed')"
    )
    raise RuntimeError("News feed for 'Avantor' returned HTTP 429")


def _run_with(monkeypatch, tmp_path, loaders):
    monkeypatch.setattr(refresh, "LOADERS", loaders)
    db = tmp_path / "app.db"
    rows = refresh.run(db, "manual")
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    run = conn.execute("SELECT * FROM refresh_run ORDER BY rowid DESC LIMIT 1").fetchone()
    companies = [r[0] for r in conn.execute("SELECT company_id FROM company ORDER BY 1")]
    conn.close()
    return rows, run, companies


def test_a_failing_feed_is_logged_and_the_run_goes_on(monkeypatch, tmp_path):
    rows, run, companies = _run_with(
        monkeypatch, tmp_path, [_ok_loader, _failing_feed, _ok_loader_two]
    )
    assert run["status"] == "completed with errors"
    assert "_failing_feed" in run["error"]
    assert "HTTP 429" in run["error"]
    assert "|" in run["error"]  # step | time | error
    assert rows == 2  # the two steps that worked are counted
    assert companies == ["X", "Z"]  # the failed step's partial insert was rolled back


def test_a_clean_run_is_succeeded_with_no_error(monkeypatch, tmp_path):
    _, run, _ = _run_with(monkeypatch, tmp_path, [_ok_loader])
    assert run["status"] == "succeeded"
    assert run["error"] is None


def test_every_failing_step_is_listed(monkeypatch, tmp_path):
    _, run, _ = _run_with(monkeypatch, tmp_path, [_failing_feed, _failing_feed])
    assert run["status"] == "completed with errors"
    assert run["error"].count("_failing_feed") == 2
