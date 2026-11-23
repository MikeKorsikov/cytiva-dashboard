"""Competitor coverage (screen 2) and China (screen 6): product-family cells and bioprocess steps.

One step rule, used by both screens (approved in the audit, decision 1):
- a step needs a set of product families (STEP_FAMILIES);
- all of them Made: Made;
- any of them unknown (no cell): ?;
- some Made or Partial: Partial;
- otherwise: Not made.
Step 8 (service and support) is Made only when a Service row is Made in the region; with no
evidence row it is ?. Step 8 is shown but not counted.
"""

from __future__ import annotations

import sqlite3

# Step -> product families it needs (approved, audit decision 1).
STEP_FAMILIES: dict[str, tuple[str, ...]] = {
    "1. Research tools": ("Analytical",),
    "2. Cell line and process dev.": ("Genomic", "Media", "Single-use"),
    "3. Upstream processing": ("Media", "Single-use"),
    "4. Downstream processing": ("Resins", "Filtration"),
    "5. Formulation and fill-finish": ("Filling",),
    "6. QC and release testing": ("Analytical",),
    "7. Facility and automation": ("Systems",),
    "8. Service and support": (),  # from a Service row, not from families
}
SERVICE_FAMILY = "Service"


def grid_cells(conn: sqlite3.Connection) -> dict[tuple[str, str, str], dict]:
    """Stored grid cells keyed by (company, region, family). A missing key is ?."""
    rows = conn.execute(
        "SELECT company_id, region_id, family, status, confidence, source_url FROM s2_grid"
    ).fetchall()
    return {
        (r["company_id"], r["region_id"], r["family"]): {
            "status": r["status"],
            "confidence": r["confidence"],
            "source_url": r["source_url"],
        }
        for r in rows
    }


def step_status(statuses: list[str | None]) -> str:
    """The step rule on family statuses. None means no cell (?)."""
    if statuses and all(s == "Made" for s in statuses):
        return "Made"
    if any(s is None for s in statuses):
        return "?"
    if any(s in ("Made", "Partial") for s in statuses):
        return "Partial"
    return "Not made"


def step_cells(cells: dict[tuple[str, str, str], dict]) -> dict[tuple[str, str, str], dict]:
    """Steps by (company, region, step): Made, Partial, Not made or ?, with a source.

    Companies and regions are those in `cells`. Step 8 reads the Service row only.
    """
    keys = {(co, region) for (co, region, _f) in cells}
    out: dict[tuple[str, str, str], dict] = {}
    for company, region in sorted(keys):
        for step, needs in STEP_FAMILIES.items():
            if not needs:
                service = cells.get((company, region, SERVICE_FAMILY))
                status = (
                    service["status"]
                    if service and service["status"] in ("Made", "Partial", "Not made")
                    else "?"
                )
                out[(company, region, step)] = {
                    "status": status,
                    "source_url": service["source_url"] if service else None,
                }
                continue
            found = [cells.get((company, region, f)) for f in needs]
            status = step_status([c["status"] if c else None for c in found])
            sources = [c["source_url"] for c in found if c and c["source_url"]]
            out[(company, region, step)] = {
                "status": status,
                "source_url": sources[0] if sources else None,
            }
    return out


def implications(conn: sqlite3.Connection) -> list[dict]:
    """Screen 2 hypotheses from the sheet's T5 tab (B-17). Always Hypothesis. Empty until loaded."""
    try:
        rows = conn.execute("SELECT * FROM s2_implication ORDER BY id").fetchall()
    except sqlite3.OperationalError:
        return []
    return [dict(r) for r in rows]


def biotech_sales(conn: sqlite3.Connection) -> dict[str, dict]:
    """Biotechnology sales by Danaher region, Q1 2026, with the share of the four regions."""
    rows = conn.execute(
        "SELECT region_id, value_m, period, quote, confidence, source_url FROM s2_biotech_sales"
    ).fetchall()
    total = sum(r["value_m"] for r in rows)
    return {
        r["region_id"]: {
            "value_m": r["value_m"],
            "share": r["value_m"] / total * 100 if total else None,
            "period": r["period"],
            "quote": r["quote"],
            "confidence": r["confidence"],
            "source_url": r["source_url"],
            "total_m": total,
        }
        for r in rows
    }
