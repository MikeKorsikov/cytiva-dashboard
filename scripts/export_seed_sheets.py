"""Export the seed sheets to CSV, read only.

Every seed CSV under data/ comes from this script. Nothing is written to Google.

Sheet IDs and tab gids come from seed_sheet_gids.yaml (repo root). Each tab is fetched with the
plain export URL, which returns the displayed values as text:

    https://docs.google.com/spreadsheets/d/<sheet_id>/export?format=csv&gid=<gid>

The gviz endpoint is not used: it guesses one type per column and blanks the text values in
mixed numeric and text columns.

Usage:
    uv run python -m scripts.export_seed_sheets               # all groups
    uv run python -m scripts.export_seed_sheets --only applications
    uv run python -m scripts.export_seed_sheets --dry-run     # print the plan, fetch nothing

Each file written is logged with sheet ID, tab, row count and timestamp, to stdout and to
data/sheet_exports.log (appended).
"""

from __future__ import annotations

import argparse
import csv
import io
import sys
import urllib.request
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
GIDS_PATH = ROOT / "seed_sheet_gids.yaml"
LOG_PATH = ROOT / "data" / "sheet_exports.log"
EXPORT_URL = "https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"


@dataclass(frozen=True)
class SheetConfig:
    """One export group. `key` is the yaml key, `folder` the data/ folder for its CSVs.

    `tabs` maps tab title -> file name. A tab not listed here is not exported.
    `filtered_tabs` lists tabs with a basic filter, which would hide rows from the export.
    """

    key: str
    folder: str
    tabs: dict[str, str] = field(default_factory=dict)
    filtered_tabs: frozenset[str] = frozenset()


SHEETS: dict[str, SheetConfig] = {
    "overview": SheetConfig(
        key="screen1_overview",
        folder="data/overview/sheet",
        tabs={
            "README": "readme.csv",
            "Attention": "attention.csv",
            "T1 Peer financials": "t1_peer_financials.csv",
            "T1 Rankings": "t1_rankings.csv",
            "T2 M&A": "t2_ma.csv",
            "T3 Share prices": "t3_share_prices.csv",
            "T4 Competitor news": "t4_competitor_news.csv",
            "T5 Implications": "t5_implications.csv",
            "Sources": "sources.csv",
            "T6 Layoffs": "layoffs.csv",
        },
    ),
    "coverage": SheetConfig(
        key="screen2_coverage",
        folder="data/coverage/sheet",
        tabs={
            "Sources": "sources.csv",
            "Peer sites": "peer_sites.csv",
            "T1 Coverage grid": "t1_coverage_grid.csv",
            "T2 Steps local": "t2_steps_local.csv",  # export only: the app computes the steps
            "T3 Supplier revenue": "t3_supplier_revenue.csv",
            "T3 Market size": "t3_market_size.csv",
            "T4 Region cards": "t4_region_cards.csv",
            "T5 Implications": "t5_implications.csv",
        },
    ),
    "register": SheetConfig(
        key="cytiva_sites_register",
        folder="data/coverage/sheet",
        # Legal entities, Entity-site links and Sources are not exported (owner decision).
        tabs={
            "Sites": "register_sites.csv",
            "Value-chain coverage": "register_value_chain.csv",  # export only: formulas
        },
    ),
    "clusters": SheetConfig(
        key="screen3_clusters",
        folder="data/clusters/sheet",
        tabs={
            "Clusters": "clusters.csv",
            "Country barriers": "country_barriers.csv",
            "Demand by country": "demand_by_country.csv",
            "Demand by region": "demand_by_region.csv",
            "Research institutions": "research_institutions.csv",
            "CDMO sites": "cdmo_sites.csv",
            "Market signals": "market_signals.csv",
            "Data Sources": "data_sources.csv",
        },
    ),
    "demand": SheetConfig(
        key="screen4_demand",
        folder="data/demand/sheet",
        tabs={
            "T1 Disease burden": "t1_disease_burden.csv",
            "T2 Top 10 countries": "t2_top10_countries.csv",
            "T3 Pipeline by type": "t3_pipeline_by_type.csv",
            "T4 Approvals & expiries": "t4_approvals_expiries.csv",
            "T5 Policy & funding": "t5_policy_funding.csv",
            "T6 Biggest drugs": "t6_biggest_drugs.csv",
            "T7 Capacity pledges": "t7_capacity_pledges.csv",
            "T8 Products used": "t8_products_used.csv",
            "Sources": "sources.csv",
            "T9 Implications": "implications.csv",
        },
    ),
    "technology": SheetConfig(
        key="screen5_technology",
        folder="data/technology/sheet",
        tabs={
            "README": "readme.csv",
            "T1 End of support": "eos.csv",
            "T2 Incidents 30 days": "incidents.csv",
            "T2 Watchlist": "watchlist.csv",
            "T2 Feeds": "feeds.csv",
            "T2 Rules": "rules.csv",
            "T3 Integration readiness": "integrations.csv",
            "T4 Adoption signals": "adoption.csv",
            "T5 Implications": "implications.csv",
            "Estate evidence": "estate_evidence.csv",
            "Sources": "sources.csv",
        },
    ),
    "china": SheetConfig(
        key="screen6_china",
        folder="data/china/sheet",
        tabs={
            "H Headline figures": "headline.csv",
            "T1 Companies": "companies.csv",
            "T1 Coverage grid": "coverage_grid.csv",
            "T1 Coverage evidence": "coverage_evidence.csv",
            "T2 Financials": "financials.csv",
            "T3 Vendors": "vendors.csv",
            "T4 Opportunities": "opportunities.csv",
            "T5 Implications": "implications.csv",
            "Sources": "sources.csv",
        },
    ),
    "applications": SheetConfig(
        key="applications_list",
        folder="data/technology/sheet",
        tabs={
            "Applications and technology": "applications.csv",
            "Size and complexity ranking": "ranking.csv",
            "Notes": "notes.csv",
            "Vendors": "vendors.csv",
            "Competitors": "competitors.csv",
        },
    ),
}


