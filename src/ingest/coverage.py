"""Product families and bioprocess steps by region, for the Competitor coverage screen (screen 2).

Source: the research file "Competitor footprint evidence" (Google Sheets), tab Evidence, saved
as data/coverage/evidence.csv. One row per site and product family, with its source link and a
confidence mark. The research file is the single record; this module only reads it.

Rules (the same as the research file's Grid and Steps tabs):
- Family cell Made (✓): at least one evidence row says Made for that family in the region.
- Partial (◐): no Made row, but one row is under construction or planned.
- Not made (×): no evidence at all. Linked to the research file.
- To collect (?): only unconfirmed leads ("To confirm"). No row is stored.
- "Service only" rows (contract services) are recorded but not counted.
- Step 8 (service and support) is Made when the company has a Service row in the region.
- Other steps are derived from the families they need (see metrics/coverage.py).

Each stored cell keeps the source link of the strongest evidence behind it (H, then M, then L).
"""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

from src.ingest import store

REPO_ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_CSV = REPO_ROOT / "data" / "coverage" / "evidence.csv"
RESEARCH_FILE = (
    "https://docs.google.com/spreadsheets/d/1C1vMJGXnCm1mNIvrPBoK5qIYdp5-2hWYYDUpBJa5g2c/edit"
)

NA = "North America"
WE = "Western Europe"
HG = "High-growth markets"
JP = "Japan, Australia and New Zealand"

COMPANY_IDS = {
    "CYT": "Cytiva",
    "TMO": "Thermo Fisher",
    "SRT": "Sartorius",
    "RGN": "Repligen",
    "AVT": "Avantor",
    "MRK": "Merck KGaA",
}
REGION_NAMES = {
    "North America": NA,
    "Western Europe": WE,
    "High-growth markets": HG,
    "Japan, Aus. & NZ": JP,
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
CONFIDENCE_RANK = {"H": 0, "M": 1, "L": 2}


def read_evidence(path: Path = EVIDENCE_CSV) -> list[dict]:
    """Evidence rows, with company and region names normalised to the screen's names."""
    with path.open(encoding="utf-8", newline="") as handle:
        rows = []
        for raw in csv.DictReader(handle):
            rows.append(
                {
                    **raw,
                    "company_id": COMPANY_IDS[raw["company"]],
                    "region_id": REGION_NAMES[raw["region"]],
                }
            )
    return rows


def derive_cells(rows: list[dict]) -> list[dict]:
    """One footprint cell per company, region and family (or service) that the evidence supports."""
    cells = []
    keys = sorted({(r["company_id"], r["region_id"]) for r in rows})
    for company, region in keys:
        mine = [r for r in rows if r["company_id"] == company and r["region_id"] == region]
        for family in FAMILIES:
            matches = [r for r in mine if r["product_family"] == family]
            made = [r for r in matches if r["status"] == "Made"]
            partial = [r for r in matches if r["status"] == "Partial"]
            if made:
                cells.append(_cell(company, region, family, "Made", _best(made)))
            elif partial:
                cells.append(_cell(company, region, family, "Partial", _best(partial)))
            elif any(r["status"] == "To confirm" for r in matches):
                continue  # only leads: shown as to collect; no cell is stored
            else:
                cells.append(_cell(company, region, family, "Not made", None))
        service = [r for r in mine if r["product_family"] == "Service" and r["status"] == "Made"]
        if service:
            cells.append(_cell(company, region, "Service", "Made", _best(service)))
    return cells


def _best(rows: list[dict]) -> dict:
    """Strongest evidence: a public source before a research sheet, then by confidence."""
    return min(rows, key=lambda r: (is_research_sheet(r["url"]), CONFIDENCE_RANK[r["confidence"]]))


def is_research_sheet(url: str) -> bool:
    """True for links to our own research spreadsheets, which are not public evidence."""
    return "docs.google.com/spreadsheets" in url


def _cell(company: str, region: str, family: str, status: str, evidence: dict | None) -> dict:
    return {
        "company_id": company,
        "region_id": region,
        "product_family": family,
        "status": status,
        "source_url": evidence["url"] if evidence else RESEARCH_FILE,
        "source_type": "document",
        "published_date": None,
        "evidence_label": "Fact",
    }


def load_coverage(conn: sqlite3.Connection, run_id: int) -> int:
    """Store the evidence rows and the derived family and service cells. Returns cells written."""
    rows = read_evidence()
    for r in rows:
        store.upsert(
            conn,
            run_id,
            "footprint_evidence",
            {
                "evidence_id": r["id"],
                "company_id": r["company_id"],
                "region_id": r["region_id"],
                "product_family": r["product_family"],
                "status": r["status"],
                "site": r["site"],
                "what_it_makes": r["what_it_makes"],
                "timing": r["timing"],
                "confidence": r["confidence"],
                "note": r["note"],
                "source_url": r["url"],
                "source_type": "document",
                "published_date": None,
                "evidence_label": "Fact",
            },
        )
    written = 0
    for cell in derive_cells(rows):
        if store.upsert(conn, run_id, "footprint", cell) != "rejected":
            written += 1
    return written
