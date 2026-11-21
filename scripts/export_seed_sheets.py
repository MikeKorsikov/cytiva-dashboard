"""Export the seed sheets to CSV, read only.

Every seed CSV under data/ comes from this script. Nothing is written to Google.
Each tab is fetched with a GET request to the sheet's public CSV endpoint (gviz) by tab name, and
the bytes are saved unchanged, so a re-export can be diffed against the committed file.

Usage:
    uv run python -m scripts.export_seed_sheets            # all sheets
    uv run python -m scripts.export_seed_sheets --only applications
    uv run python -m scripts.export_seed_sheets --dry-run  # print the plan, fetch nothing

Each file written is logged with its sheet ID, tab, row count and timestamp, to stdout and to
data/sheet_exports.log (appended).
"""

from __future__ import annotations

import argparse
import csv
import io
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG_PATH = ROOT / "data" / "sheet_exports.log"
GVIZ_URL = (
    "https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&headers=1&sheet={tab}"
)


@dataclass(frozen=True)
class SheetConfig:
    """One spreadsheet: its ID, the folder under data/ for its CSVs, and tab title -> file name.

    `filtered_tabs` lists tabs with an active filter. The CSV endpoint leaves out rows that a
    filter hides, so those tabs are not exported unless --allow-filtered is given.
    """

    key: str
    sheet_id: str
    folder: str
    tabs: dict[str, str] = field(default_factory=dict)
    filtered_tabs: frozenset[str] = frozenset()


SHEETS: tuple[SheetConfig, ...] = (
    SheetConfig(
        key="coverage",
        sheet_id="1EKU_0DEEWXGkAaFEWyrhT9WpdmlBRcgiPpTK6dcoqss",
        folder="data/coverage/sheet",
        tabs={
            "Sources": "sources.csv",
            "Peer sites": "peer_sites.csv",
            "T1 Coverage grid": "t1_coverage_grid.csv",
            "T2 Steps local": "t2_steps_local.csv",
            "T3 Supplier revenue": "t3_supplier_revenue.csv",
            "T3 Market size": "t3_market_size.csv",
            "T4 Region cards": "t4_region_cards.csv",
        },
    ),
    SheetConfig(
        key="register",
        sheet_id="1MPccYB-6lvaNS5HbDMP0kMzfpmMvQbL5fdorRQi27KM",
        folder="data/coverage/sheet",
        tabs={
            "Legal entities": "register_legal_entities.csv",
            "Sites": "register_sites.csv",
            "Value-chain coverage": "register_value_chain.csv",
            "Entity-site links": "register_entity_site_links.csv",
            "Sources": "register_sources.csv",
        },
    ),
    SheetConfig(
        key="overview",
        sheet_id="1k5MfRSdsziSTZgtIplwASKkCSlY3nLkfg8jpwqiA8Fg",
        folder="data/overview/sheet",
        tabs={
            "Attention": "attention.csv",
            "T1 Peer financials": "t1_peer_financials.csv",
            "T1 Rankings": "t1_rankings.csv",
            "T2 M&A": "t2_ma.csv",
            "T3 Share prices": "t3_share_prices.csv",
            "T4 Competitor news": "t4_competitor_news.csv",
            "T5 Implications": "t5_implications.csv",
            "Sources": "sources.csv",
        },
    ),
    SheetConfig(
        key="clusters",
        sheet_id="1asd0YHjtFgSCAmAeFbq_QIbYLXCc-AzjWgcZsTEteOk",
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
    SheetConfig(
        key="demand",
        sheet_id="12YV6UNxTET8WWUmzNG46KjQHeeFBBMaPS-zn-FM5-_o",
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
        },
    ),
    SheetConfig(
        key="technology",
        sheet_id="1Io-AbomyfDeRX-LOcxLNJ_YpaqiJbWVh8rSHsy_dgz4",
        folder="data/technology/sheet",
        tabs={
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
    SheetConfig(
        key="china",
        sheet_id="1wEndgjfRVTKSpNWlNFHdgZp_PWvnLnrca6UCHxzvvXI",
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
    SheetConfig(
        key="applications",
        sheet_id="16MYgBYe3_bxaSimXkR0UjoFcAHUe1gT-IkP8xhu1qKU",
        folder="data/technology/sheet",
        tabs={
            "Applications and technology": "applications.csv",
            "Size and complexity ranking": "ranking.csv",
            "Notes": "notes.csv",
            "Vendors": "vendors.csv",
            "Competitors": "competitors.csv",
        },
        # Filter on column 7 (Ad mentions 22 Oct 2026) hides 34 rows from the CSV endpoint.
        filtered_tabs=frozenset({"Applications and technology"}),
    ),
)


def gviz_url(sheet_id: str, tab: str) -> str:
    return GVIZ_URL.format(sheet_id=sheet_id, tab=urllib.parse.quote(tab, safe=""))


def fetch(sheet_id: str, tab: str) -> bytes:
    """GET only. Returns the CSV bytes exactly as the sheet gives them."""
    request = urllib.request.Request(gviz_url(sheet_id, tab), method="GET")
    with urllib.request.urlopen(request, timeout=60) as response:
        body = response.read()
    if not body.lstrip().startswith(b'"') and b"<html" in body[:200].lower():
        raise RuntimeError(f"tab {tab!r} of sheet {sheet_id} is not public or not found")
    return body


def normalise(body: bytes) -> bytes:
    """Re-write the CSV with minimal quoting and LF line ends, so an unchanged sheet gives a
    byte-identical file. Values are not changed."""
    rows = list(csv.reader(io.StringIO(body.decode("utf-8"), newline="")))
    out = io.StringIO(newline="")
    csv.writer(out, lineterminator="\n").writerows(rows)
    return out.getvalue().encode("utf-8")


def row_count(body: bytes) -> int:
    rows = list(csv.reader(io.StringIO(body.decode("utf-8"), newline="")))
    return max(len(rows) - 1, 0)


def log_line(sheet_id: str, tab: str, path: str, rows: int) -> str:
    stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    return f"{stamp}\tsheet={sheet_id}\ttab={tab!r}\tfile={path}\trows={rows}"


def export(sheet: SheetConfig, dry_run: bool, allow_filtered: bool) -> list[str]:
    lines: list[str] = []
    for tab, filename in sheet.tabs.items():
        rel = f"{sheet.folder}/{filename}"
        if tab in sheet.filtered_tabs and not allow_filtered:
            lines.append(
                f"SKIPPED\tsheet={sheet.sheet_id}\ttab={tab!r}\tfile={rel}\t"
                "reason=active filter hides rows from the CSV endpoint"
            )
            continue
        if dry_run:
            lines.append(f"plan\tsheet={sheet.sheet_id}\ttab={tab!r}\tfile={rel}")
            continue
        body = normalise(fetch(sheet.sheet_id, tab))
        target = ROOT / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
        lines.append(log_line(sheet.sheet_id, tab, rel, row_count(body)))
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--only", help="export one sheet by key, for example applications")
    parser.add_argument("--dry-run", action="store_true", help="print the plan only")
    parser.add_argument(
        "--allow-filtered",
        action="store_true",
        help="export tabs with an active filter anyway (the export is then partial)",
    )
    args = parser.parse_args(argv)

    selected = [s for s in SHEETS if args.only in (None, s.key)]
    if not selected:
        print(f"no sheet with key {args.only!r}", file=sys.stderr)
        return 2

    all_lines: list[str] = []
    for sheet in selected:
        all_lines.extend(export(sheet, args.dry_run, args.allow_filtered))

    for line in all_lines:
        print(line)
    if not args.dry_run:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write("\n".join(all_lines) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
