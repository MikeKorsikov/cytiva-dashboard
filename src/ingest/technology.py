"""Technology estate data (Screen 5), from the research sheet "Screen 5 - Technology data".

The sheet's tabs are saved as CSV under data/technology/ and loaded here. Every row is validated
by its ID pattern, its confidence (H, M or L) and its sources. A row without a source is
rejected by store.upsert, except a Hypothesis row (tile 5), which is labelled as such.

Dates are kept as the text the sheet gives and parsed into date_value, date_precision and
is_floor (for "at least" dates). Source IDs are split into row_sources; the source_note keeps
the full text.
"""

from __future__ import annotations

import csv
import re
import sqlite3
from datetime import date
from pathlib import Path

from src.ingest import store
from src.ingest.sheet_headers import read_sheet

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data" / "technology"
CONFIDENCE = ("H", "M", "L")
MONTHS = {
    m: i
    for i, m in enumerate(
        ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1
    )
}

# Header maps: sheet column header -> field name used by the loader and the database.
# Every header in a sheet export must appear here. An unmapped or missing header fails the load.
HEADER_MAPS: dict[str, dict[str, str]] = {
    "sheet/eos.csv": {
        "ID": "id",
        "Product / version": "product",
        "Where used (estate)": "where_used",
        "Estate evidence": "estate_evidence",
        "Estate confidence": "estate_confidence",
        "Support milestone": "support_milestone",
        "Milestone date": "milestone_date_text",
        "Next milestone / paid options": "next_milestone",
        "Status at 16 Nov 2026": "status_text",
        "Vendor-date evidence (quote)": "vendor_date_quote",
        "Source IDs": "source_ids",
        "Date confidence": "date_confidence",
        "Show on tile": "show_on_tile",
        "Reason": "reason",
        "Tile note (one line under the date)": "tile_note",
        "Application (list Name)": "application",
    },
    "sheet/incidents.csv": {
        "ID": "id",
        "Date (UTC)": "date_text",
        "Vendor": "vendor",
        "Product": "product",
        "Watchlist ID": "watchlist_id",
        "Type": "type",
        "What happened": "what_happened",
        "Vendor statement": "vendor_statement",
        "Tier A sources (n)": "tier_a_count",
        "Tier B sources (n)": "tier_b_count",
        "Corroborated?": "corroborated",
        "Product match": "product_match",
        "Type for score": "type_for_score",
        "Estate confidence": "estate_confidence",
        "Relevance (0-7)": "relevance",
        "Action": "action",
        "Days old": "days_old",
        "In 30-day window?": "in_window",
        "Evidence (quote)": "evidence_quote",
        "Source IDs": "source_ids",
        "Application (list Name)": "application",
    },
    "sheet/watchlist.csv": {
        "Watch ID": "watch_id",
        "Vendor": "vendor",
        "Products in estate": "products_in_estate",
        "Operating company": "operating_company",
        "Estate evidence IDs": "estate_evidence_ids",
        "Estate confidence": "estate_confidence",
        "News filter keywords": "news_keywords",
        "Advisory / status feed IDs": "feed_ids",
        "Notes": "notes",
        "Applications (list Name)": "applications",
    },
    "sheet/feeds.csv": {
        "Feed ID": "feed_id",
        "Tier": "tier",
        "Source": "source",
        "What it gives": "what_it_gives",
        "URL / endpoint": "endpoint",
        "Format": "format",
        "Refresh": "refresh",
        "Watchlist IDs": "watch_ids",
        "Reachable from this workspace?": "reachable_from_workspace",
        "Notes": "notes",
    },
    "sheet/integrations.csv": {
        "ID": "id",
        "System": "system",
        "Group": "readiness_group",
        "Interfaces available": "interfaces_available",
        "Estate evidence": "estate_evidence",
        "Estate confidence": "estate_confidence",
        "Vendor interface evidence": "vendor_interface_evidence",
        "Source IDs": "source_ids",
        "Capability confidence": "capability_confidence",
        "Notes": "notes",
    },
    "sheet/adoption.csv": {
        "ID": "id",
        "Technology": "technology",
        "Level": "level",
        "Signal": "signal",
        "Signal date": "signal_date_text",
        "Who": "who",
        "Evidence (quote)": "evidence_quote",
        "Source IDs": "source_ids",
        "Confidence": "confidence",
        "Gartner 2026 trend link": "gartner_trend_link",
    },
    "sheet/implications.csv": {
        "ID": "id",
        "Hypothesis (not a finding)": "hypothesis",
        "Based on": "based_on",
        "What would confirm or refute it": "confirm_or_refute",
        "Area": "area",
        "Confidence": "confidence",
    },
    "sheet/estate_evidence.csv": {
        "ID": "id",
        "System": "system",
        "Operating company": "operating_company",
        "Evidence (quote)": "evidence_quote",
        "Source ID": "source_ids",
        "Seen": "seen_date",
        "Confidence": "confidence",
        "Applications (list Name)": "applications",
    },
    "sheet/sources.csv": {
        "ID": "id",
        "Title": "title",
        "Publisher": "publisher",
        "Date": "date_text",
        "URL": "url",
        "Notes": "notes",
        "Tier (tile 2)": "tier",
        "Type": "type",  # Primary or Secondary (sheet column H); used by the badge rule
    },
}

