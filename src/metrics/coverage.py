"""Competitor coverage screen (screen 2): footprint cells and bioprocess steps by region.

Families come from the footprint table (loaded from the research file). Steps are derived from
the families using the step map below, which matches the research file's 'Step map' tab:
a step is Made only when every family it needs is Made in the region.
"""

from __future__ import annotations

import sqlite3

from src.ingest.coverage import RESEARCH_FILE

# Step -> product families it needs (research file, footnote and 'Step map' tab).
STEP_FAMILIES: dict[str, tuple[str, ...]] = {
    "1. Research tools": ("Analytical",),
    "2. Cell line and process dev.": ("Genomic", "Media", "Single-use"),
    "3. Upstream processing": ("Media", "Single-use"),
    "4. Downstream processing": ("Resins", "Filtration"),
    "5. Formulation and fill-finish": ("Filling",),
    "6. QC and release testing": ("Analytical",),
    "7. Facility and automation": ("Systems",),
    "8. Service and support": (),  # from the Service row, not from families
}


def footprint_cells(conn: sqlite3.Connection) -> dict[tuple[str, str, str], dict]:
    """Stored family cells keyed by (company, region, family). A missing key is 'to collect'."""
    rows = conn.execute(
        "SELECT company_id, region_id, product_family, status, source_url FROM footprint"
    ).fetchall()
    return {
        (r["company_id"], r["region_id"], r["product_family"]): {
            "status": r["status"],
            "source_url": r["source_url"],
        }
        for r in rows
    }


def step_cells(cells: dict[tuple[str, str, str], dict]) -> dict[tuple[str, str, str], dict]:
    """Steps by (company, region, step): Made, Partial, Not made or To collect, with a source.

    Rule: Made if every needed family is Made. Partial if the only missing families are Partial
    (under construction or planned). Not made if a needed family has no evidence. Otherwise
    To collect (only unconfirmed leads stand in the way). Step 8 is Made when a Service row exists.
    """
    keys = {(co, region) for (co, region, _f) in cells}
    out: dict[tuple[str, str, str], dict] = {}
    for company, region in sorted(keys):
        for step, needs in STEP_FAMILIES.items():
            if not needs:  # step 8: service and support
                service = cells.get((company, region, "Service"))
                status = "Made" if service else "To collect"
                out[(company, region, step)] = {
                    "status": status,
                    "source_url": service["source_url"] if service else RESEARCH_FILE,
                }
                continue
            found = [cells.get((company, region, f)) for f in needs]
            statuses = [c["status"] if c else "To collect" for c in found]
            if all(s == "Made" for s in statuses):
                status = "Made"
            else:
                missing = [s for s in statuses if s != "Made"]
                if all(s == "Partial" for s in missing):
                    status = "Partial"
                elif "Not made" in missing:
                    status = "Not made"
                else:
                    status = "To collect"
            sources = [c["source_url"] for c in found if c and c["source_url"] != RESEARCH_FILE]
            public = [u for u in sources if "docs.google.com/spreadsheets" not in u]
            out[(company, region, step)] = {
                "status": status,
                "source_url": public[0] if public else RESEARCH_FILE,
            }
    return out
