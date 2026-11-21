"""Header maps for the seed sheet exports of screens 2 and 6 (and the register).

Each export is read through its map: a dict of sheet header -> field name used by the loader.
read_sheet() fails loudly when a file has a header the map does not know, or when a mapped header
is missing. A changed header in the sheet therefore stops the load instead of being read silently.
"""

from __future__ import annotations

import csv
from pathlib import Path

DATA_ROOT = Path(__file__).resolve().parents[2] / "data"

_CHINA_COMPANIES = {
    "ID": "ID",
    "Company (EN)": "Company (EN)",
    "Company (CN)": "Company (CN)",
    "Listed?": "Listed?",
    "Exchange code": "Exchange code",
    "Ownership / status": "Ownership / status",
    "Main business": "Main business",
    "Source IDs": "Source IDs",
    "Confidence": "Confidence",
}

HEADER_MAPS: dict[str, dict[str, str]] = {
    "china/sheet/companies.csv": _CHINA_COMPANIES,
    "china/sheet/coverage_evidence.csv": {
        "Evidence ID": "Evidence ID",
        "Company ID": "Company ID",
        "Family": "Family",
        "Status": "Status",
        "Evidence (quote)": "Evidence (quote)",
        "Source IDs": "Source IDs",
        "Source date": "Source date",
        "Confidence": "Confidence",
    },
    "china/sheet/coverage_grid.csv": {
        "ID": "ID",
        "Company": "Company",
        "Med (media)": "Med (media)",
        "SU (single-use)": "SU (single-use)",
        "Res (resins)": "Res (resins)",
        "Filt (filtration)": "Filt (filtration)",
        "Fill (filling)": "Fill (filling)",
        "Gen (genomic)": "Gen (genomic)",
        # The sheet now writes a comma; the loader keys on the older semicolon form.
        "Sys (systems, bioreactors)": "Sys (systems; bioreactors)",
        "Anl (analytical)": "Anl (analytical)",
        "Families evidenced": "Families evidenced",
        "Step 8 service in China": "Step 8 service in China",
    },
    "china/sheet/financials.csv": {
        "ID": "ID",
        "Company ID": "Company ID",
        "Company": "Company",
        "Code": "Code",
        "Period": "Period",
        "Revenue (RMB m)": "Revenue (RMB m)",
        "Revenue YoY %": "Revenue YoY %",
        "Gross margin %": "Gross margin %",
        "R&D / revenue %": "R&D / revenue %",
        "Net profit attrib. (RMB m)": "Net profit attrib. (RMB m)",
        "Revenue (USD bn)": "Revenue (USD bn)",
        "Basis": "Basis",
        "Source IDs": "Source IDs",
        "Confidence": "Confidence",
        "Notes": "Notes",
    },
    "china/sheet/headline.csv": {
        "ID": "ID",
        "Metric": "Metric",
        "Value": "Value",
        "Unit": "Unit",
        "Period": "Period",
        "Show on tile?": "Show on tile?",
        "Evidence (quote)": "Evidence (quote)",
        "Source IDs": "Source IDs",
        "Confidence": "Confidence",
        "Notes": "Notes",
    },
    "china/sheet/implications.csv": {
        "ID": "ID",
        "Hypothesis (not a finding)": "Hypothesis (not a finding)",
        "Based on": "Based on",
        "What would confirm or refute it": "What would confirm or refute it",
        "Area": "Area",
        "Confidence": "Confidence",
    },
    "china/sheet/opportunities.csv": {
        "ID": "ID",
        "Opportunity": "Opportunity",
        "Why (evidence summary)": "Why (evidence summary)",
        "Product lines": "Product lines",
        "Label": "Label",
        "Evidence (quote)": "Evidence (quote)",
        "Source IDs": "Source IDs",
        "Source date": "Source date",
        "Confidence": "Confidence",
    },
    "china/sheet/sources.csv": {
        "ID": "ID",
        "Title": "Title",
        "Publisher": "Publisher",
        "Date": "Date",
        "URL": "URL",
        "Type": "Type",
        "Notes": "Notes",
    },
    "china/sheet/vendors.csv": {
        "ID": "ID",
        "Vendor (EN)": "Vendor (EN)",
        "Vendor (CN)": "Vendor (CN)",
        "Code": "Code",
        "Supplies": "Supplies",
        "To (Danaher company)": "To (Danaher company)",
        "Relationship type": "Relationship type",
        "Evidence (quote)": "Evidence (quote)",
        "Source IDs": "Source IDs",
        "Confidence": "Confidence",
    },
    "coverage/sheet/sources.csv": {
        "ID": "ID",
        "Title": "Title",
        "Publisher": "Publisher",
        "Date": "Date",
        "URL": "URL",
        "Type": "Type",
    },
    "coverage/sheet/peer_sites.csv": {
        "Site ID": "Site ID",
        "Company": "Company",
        "Site": "Site",
        "Country": "Country",
        "Danaher region": "Danaher region",
        "Families made": "Families made",
        "Evidence (summary of source)": "Evidence (summary of source)",
        "Source ID": "Source ID",
        "Confidence": "Confidence",
    },
    "coverage/sheet/register_sites.csv": {
        "Site ID": "Site ID",
        "Site": "Site",
        "Country": "Country",
        "Region": "Region",
        "Site type": "Site type",
        "Activities seen": "Activities seen",
        "Presence": "Presence",
        "Heritage": "Heritage",
        "Evidence": "Evidence",
        "Confidence (H/M/L)": "Confidence (H/M/L)",
        "Source": "Source",
        "Linked entities": "Linked entities",
        "Danaher reporting region": "Danaher reporting region",
        "Value-chain stages made here": "Value-chain stages made here",
        "Stage evidence": "Stage evidence",
        "Source URL": "Source URL",
        "Source quote": "Source quote",
        "Source date": "Source date",
        "Service evidence (region)": "Service evidence (region)",
        "Service quote": "Service quote",
        "Service source URL": "Service source URL",
    },
    "coverage/sheet/t3_market_size.csv": {
        "ID": "ID",
        "Estimate": "Estimate",
        "Value (USD bn)": "Value (USD bn)",
        "Year": "Year",
        "Publisher": "Publisher",
        "Scope": "Scope",
        "Share figures given": "Share figures given",
        "Use on tile": "Use on tile",
        "Evidence (quote)": "Evidence (quote)",
        "Source IDs": "Source IDs",
        "Confidence": "Confidence",
    },
    "coverage/sheet/t3_supplier_revenue.csv": {
        "ID": "ID",
        "Company": "Company",
        "Reported unit": "Reported unit",
        "FY2025 revenue (reported currency, m)": "FY2025 revenue (reported currency, m)",
        "Currency": "Currency",
        "FY2025 revenue (USD m)": "FY2025 revenue (USD m)",
        "Share of disclosed peer pool": "Share of disclosed peer pool",
        "Growth (as reported)": "Growth (as reported)",
        "Scope of the unit": "Scope of the unit",
        "Evidence (quote)": "Evidence (quote)",
        "Source IDs": "Source IDs",
        "Confidence": "Confidence",
    },
    "coverage/sheet/t4_region_cards.csv": {
        "Region": "Region",
        "Cytiva families made (of 8)": "Cytiva families made (of 8)",
        "Cytiva steps local (of 8)": "Cytiva steps local (of 8)",
        "Biotech sales Q1 2026 ($m)": "Biotech sales Q1 2026 ($m)",
        "Share of Biotech sales": "Share of Biotech sales",
        "Peers with a site found": "Peers with a site found",
        "Source IDs": "Source IDs",
        "Confidence": "Confidence",
        "Sales evidence (quote)": "Sales evidence (quote)",
    },
}


def read_sheet(path: Path) -> list[dict]:
    """Read one export through its header map. Keys are the field names of the map.

    Raises ValueError if the file has no map, a header the map does not know, or a mapped header
    that is missing from the file."""
    key = path.resolve().relative_to(DATA_ROOT.resolve()).as_posix()
    if key not in HEADER_MAPS:
        raise ValueError(f"{key}: no header map")
    mapping = HEADER_MAPS[key]
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames or []
        unknown = [h for h in headers if h not in mapping]
        missing = [h for h in mapping if h not in headers]
        if unknown or missing:
            raise ValueError(f"{key}: unmapped headers {unknown}, missing headers {missing}")
        return [{mapping[h]: (v or "") for h, v in row.items()} for row in reader]