GARTNER_COLUMNS: list[tuple[str, str | None]] = [
    ("G26 ID", "id"),
    ("Gartner Top Strategic Technology Trend 2026", "trend"),
    ("Cytiva / Danaher signal", "cytiva_danaher_signal"),
    ("", None),
    ("Release date", "release_date"),
    ("Publisher", "publisher"),
    ("Evidence", "evidence"),
    ("Source IDs", "source_ids"),
    ("Confidence", "confidence"),
    ("", None),
]

# (csv file, table, natural key column, id pattern, source-link column or None).
# The id pattern is matched with fullmatch, so a note row such as "Gap" is never a data row.
SPECS = (
    ("sheet/eos.csv", "tech_eos", "id", r"EOS-\d+", "source_ids"),
    ("sheet/incidents.csv", "tech_incidents", "id", r"(INC|REF)-\d+", "source_ids"),
    ("sheet/watchlist.csv", "tech_watchlist", "watch_id", r"W\d+", None),
    ("sheet/feeds.csv", "tech_feeds", "feed_id", r"F\d+", None),
    ("sheet/integrations.csv", "tech_integrations", "id", r"INT-\d+", "source_ids"),
    # The T4 tab holds the Gartner 2026 rows (G26-) in a second section below the ADO rows.
    # Each section is loaded once, from its own spec. There is no separate gartner.csv.
    ("sheet/adoption.csv", "tech_adoption", "id", r"ADO-\d+", "source_ids"),
    ("sheet/adoption.csv#gartner", "tech_gartner", "id", r"G26-\d+", "source_ids"),
    ("sheet/implications.csv", "tech_implications", "id", r"IMP-\d+", None),
    ("sheet/estate_evidence.csv", "tech_estate_evidence", "id", r"EST-\d+", "source_ids"),
    ("sheet/sources.csv", "tech_sources", "id", r"S\d+", None),
)
# Tab title of each sheet file: the screen_notes tab for its note rows.
TAB_OF_FILE: dict[str, str] = {
    "sheet/eos.csv": "T1 End of support",
    "sheet/incidents.csv": "T2 Incidents 30 days",
    "sheet/watchlist.csv": "T2 Watchlist",
    "sheet/feeds.csv": "T2 Feeds",
    "sheet/integrations.csv": "T3 Integration readiness",
    "sheet/adoption.csv": "T4 Adoption signals",
    "sheet/implications.csv": "T5 Implications",
    "sheet/estate_evidence.csv": "Estate evidence",
    "sheet/sources.csv": "Sources",
}


def parse_date(text: str | None) -> tuple[date | None, str | None, bool]:
    """Sheet date text -> (date_value, date_precision, is_floor). See the import rules."""
    t = (text or "").strip()
    if not t or t.lower() in ("n/a",) or t.startswith("seen"):
        return None, None, False
    floor = t.lower().startswith("at least")
    body = re.sub(r"^at least\s+", "", t, flags=re.I)
    body = re.sub(r"\s*\(.*\)$", "", body).strip()  # drop "(rolling)" and "(job ads)"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", body):
        return date.fromisoformat(body), "day", False
    m = re.fullmatch(r"(\d{1,2}) ([A-Za-z]{3}) (\d{4})", body)
    if m and m.group(2).lower() in MONTHS:
        return date(int(m.group(3)), MONTHS[m.group(2).lower()], int(m.group(1))), "day", False
    if re.fullmatch(r"\d{4}-\d{2}", body):
        y, mo = body.split("-")
        return date(int(y), int(mo), 1), "month", False
    if re.fullmatch(r"\d{4}", body):
        if floor:
            return date(int(body), 12, 31), "year", True
        return None, None, False  # a bare year without "at least" is shown as text only
    return None, None, False


def source_ids(text: str | None) -> list[str]:
    return re.findall(r"S\d+", text or "")


GARTNER_SECTION = "G26 ID"  # first cell of the Gartner header row inside the adoption tab