def load_gids(path: Path = GIDS_PATH) -> dict:
    """The sheet IDs and tab gids, by yaml key."""
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def export_url(sheet_id: str, gid: int) -> str:
    return EXPORT_URL.format(sheet_id=sheet_id, gid=gid)


def fetch(sheet_id: str, gid: int) -> bytes:
    """GET only, following redirects. Returns the CSV bytes as the sheet gives them."""
    request = urllib.request.Request(export_url(sheet_id, gid), method="GET")
    with urllib.request.urlopen(request, timeout=60) as response:
        body = response.read()
    if b"<html" in body[:200].lower():
        raise RuntimeError(f"gid {gid} of sheet {sheet_id} is not public or not found")
    return body


def normalise(body: bytes) -> bytes:
    """Re-write the CSV with minimal quoting and LF line ends, so an unchanged sheet gives a
    byte-identical file. Values are not changed. Trailing columns with no header are dropped."""
    rows = list(csv.reader(io.StringIO(body.decode("utf-8"), newline="")))
    # Width is the last column that holds a value in ANY row. Using row 0 alone cut tabs whose
    # first row is a one-cell title (T4 Approvals & expiries lost every column but A).
    last_used = [max((i + 1 for i, v in enumerate(row) if v != ""), default=0) for row in rows]
    width = max(last_used, default=0)
    rows = [row[:width] + [""] * max(0, width - len(row)) for row in rows]
    out = io.StringIO(newline="")
    csv.writer(out, lineterminator="\n").writerows(rows)
    return out.getvalue().encode("utf-8")


def row_count(body: bytes) -> int:
    rows = list(csv.reader(io.StringIO(body.decode("utf-8"), newline="")))
    return max(len(rows) - 1, 0)


def log_line(sheet_id: str, tab: str, path: str, rows: int) -> str:
    stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    return f"{stamp}\tsheet={sheet_id}\ttab={tab!r}\tfile={path}\trows={rows}"


def export(config: SheetConfig, gids: dict, dry_run: bool, allow_filtered: bool) -> list[str]:
    sheet_id = gids[config.key]["sheet_id"]
    tab_gids = gids[config.key]["tabs"]
    lines: list[str] = []
    for tab, filename in config.tabs.items():
        rel = f"{config.folder}/{filename}"
        if tab not in tab_gids:
            lines.append(f"MISSING\tsheet={sheet_id}\ttab={tab!r}\tnot in seed_sheet_gids.yaml")
            continue
        if tab in config.filtered_tabs and not allow_filtered:
            lines.append(f"SKIPPED\tsheet={sheet_id}\ttab={tab!r}\tfile={rel}\treason=filtered")
            continue
        if dry_run:
            lines.append(f"plan\tsheet={sheet_id}\ttab={tab!r}\tgid={tab_gids[tab]}\tfile={rel}")
            continue
        body = normalise(fetch(sheet_id, tab_gids[tab]))
        target = ROOT / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
        lines.append(log_line(sheet_id, tab, rel, row_count(body)))
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--only", help="export one group, for example applications")
    parser.add_argument("--dry-run", action="store_true", help="print the plan only")
    parser.add_argument("--allow-filtered", action="store_true", help="export filtered tabs")
    args = parser.parse_args(argv)

    if args.only is not None and args.only not in SHEETS:
        print(f"no export group {args.only!r}; choose from {sorted(SHEETS)}", file=sys.stderr)
        return 2
    gids = load_gids()
    all_lines: list[str] = []
    for name, config in SHEETS.items():
        if args.only in (None, name):
            all_lines.extend(export(config, gids, args.dry_run, args.allow_filtered))

    for line in all_lines:
        print(line)
    if not args.dry_run:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write("\n".join(all_lines) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
