"""Actively exploited vulnerabilities in the Cytiva estate, last 30 days (CD-30).

Source: CISA Known Exploited Vulnerabilities (KEV) catalogue, an official list of CVEs with
evidence of active exploitation. Only entries whose vendor matches a product in the
end-of-support register (src/ingest/technology.py) are kept. The window is rolling: an entry
counts when CISA added it to the catalogue within the last 30 days.

A failed download raises, so the refresh run is marked failed rather than showing a false zero.
"""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta

import requests

from src.ingest import store

KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
KEV_PAGE = "https://www.cisa.gov/known-exploited-vulnerabilities-catalog"
WINDOW_DAYS = 30
TIMEOUT_SECONDS = 60

# KEV vendor name fragment -> the estate product it relates to (see technology.ESTATE).
ESTATE_VENDORS: dict[str, str] = {
    "Oracle": "Oracle E-Business Suite",
    "SAP": "SAP Service Cloud (Pall field service)",
    "Rockwell": "Rockwell Automation PlantPAx",
    "Genetec": "Genetec security platform",
}


class IncidentError(RuntimeError):
    """Raised when the KEV catalogue cannot be downloaded or read."""


def fetch_kev() -> dict:
    try:
        response = requests.get(
            KEV_URL, timeout=TIMEOUT_SECONDS, headers={"User-Agent": "cytiva-dashboard/0.1"}
        )
    except requests.RequestException as exc:
        raise IncidentError(f"KEV download failed: {exc}") from exc
    if response.status_code != 200:
        raise IncidentError(f"KEV returned HTTP {response.status_code}")
    try:
        return response.json()
    except ValueError as exc:
        raise IncidentError("KEV response is not JSON") from exc


def estate_product(vendor_project: str) -> str | None:
    for fragment, product in ESTATE_VENDORS.items():
        if fragment.lower() in vendor_project.lower():
            return product
    return None


def recent_estate_entries(feed: dict, as_of: date) -> list[dict]:
    """KEV entries added in the window that relate to an estate product."""
    start = (as_of - timedelta(days=WINDOW_DAYS)).isoformat()
    end = as_of.isoformat()
    found = []
    for entry in feed.get("vulnerabilities", []):
        added = entry.get("dateAdded", "")
        product = estate_product(entry.get("vendorProject", ""))
        if product and start <= added <= end:
            found.append({**entry, "estate_product": product})
    return found


def load_incidents(conn: sqlite3.Connection, run_id: int, as_of: date | None = None) -> int:
    """Store the estate entries added in the window. Returns rows written."""
    as_of = as_of or date.today()
    feed = fetch_kev()
    written = 0
    for entry in recent_estate_entries(feed, as_of):
        cve = entry.get("cveID", "")
        row = {
            "vendor": entry.get("vendorProject", ""),
            "incident_date": entry["dateAdded"],
            "title": f"{cve}: {entry.get('vulnerabilityName', '')}".strip(": "),
            "incident_type": "actively exploited (CISA KEV)",
            "cve": cve,
            "estate_link": entry["estate_product"],
            "relevance": entry.get("shortDescription", ""),
            "source_url": KEV_PAGE,
            "source_type": "API",
            "published_date": entry["dateAdded"],
            "evidence_label": "Fact",
        }
        if store.upsert(conn, run_id, "incident", row) != "rejected":
            written += 1
    return written
