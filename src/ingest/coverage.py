"""Competitor coverage (screen 2) from the seed sheets, loaded into the app database.

Sources of truth, read from data/coverage/sheet/ (exports of the live tabs, read only):
- Coverage sheet 1EKU: Sources, Peer sites, T1 Coverage grid, T4 Region cards.
- Danaher and Cytiva register 1MPcc: Sites (Cytiva's sites, their evidence and service evidence).

The research file 1C1vMJ is not read for displayed data. Its export is kept in
data/coverage/research/ for the diff only. Every stored row keeps its sheet source ID and URL.
A missing cell is ? on the screen, and cells the sheet shows as ? are not stored.

Peer cells: the T1 grid is the displayed value; its confidence is the best of the Peer sites
rows behind it (H, M, L).

Cytiva cells are derived from the register, not copied from T1 (approved decisions, screen 2):
- a family is Made when a site in the region is evidenced for it ("Evidenced: ..." stage
  evidence) and the site is producing;
- Partial when the only evidenced site is not yet producing ("from 2028", "start 2026"), with
  that site's confidence, or when the family rests only on hypothesis rows (confidence L);
- Not made when no site in the region names the family.
The T1 Cytiva column is checked against this and every difference is written to the report.

Step 8 for Cytiva comes from the register's service evidence, one row per region (Made or
Partial, confidence M). With no service evidence, step 8 is ?.

Evidence label: Fact for H, Signal otherwise (the display maps L to UNCONFIRMED).
"""

from __future__ import annotations

import csv
import re
import sqlite3
from collections import defaultdict
from pathlib import Path

from src.ingest import store
from src.ingest.sheet_headers import read_sheet