def _columns(name: str) -> list[tuple[str, str | None]]:
    """The header map for a file or section, as ordered (sheet header, field) pairs.
    A field of None means the column is read but not stored."""
    if name.endswith("#gartner"):
        return GARTNER_COLUMNS
    return list(HEADER_MAPS[name].items())


def _rows(name: str) -> list[dict]:
    """Read a sheet export, or one section of it, and rename each column with its header map.

    A name ending in "#gartner" reads the Gartner section of the adoption tab. The ADO section is
    the rows above that section. The header row must match the map exactly, in order, otherwise
    the load fails: a changed or unmapped header is never read silently."""
    file, _, section = name.partition("#")
    with (DATA_DIR / file).open(encoding="utf-8", newline="") as handle:
        table = list(csv.reader(handle))
    if section == "gartner":
        head = next(i for i, r in enumerate(table) if r[:1] == [GARTNER_SECTION])
        body = table[head + 1 :]
    else:
        head = 0
        body = table[1:]
        if file == "sheet/adoption.csv":
            cut = next((i for i, r in enumerate(body) if r[:1] == [GARTNER_SECTION]), len(body))
            body = body[:cut]
    columns = _columns(name)
    if table[head] != [h for h, _ in columns]:
        raise ValueError(f"{name}: header row changed; expected {[h for h, _ in columns]}")
    rows = []
    for values in body:
        if not any(v.strip() for v in values):
            continue
        if len(values) > len(columns):
            raise ValueError(f"{name}: row has {len(values)} cells, the map has {len(columns)}")
        padded = values + [""] * (len(columns) - len(values))
        rows.append(
            {field: value for (_, field), value in zip(columns, padded, strict=True) if field}
        )
    return rows


