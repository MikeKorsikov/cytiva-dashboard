"""Incidents in the last 30 days (CD-30). No network: the KEV feed is a fixture."""

from datetime import date

import pytest
import requests

from src.ingest import incidents, store
from src.metrics import technology as tech_metrics

AS_OF = date(2026, 11, 9)
FEED = {
    "vulnerabilities": [
        {  # in window, Oracle: estate product
            "cveID": "CVE-2026-0001",
            "vendorProject": "Oracle",
            "vulnerabilityName": "Oracle E-Business Suite RCE",
            "dateAdded": "2026-10-20",
            "shortDescription": "Remote code execution.",
        },
        {  # outside window (before 10 Oct 2026)
            "cveID": "CVE-2026-0002",
            "vendorProject": "Oracle",
            "vulnerabilityName": "Old Oracle issue",
            "dateAdded": "2026-09-01",
            "shortDescription": "Old.",
        },
        {  # in window, not an estate vendor
            "cveID": "CVE-2026-0003",
            "vendorProject": "Apple",
            "vulnerabilityName": "iOS issue",
            "dateAdded": "2026-11-04",
            "shortDescription": "Not ours.",
        },
        {  # in window, Rockwell: estate product
            "cveID": "CVE-2026-0004",
            "vendorProject": "Rockwell Automation",
            "vulnerabilityName": "Controller authentication bypass",
            "dateAdded": "2026-11-01",
            "shortDescription": "Bypass.",
        },
    ]
}


def test_only_estate_vendors_inside_the_window_are_kept():
    found = incidents.recent_estate_entries(FEED, AS_OF)
    assert sorted((e["cveID"], e["estate_product"]) for e in found) == sorted(
        [
            ("CVE-2026-0004", "Rockwell Automation PlantPAx"),
            ("CVE-2026-0001", "Oracle E-Business Suite"),
        ]
    )


def test_loader_stores_fact_rows_with_the_catalogue_link(tmp_path, monkeypatch):
    monkeypatch.setattr(incidents, "fetch_kev", lambda: FEED)
    conn = store.connect(tmp_path / "app.db")
    store.create_schema(conn)
    run_id = store.start_run(conn, "manual")
    assert incidents.load_incidents(conn, run_id, as_of=AS_OF) == 2
    rows = tech_metrics.recent_incidents(conn, AS_OF)
    assert {r["cve"] for r in rows} == {"CVE-2026-0001", "CVE-2026-0004"}
    assert all(r["source_url"] == incidents.KEV_PAGE for r in rows)
    evidence = {r["evidence_label"] for r in conn.execute("SELECT evidence_label FROM incident")}
    assert evidence == {"Fact"}


def test_metric_window_edges(tmp_path, monkeypatch):
    monkeypatch.setattr(incidents, "fetch_kev", lambda: FEED)
    conn = store.connect(tmp_path / "app.db")
    store.create_schema(conn)
    run_id = store.start_run(conn, "manual")
    incidents.load_incidents(conn, run_id, as_of=AS_OF)
    # 30 days before 9 Nov is 10 Oct: an entry dated 20 Oct is in, one dated 1 Sep is out.
    later = tech_metrics.recent_incidents(conn, date(2026, 11, 9))
    assert "CVE-2026-0002" not in {r["cve"] for r in later}
    earlier = tech_metrics.recent_incidents(conn, date(2026, 10, 20))
    assert "CVE-2026-0001" in {r["cve"] for r in earlier}


def test_failed_download_raises_rather_than_showing_zero(monkeypatch):
    class Response:
        status_code = 503

    monkeypatch.setattr(requests, "get", lambda *a, **k: Response())
    with pytest.raises(incidents.IncidentError):
        incidents.fetch_kev()


def test_no_check_yet_means_no_check_date(tmp_path):
    conn = store.connect(tmp_path / "app.db")
    store.create_schema(conn)
    assert tech_metrics.last_successful_check(conn) is None
