"""Competitor coverage (screen 2) from the seed sheets, loaded into the app database.

Sources of truth, read from data/coverage/sheet/ (exports of the live tabs, read only):
- Coverage sheet 1EKU: Sources, Peer sites, T1 Coverage grid, T4 Region cards.
- Danaher and Cytiva register 1MPcc: Sites (Cytiva's site count per family comes from here).

The research file 1C1vMJ is not read for displayed data. Its export is kept in
data/coverage/research/ for the diff only. Every stored row keeps its sheet source ID and URL.
Cells the sheet shows as ? are not stored: a missing cell is ? on the screen.

Confidence of a grid cell is the best confidence of the rows behind it (H, then M, then L).
Evidence label: Fact for H, Signal otherwise (the display maps L to UNCONFIRMED).
"""

from __future__ import annotations

import csv
import re
import sqlite3
from collections import defaultdict
from pathlib import Path

from src.ingest import store

REPO_ROOT = Path(__file__).resolve().parents[2]
SHEET_DIR = REPO_ROOT / "data" / "coverage" / "sheet"
REGISTER_SOURCE = "S19"  # the Danaher & Cytiva site register, a pointer for site counts

NA = "North America"
WE = "Western Europe"
HG = "High-growth markets"
JP = "Other developed markets"  # the sheet's name for the fourth region

COMPANY_NAMES = {
    "CYT": "Cytiva",
    "TMO": "Thermo Fisher",
    "SRT": "Sartorius",
    "RGN": "Repligen",
    "AVT": "Avantor",
    "MRK": "Merck KGaA",
}
FAMILIES = (
    "Media",
    "Single-use",
    "Resins",
    "Filtration",
    "Filling",
    "Genomic",
    "Systems",
    "Analytical",
)
# Register stage (Value-chain stages made here) -> product family. A stage named in a site's
# text counts that site toward the family.
STAGE_FAMILY = {
    "Cell culture media": "Media",
    "Single-use and bioreactors": "Single-use",
    "Chromatography resins": "Resins",
    "Filtration": "Filtration",
    "Fill-finish": "Filling",
    "Genomic medicine": "Genomic",
    "Process hardware": "Systems",
    "Discovery and analytics": "Analytical",
}
CONFIDENCE_RANK = {"H": 0, "M": 1, "L": 2}