def _raw_rows(name: str) -> list[dict]:
    """Plain read, for exports that have no header map (ranking, applications notes)."""
    with (DATA_DIR / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _readme_notes() -> list[dict]:
    """The README tab is free text: each row with two or more cells is a note (tab "README")."""
    notes = []
    with (DATA_DIR / "sheet" / "readme.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.reader(handle):
            values = [v.strip() for v in row if v and v.strip()]
            if len(values) >= 2:
                notes.append({"tab": "README", "label": values[0], "text": values[-1]})
    return notes


def _note_rows(name: str) -> list[dict]:
    """Rows of a sheet export that are not data rows (no valid ID) become screen_notes. The label
    is the first non-empty cell and the text is the last non-empty cell."""
    _, _, key, pattern, _ = next(spec for spec in SPECS if spec[0] == name)
    notes = []
    for raw in _rows(name):
        if re.fullmatch(pattern, raw[key] or ""):
            continue
        values = [v.strip() for v in raw.values() if v and v.strip()]
        if len(values) >= 2:
            notes.append({"tab": TAB_OF_FILE[name], "label": values[0], "text": values[-1]})
    return notes


def load_technology(conn: sqlite3.Connection, run_id: int) -> int:
    """Store the screen 5 rows. Returns the number of rows accepted. Re-runnable: rows are
    upserted by their ID, so a second run changes nothing."""
    sources = {r["id"]: r for r in _rows("sheet/sources.csv")}
    evidence = {r["id"]: r for r in _rows("sheet/estate_evidence.csv")}
    written = 0
    for filename, table, key, pattern, link_col in SPECS:
        for raw in _rows(filename):
            if not re.fullmatch(pattern, raw[key] or ""):
                continue  # notes, rules and section labels are not data rows
            if table == "tech_eos" and raw[key] == "EOS-08":
                # The S/4HANA target is not an end-of-support item: a screen note only, and no
                # footnote on the tile (review item 1, 22 Nov 2026).
                conn.execute(
                    "INSERT OR REPLACE INTO screen_notes (tab, label, text, source_url, "
                    "source_type, loaded_at, evidence_label, verification_status) VALUES "
                    "('T1 End of support', ?, ?, '', 'curated', ?, 'Fact', 'passed')",
                    (raw["product"], raw["next_milestone"], store.now_iso()),
                )
                conn.execute("DELETE FROM tech_eos WHERE id = 'EOS-08'")  # a row from before
                continue
            row = {k: (v.strip() if v and v.strip() else None) for k, v in raw.items()}
            if table == "tech_feeds" and raw.get("tier") == "C":
                continue  # leads only: never a source, never shown
            ids = source_ids(raw.get(link_col)) if link_col else []
            if table == "tech_watchlist":
                est = re.findall(r"EST-\d+", raw["estate_evidence_ids"] or "")
                ids = source_ids(" ".join(evidence[e]["source_ids"] for e in est if e in evidence))
            url = next((sources[s]["url"] for s in ids if s in sources), None)
            if table == "tech_sources":
                url = raw["url"]
            if table == "tech_feeds":
                url = raw["endpoint"] if raw.get("endpoint", "").startswith("https://") else None
            label = {"Fact": "Fact"}.get(raw.get("label") or "", None)
            confidence = (
                raw.get("confidence")
                or raw.get("date_confidence")
                or raw.get("capability_confidence")
                or ""
            )
            if table == "tech_implications":
                label = "Hypothesis"
            row.update(
                {
                    "source_url": url or "",
                    "source_type": "document" if url else "curated",
                    "published_date": None,
                    "evidence_label": label
                    or (
                        "Hypothesis"
                        if table == "tech_implications"
                        else "Signal"
                        if confidence == "L"
                        else "Fact"
                    ),
                }
            )
            if table == "tech_eos":
                value, precision, floor = parse_date(raw["milestone_date_text"])
                row.update(
                    {
                        "date_value": value.isoformat() if value else None,
                        "date_precision": precision,
                        "is_floor": int(floor),
                        "date_text": raw["milestone_date_text"] or None,
                        "source_note": raw["source_ids"],
                    }
                )
            if table == "tech_incidents":
                row["source_note"] = raw["source_ids"]
                row["date_value"] = raw["date_text"]
            if store.upsert(conn, run_id, table, row) == "rejected":
                continue
            written += 1
            for s in ids:
                if s not in sources:
                    continue
                store.upsert(
                    conn,
                    run_id,
                    "tech_row_sources",
                    {
                        "row_type": table,
                        "row_id": raw[key],
                        "source_id": s,
                        "source_url": sources[s]["url"],
                        "source_type": "document",
                        "published_date": None,
                        "evidence_label": "Fact",
                    },
                )
    for raw in [
        note for filename in TAB_OF_FILE for note in _note_rows(filename)
    ] + _readme_notes():
        conn.execute(
            "INSERT OR REPLACE INTO screen_notes (tab, label, text, source_url, source_type, "
            "loaded_at, evidence_label, verification_status) VALUES (?, ?, ?, '', 'curated', ?, "
            "'Fact', 'passed')",
            (raw["tab"], raw["label"], raw["text"], store.now_iso()),
        )
    load_apps(conn, run_id)
    conn.commit()
    return written


def load_app_list(conn: sqlite3.Connection, run_id: int) -> int:
    """The applications list (Name is the key), read through its header map. Analyst work, so
    the rows are Hypothesis with no URL, as the ranking is."""
    written = 0
    for row in read_sheet(DATA_DIR / "sheet" / "applications.csv"):
        row.update(
            {
                "source_url": "",
                "source_type": "curated",
                "published_date": None,
                "evidence_label": "Hypothesis",
            }
        )
        if store.upsert(conn, run_id, "tech_app_list", row) != "rejected":
            written += 1
    conn.commit()
    return written


def load_apps(conn: sqlite3.Connection, run_id: int) -> int:
    """Application ranking (size and complexity), from the applications sheet's "Size and
    complexity ranking" tab (data/technology/sheet/ranking.csv). The scores are analyst
    judgements, so they are stored as Hypothesis, with the sheet's scoring confidence and no
    URL: the sheet's source IDs point to another workbook (owner decision, 21 Nov 2026)."""
    written = 0
    for raw in _raw_rows("sheet/ranking.csv"):
        row = {
            "name": raw["Name"],
            "rank_no": int(raw["Rank"]),
            "area": raw["Area"],
            "domain": raw["Domain"],
            "size_score": int(raw["Size (1-5)"]),
            "complexity_score": int(raw["Complexity (1-5)"]),
            "score": int(raw["Score (size + complexity)"]),
            "basis": raw["Basis for scores"],
            "scoring_confidence": raw["Scoring confidence (H/M/L)"],
            "source_url": "",
            "source_type": "curated",
            "published_date": None,
            "evidence_label": "Hypothesis",
        }
        if store.upsert(conn, run_id, "tech_apps", row) != "rejected":
            written += 1
    for raw in _raw_rows("sheet/notes.csv"):
        conn.execute(
            "INSERT OR REPLACE INTO screen_notes (tab, label, text, source_url, source_type, "
            "loaded_at, evidence_label, verification_status) VALUES (?, ?, ?, '', 'curated', ?, "
            "'Fact', 'passed')",
            (APPS_NOTES_TAB, raw["Topic"], raw["Note"], store.now_iso()),
        )
    load_app_list(conn, run_id)
    conn.commit()
    return written


APPS_NOTES_TAB = "Applications list notes"