REPO_ROOT = Path(__file__).resolve().parents[2]
SHEET_DIR = REPO_ROOT / "data" / "coverage" / "sheet"
REGISTER_SOURCE = "S19"  # the Danaher & Cytiva site register: a pointer, used when no primary URL
SITE_ID = re.compile(r"ST\d+")

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
# Register stage (Value-chain stages made here) -> product family.
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
# Words that name a family in the evidenced part of a mixed stage-evidence text.
EVIDENCE_WORD = {
    "Resins": "resin",
    "Filtration": "filtration",
    "Single-use": "single-use",
    "Media": "media",
    "Filling": "fill",
    "Genomic": "genomic",
    "Systems": "hardware",
    "Analytical": "analytic",
}
PEER_SITE_ID = re.compile(r"PS-\d+")
MARKET_ID = re.compile(r"MS-\d+")
SUPPLIER_ID = re.compile(r"SR-\d+")
GRID_FAMILIES = (
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


def first_source_id(text: str) -> str:
    """The first S-ID in a Source IDs cell, for example "S03" from "S03, S04"."""
    return re.search(r"S\d+", text).group(0)


def _read(name: str) -> list[dict]:
    return read_sheet(SHEET_DIR / name)


def label_for(confidence: str) -> str:
    return "Fact" if confidence == "H" else "Signal"


def parse_families(text: str) -> list[tuple[str, bool]]:
    """'Single-use; Systems' -> [('Single-use', False), ('Systems', False)];
    'Single-use (partial)' -> [('Single-use', True)]."""
    out = []
    for piece in re.split(r"[;,]", text or ""):
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


def site_evidence(stages: str, evidence: str) -> tuple[set[str], set[str]]:
    """(evidenced families, hypothesis families) for one register site.

    'Hypothesis' evidence makes every family a hypothesis. Mixed evidence such as
    'Evidenced: public source (resins); hypothesis (others)' evidences the families named before
    '; hypothesis'. Anything else is evidenced."""
    named = stage_families(stages)
    lowered = (evidence or "").lower().strip()
    if not lowered or lowered.startswith("hypothesis"):
        return set(), named
    if re.search(r";\s*hypothesis", lowered):
        part = re.split(r";\s*hypothesis", lowered)[0]
        evidenced = {f for f in named if EVIDENCE_WORD[f] in part}
        return evidenced, named - evidenced
    return named, set()


def is_producing(stages: str) -> bool:
    """A site not yet producing names its start year in its stages ('from 2028', 'start 2026')."""
    return not re.search(r"\b(from|start) 20\d\d", stages or "")


def _best(rows: list[tuple[str, str]]) -> tuple[str, str]:
    """(confidence, url) of the strongest row: H before M before L."""
    return min(rows, key=lambda r: CONFIDENCE_RANK[r[0]])


def load_coverage(conn: sqlite3.Connection, run_id: int, report: list[str] | None = None) -> int:
    """Load the screen 2 sheet tabs. Returns the number of rows accepted. Re-runnable: rows are
    upserted by their sheet IDs. Values that cannot be parsed are appended to `report` as
    'ID: cell'. Differences from the T1 grid's Cytiva column are appended as 'T1 vs register'."""
    report = report if report is not None else []
    accepted = 0

    def put(table: str, row: dict, url: str, label: str | None = None) -> None:
        nonlocal accepted
        row.update(
            {
                "source_url": url,
                "source_type": "document",
                "published_date": None,
                "evidence_label": label or label_for(row.get("confidence", "M")),
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
        }
        put("s2_source", row, src["URL"], label="Fact")
    register_url = sources[REGISTER_SOURCE]["URL"]

    # Peer sites (1EKU, Peer sites)
    peer_families: dict[tuple[str, str, str], list[tuple[str, str]]] = defaultdict(list)
    for raw in _read("peer_sites.csv"):
        site_id = raw["Site ID"]
        if not PEER_SITE_ID.fullmatch(site_id):
            continue  # the Note row under the peer sites
        source = sources.get(raw["Source ID"])
        if source is None:
            report.append(f"{site_id}: unknown source {raw['Source ID']}")
            continue
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
        put("s2_peer_site", row, source["URL"])
        for family, partial in parse_families(raw["Families made"]):
            if family not in FAMILIES:
                report.append(f"{site_id}: unknown family {family!r} in Families made")
                continue
            peer_families[(raw["Company"], raw["Danaher region"], family)].append(
                (raw["Confidence"], source["URL"])
            )
            put(
                "s2_peer_family",
                {
                    "site_id": site_id,
                    "family": family,
                    "partial": int(partial),
                    "confidence": raw["Confidence"],
                },
                source["URL"],
            )

    # Register (Sites tab): site rows are those whose ID matches ST<n>; other rows are notes
    cyt_sites: list[dict] = []
    for raw in _read("register_sites.csv"):
        site_id = raw["Site ID"].strip()
        if not SITE_ID.fullmatch(site_id):
            if site_id:
                put(
                    "screen_notes",
                    {"tab": "Sites (register)", "label": site_id, "text": raw["Site"]},
                    register_url,
                    label="Signal",
                )
            continue
        primary = raw.get("Source URL", "").strip()
        url = primary or register_url
        stages, evidence = raw["Value-chain stages made here"], raw["Stage evidence"]
        evidenced, hypothesis = site_evidence(stages, evidence)
        # Column S holds the service status for the site's Danaher region (step 8 evidence).
        service_region = (
            raw["Danaher reporting region"] if raw.get("Service evidence (region)") else None
        )
        site = {
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
            "stages_made": stages,
            "stage_evidence": evidence,
            "source_id": REGISTER_SOURCE,
            "primary_url": int(bool(primary)),
            "source_quote": raw.get("Source quote", "") or None,
            "source_date": raw.get("Source date", "") or None,
            "service_region": service_region,
            "service_status": raw.get("Service evidence (region)", "").strip() or None,
            "service_quote": raw.get("Service quote", "") or None,
            "confidence": raw["Confidence (H/M/L)"],
        }
        put("s2_cyt_site", site, url)
        cyt_sites.append(
            {
                "site_id": site_id,
                "region": raw["Danaher reporting region"],
                "named": stage_families(stages),
                "evidenced": evidenced,
                "producing": is_producing(stages),
                "confidence": raw["Confidence (H/M/L)"],
                "url": url,
            }
        )
        service_url = (raw.get("Service source URL", "") or "").split(" ; ")[0].strip()
        if service_status := site["service_status"]:
            if service_status not in ("Made", "Partial") or not service_url:
                report.append(f"{site_id}: service evidence {service_status!r} without a URL")
            else:
                put(
                    "s2_grid",
                    {
                        "company_id": "Cytiva",
                        "region_id": site["region_id"],
                        "family": "Service",
                        "status": service_status,
                        "confidence": "M",
                        "source_id": site_id,
                    },
                    service_url,
                )

    def cytiva_cell(region: str, family: str) -> tuple[str, str, str] | None:
        """(status, confidence, url) for a Cytiva family in a region, or None when no site
        names the family (then the cell is Not made)."""
        named = [s for s in cyt_sites if s["region"] == region and family in s["named"]]
        if not named:
            return None
        made = [s for s in named if family in s["evidenced"] and s["producing"]]
        not_yet = [s for s in named if family in s["evidenced"] and not s["producing"]]
        if made:
            conf, url = _best([(s["confidence"], s["url"]) for s in made])
            return "Made", conf, url
        if not_yet:
            conf, url = _best([(s["confidence"], s["url"]) for s in not_yet])
            return "Partial", conf, url
        _, url = _best([(s["confidence"], s["url"]) for s in named])
        return "Partial", "L", url  # hypothesis only

    # Coverage grid (1EKU, T1 Coverage grid): one row per company, region and family
    grid = list(csv.reader((SHEET_DIR / "t1_coverage_grid.csv").open(encoding="utf-8", newline="")))
    regions, codes = grid[0][1:], grid[1][1:]
    for line in grid[2:]:
        family = line[0]
        if family not in GRID_FAMILIES:
            continue  # blank line and the Key, Regions and Cytiva column notes below the grid
        for region, code, sheet_status in zip(regions, codes, line[1:], strict=True):
            company = COMPANY_NAMES[code]
            cell_id = f"grid {company} / {region} / {family}"
            if code == "CYT":
                derived = cytiva_cell(region, family)
                status = derived[0] if derived else "Not made"
                confidence, url = (derived[1], derived[2]) if derived else ("M", register_url)
                if status != sheet_status and sheet_status != "?":
                    report.append(
                        f"T1 vs register: {cell_id}: T1 {sheet_status}, register {status}"
                    )
                if sheet_status == "?":
                    report.append(f"T1 vs register: {cell_id}: T1 says ?, register gives {status}")
                put(
                    "s2_grid",
                    {
                        "company_id": company,
                        "region_id": region,
                        "family": family,
                        "status": status,
                        "confidence": confidence,
                        "source_id": REGISTER_SOURCE,
                    },
                    url,
                )
                continue
            if sheet_status == "?":
                continue  # not stored: no evidence
            contributing = peer_families.get((company, region, family), [])
            if not contributing:
                report.append(f"{cell_id}: {sheet_status} with no peer site")
                continue
            confidence, url = _best(contributing)
            put(
                "s2_grid",
                {
                    "company_id": company,
                    "region_id": region,
                    "family": family,
                    "status": sheet_status,
                    "confidence": confidence,
                    "source_id": _source_id(sources, url),
                },
                url,
            )

    # Biotech sales by region (1EKU, T4 Region cards; sales from the Q1 2026 10-Q, S20)
    for raw in _read("t4_region_cards.csv"):
        if not re.fullmatch(r"\d[\d,]*(\.\d+)?", raw["Biotech sales Q1 2026 ($m)"].strip()):
            continue  # blank rows, notes and implications have no sales figure
        # Source IDs read "S20 (sales); S19 (Cytiva sites); S10-S17 (peers)". The sales figure
        # and its confidence come from the "(sales)" part only.
        sales_id = re.search(r"(S\d+) \(sales\)", raw["Source IDs"]).group(1)
        sales_conf = re.search(r"([HML]) \(sales\)", raw["Confidence"]).group(1)
        source = sources[sales_id]
        row = {
            "region_id": raw["Region"],
            "value_m": float(raw["Biotech sales Q1 2026 ($m)"].replace(",", "")),
            "period": "Q1 2026 (three months ended 27 Mar 2026)",
            "quote": raw["Sales evidence (quote)"],
            "source_id": sales_id,
            "confidence": sales_conf,
        }
        put("s2_biotech_sales", row, source["URL"])

    # Tile 3 inputs (1EKU, T3 Market size and T3 Supplier revenue). Only MS- and SR- rows load.
    for raw in _read("t3_market_size.csv"):
        if not MARKET_ID.fullmatch(raw["ID"]):
            continue
        source_id = first_source_id(raw["Source IDs"])
        put(
            "s2_market_size",
            {
                "id": raw["ID"],
                "estimate": raw["Estimate"],
                "value_usd_bn": float(raw["Value (USD bn)"].replace(",", "")),
                "year": int(raw["Year"]),
                "publisher": raw["Publisher"],
                "scope": raw["Scope"],
                "share_figures": raw["Share figures given"],
                "use_on_tile": raw["Use on tile"],
                "quote": raw["Evidence (quote)"],
                "source_id": source_id,
                "confidence": raw["Confidence"],
            },
            sources[source_id]["URL"],
        )
    for raw in _read("t3_supplier_revenue.csv"):
        if not SUPPLIER_ID.fullmatch(raw["ID"]):
            continue
        source_id = first_source_id(raw["Source IDs"])
        usd = raw["FY2025 revenue (USD m)"].replace(",", "").strip()
        put(
            "s2_supplier_revenue",
            {
                "id": raw["ID"],
                "company": raw["Company"],
                "reported_unit": raw["Reported unit"],
                "revenue_reported_m": raw["FY2025 revenue (reported currency, m)"],
                "currency": raw["Currency"],
                "revenue_usd_m": float(usd) if re.fullmatch(r"\d+(\.\d+)?", usd) else None,
                "share_of_pool": raw["Share of disclosed peer pool"],
                "growth_reported": raw["Growth (as reported)"],
                "scope": raw["Scope of the unit"],
                "quote": raw["Evidence (quote)"],
                "source_id": source_id,
                "confidence": raw["Confidence"],
            },
            sources[source_id]["URL"],
        )

    conn.commit()
    return accepted


def _source_id(sources: dict, url: str) -> str:
    """The sheet source ID whose URL is `url` (or the register ID for a register link)."""
    for sid, src in sources.items():
        if src["URL"] == url:
            return sid
    return REGISTER_SOURCE
