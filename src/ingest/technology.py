"""End-of-support register for the Technology screen (CD-29).

Estate items are products that public sources show in use at Cytiva (case studies, vendor
press releases, conference decks). The use is Signal: the source shows it, Cytiva has not
confirmed it. The vendor status is written only where the vendor states a date or commitment,
and carries that statement. Where no vendor date was found it reads "to collect".
"""

from __future__ import annotations

import sqlite3

from src.ingest import store

# (product, where it is used, vendor support status, source URL)
ESTATE: tuple[tuple[str, str, str, str], ...] = (
    (
        "Oracle E-Business Suite",
        "Finance ERP (GE-legacy estate), moved to Oracle Cloud Infrastructure",
        "Premier Support committed through at least 2037 (Oracle PDF). Release in use: to collect.",
        "https://www.centroid.com/customer_stories/cytiva-success-story/",
    ),
    (
        "SAP Service Cloud (Pall field service)",
        "Field service at Pall, later part of Cytiva",
        "Cloud service, vendor-managed: no end-of-support date. On-premise SAP ECC: mainstream "
        "end 31 Dec 2027 per third-party reading of SAP policy; applies only if ECC is in use.",
        "https://blog.asug.com/hubfs/2019%20AC%20Slide%20Decks%20Thursday/ASUG83146%20-%20Field%20Service%20Automation%20with%20SAP%20Service%20Cloud%20at%20Pall%20Corporation.pdf",
    ),
    (
        "Rockwell Automation PlantPAx",
        "Process control in Cytiva manufacturing",
        "to collect: no PlantPAx lifecycle date found; check the installed release.",
        "https://www.rockwellautomation.com/en-us/company/news/case-studies/cytiva-bringing-digital-manufacturing-to-life.html",
    ),
    (
        "Genetec security platform",
        "Physical security at Cytiva sites",
        "to collect: vendor lifecycle not checked.",
        "https://www.securitymagazine.com/articles/97110-case-study-biotech-firm-cytiva-hardens-physical-security",
    ),
)


def load_estate_register(conn: sqlite3.Connection, run_id: int) -> int:
    """Store the estate items with their sources. Returns rows written."""
    written = 0
    for product, where_used, vendor_status, url in ESTATE:
        row = {
            "product": product,
            "where_used": where_used,
            "vendor_support_status": vendor_status,
            "source_url": url,
            "source_type": "document",
            "published_date": None,
            "evidence_label": "Signal",
        }
        if store.upsert(conn, run_id, "estate_item", row) != "rejected":
            written += 1
    return written
