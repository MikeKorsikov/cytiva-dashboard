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

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data" / "technology"
CONFIDENCE = ("H", "M", "L")
MONTHS = {
    m: i
    for i, m in enumerate(
        ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1
    )
}

# (csv file, table, natural key column, id pattern, source-link column or None)
SPECS = (
    ("eos.csv", "tech_eos", "id", r"EOS-\d+", "source_ids"),
    ("incidents.csv", "tech_incidents", "id", r"(INC|REF)-\d+", "source_ids"),
    ("watchlist.csv", "tech_watchlist", "watch_id", r"W\d+", None),
    ("feeds.csv", "tech_feeds", "feed_id", r"F\d+", None),
    ("integrations.csv", "tech_integrations", "id", r"INT-\d+", "source_ids"),
    ("adoption.csv", "tech_adoption", "id", r"(ADO|G26)-\d+", "source_ids"),
    ("gartner.csv", "tech_gartner", "id", r"G26-\d+", "source_ids"),
    ("implications.csv", "tech_implications", "id", r"IMP-\d+", None),
    ("estate_evidence.csv", "tech_estate_evidence", "id", r"EST-\d+", "source_ids"),
    ("sources.csv", "tech_sources", "id", r"S\d+", None),
)


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


def _rows(name: str) -> list[dict]:
    with (DATA_DIR / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_technology(conn: sqlite3.Connection, run_id: int) -> int:
    """Store the screen 5 rows. Returns the number of rows accepted. Re-runnable: rows are
    upserted by their ID, so a second run changes nothing."""
    sources = {r["id"]: r for r in _rows("sources.csv")}
    evidence = {r["id"]: r for r in _rows("estate_evidence.csv")}
    written = 0
    for filename, table, key, pattern, link_col in SPECS:
        for raw in _rows(filename):
            if not re.fullmatch(pattern, raw[key] or ""):
                continue  # notes, rules and section labels are not data rows
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
    for raw in _rows("screen_notes.csv"):
        conn.execute(
            "INSERT OR REPLACE INTO screen_notes (tab, label, text, source_url, source_type, "
            "loaded_at, evidence_label, verification_status) VALUES (?, ?, ?, '', 'curated', ?, "
            "'Fact', 'passed')",
            (raw["tab"], raw["label"], raw["text"], store.now_iso()),
        )
    load_apps(conn, run_id)
    conn.commit()
    return written


def load_apps(conn: sqlite3.Connection, run_id: int) -> int:
    """Application ranking (size and complexity), from the applications sheet's "Size and
    complexity ranking" tab (data/technology/sheet/ranking.csv). The scores are analyst
    judgements, so they are stored as Hypothesis, with the sheet's scoring confidence and no
    URL: the sheet's source IDs point to another workbook (owner decision, 21 Nov 2026)."""
    written = 0
    for raw in _rows("sheet/ranking.csv"):
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
    for raw in _rows("sheet/notes.csv"):
        conn.execute(
            "INSERT OR REPLACE INTO screen_notes (tab, label, text, source_url, source_type, "
            "loaded_at, evidence_label, verification_status) VALUES (?, ?, ?, '', 'curated', ?, "
            "'Fact', 'passed')",
            (APPS_NOTES_TAB, raw["Topic"], raw["Note"], store.now_iso()),
        )
    conn.commit()
    return written


APPS_NOTES_TAB = "Applications list notes"