def _read(name: str) -> list[dict]:
    with (SHEET_DIR / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def label_for(confidence: str) -> str:
    return "Fact" if confidence == "H" else "Signal"


def parse_families(text: str) -> list[tuple[str, bool]]:
    """'Single-use; Systems' -> [('Single-use', False), ('Systems', False)];
    'Single-use (partial)' -> [('Single-use', True)]."""
    out = []
    for piece in (text or "").split(";"):
        piece = piece.strip()
        if not piece:
            continue
        partial = "(partial)" in piece.lower()
        out.append((re.sub(r"\s*\(partial\)", "", piece, flags=re.I).strip(), partial))
    return out


def stage_families(text: str) -> set[str]:
    """Product families named by a register site's Value-chain stages."""
    lowered = (text or "").lower()
    return {fam for stage, fam in STAGE_FAMILY.items() if stage.lower() in lowered}


def _best(rows: list[tuple[str, str]]) -> tuple[str, str]:
    """(confidence, source_id) of the strongest row: H before M before L."""
    return min(rows, key=lambda r: CONFIDENCE_RANK[r[0]])


def load_coverage(conn: sqlite3.Connection, run_id: int, report: list[str] | None = None) -> int:
    """Load the screen 2 sheet tabs. Returns the number of rows accepted. Re-runnable: rows are
    upserted by their sheet IDs. Values that cannot be parsed are appended to `report` as
    'ID: cell' and are not stored."""
    report = report if report is not None else []
    accepted = 0

    def put(table: str, row: dict, source_id: str, label: str | None = None) -> None:
        nonlocal accepted
        source = sources.get(source_id)
        if source is None:
            report.append(
                f"{table} {row.get('site_id') or row.get('region_id')}: unknown source {source_id}"
            )
            return
        row.update(
            {
                "source_url": source["URL"],
                "source_type": "document",
                "published_date": None,
                "evidence_label": label or label_for(row["confidence"]),
            }
        )
        if store.upsert(conn, run_id, table, row) != "rejected":
            accepted += 1

    sources = {r["ID"]: r for r in _read("sources.csv")}
    for sid, src in sources.items():
        row = {
            "id": sid,
            "title": src["Title"],
            "publisher": src["Publisher"],
            "date_text": src["Date"],
            "url": src["URL"],
            "confidence": "H",
        }
        put("s2_source", row, sid, label="Fact")

    # Peer sites (1EKU, Peer sites)
    peer_families: dict[tuple[str, str, str], list[tuple[str, str]]] = defaultdict(list)
    for raw in _read("peer_sites.csv"):
        site_id = raw["Site ID"]
        row = {
            "site_id": site_id,
            "company": raw["Company"],
            "site": raw["Site"],
            "country": raw["Country"],
            "region_id": raw["Danaher region"],
            "evidence": raw["Evidence (summary of source)"],
            "source_id": raw["Source ID"],
            "confidence": raw["Confidence"],
        }
        put("s2_peer_site", row, raw["Source ID"])
        for family, partial in parse_families(raw["Families made"]):
            if family not in FAMILIES:
                report.append(f"{site_id}: unknown family {family!r} in Families made")
                continue
            peer_families[(raw["Company"], raw["Danaher region"], family)].append(
                (raw["Confidence"], raw["Source ID"])
            )
            put(
                "s2_peer_family",
                {
                    "site_id": site_id,
                    "family": family,
                    "partial": int(partial),
                    "confidence": raw["Confidence"],
                },
                raw["Source ID"],
            )

    # Cytiva sites (register, Sites tab)
    cyt_families: dict[tuple[str, str], list[tuple[str, str]]] = defaultdict(list)
    for raw in _read("register_sites.csv"):
        site_id = raw["Site ID"]
        confidence = raw["Confidence (H/M/L)"]
        row = {
            "site_id": site_id,
            "site": raw["Site"],
            "country": raw["Country"],
            "region_id": raw["Danaher reporting region"],
            "site_type": raw["Site type"],
            "activities": raw["Activities seen"],
            "presence": raw["Presence"],
            "heritage": raw["Heritage"],
            "evidence": raw["Evidence"],
            "linked_entities": raw["Linked entities"],
            "stages_made": raw["Value-chain stages made here"],
            "stage_evidence": raw["Stage evidence"],
            "source_id": REGISTER_SOURCE,
            "confidence": confidence,
        }
        put("s2_cyt_site", row, REGISTER_SOURCE)
        for family in stage_families(raw["Value-chain stages made here"]):
            cyt_families[(raw["Danaher reporting region"], family)].append(
                (confidence, REGISTER_SOURCE)
            )

    # Coverage grid (1EKU, T1 Coverage grid): one row per company, region and family
    grid = list(csv.reader((SHEET_DIR / "t1_coverage_grid.csv").open(encoding="utf-8", newline="")))
    regions, codes = grid[0][1:], grid[1][1:]
    for line in grid[2:]:
        family = line[0]
        for region, code, status in zip(regions, codes, line[1:], strict=True):
            if status == "?":
                continue  # not stored: no evidence
            company = COMPANY_NAMES[code]
            cell_id = f"grid {company} / {region} / {family}"
            if code == "CYT":
                contributing = cyt_families.get((region, family), [])
                if status == "Not made":
                    confidence, source_id = "M", REGISTER_SOURCE  # checked absence, register
                elif contributing:
                    confidence, source_id = _best(contributing)
                else:
                    report.append(f"{cell_id}: {status} with no register site")
                    continue
            else:
                contributing = peer_families.get((company, region, family), [])
                if not contributing:
                    report.append(f"{cell_id}: {status} with no peer site")
                    continue
                confidence, source_id = _best(contributing)
            put(
                "s2_grid",
                {
                    "company_id": company,
                    "region_id": region,
                    "family": family,
                    "status": status,
                    "confidence": confidence,
                    "source_id": source_id,
                },
                source_id,
            )

    # Biotech sales by region (1EKU, T4 Region cards; sales from the Q1 2026 10-Q, S20)
    for raw in _read("t4_region_cards.csv"):
        region = raw["Region"]
        row = {
            "region_id": region,
            "value_m": float(raw["Biotech sales Q1 2026 ($m)"].replace(",", "")),
            "period": "Q1 2026 (three months ended 27 Mar 2026)",
            "quote": raw["Sales evidence (quote)"],
            "source_id": raw["Source IDs"],
            "confidence": raw["Confidence"],
        }
        put("s2_biotech_sales", row, raw["Source IDs"])

    conn.commit()
    return accepted
