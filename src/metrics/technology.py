"""Technology estate (Screen 5): the figures and rules behind the five tiles.

Every value comes from a stored row with its sources. Dates and the 30-day window are computed
from `today`, so the screen never shows a stale status. Confidence: H > M > L; a row's confidence
is the lower of its component confidences. Rows with confidence L are hidden unless the reader
turns on "Show unconfirmed (L)".
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass, field
from datetime import date, timedelta

RANK = {"H": 2, "M": 1, "L": 0}
WINDOW_DAYS = 30
PRODUCT_MATCH = {"Exact": 2, "Vendor": 1}
TYPE_SCORE = {
    "Exploited": 3,
    "Vendor breach": 3,
    "Critical patch": 2,
    "Outage": 2,
    "Supply-chain breach": 2,
    "Customer-side exposure": 1,
}
ESTATE_SCORE = {"H": 2, "M": 1, "L": 0}
LEVEL_ORDER = {"Strong": 0, "Emerging": 1, "Early": 2, "No public signal": 3}
PENDING_EMPTY = "No corroborated exposures at watchlist vendors in the last 30 days"


def _rows(conn: sqlite3.Connection, sql: str) -> list[dict]:
    cur = conn.execute(sql)
    names = [d[0] for d in cur.description]
    return [dict(zip(names, row, strict=True)) for row in cur.fetchall()]


@dataclass
class TechData:
    eos: list[dict] = field(default_factory=list)
    incidents: list[dict] = field(default_factory=list)
    watchlist: list[dict] = field(default_factory=list)
    integrations: list[dict] = field(default_factory=list)
    adoption: list[dict] = field(default_factory=list)
    gartner: list[dict] = field(default_factory=list)
    implications: list[dict] = field(default_factory=list)
    estate_evidence: list[dict] = field(default_factory=list)
    sources: dict[str, dict] = field(default_factory=dict)
    row_sources: dict[tuple[str, str], list[str]] = field(default_factory=dict)
    notes: list[dict] = field(default_factory=list)
    apps: list[dict] = field(default_factory=list)


def load(conn: sqlite3.Connection) -> TechData | None:
    """All screen 5 data, or None when the tables are not loaded yet."""
    try:
        data = TechData(
            eos=_rows(conn, "SELECT * FROM tech_eos ORDER BY id"),
            incidents=_rows(conn, "SELECT * FROM tech_incidents ORDER BY id"),
            watchlist=_rows(conn, "SELECT * FROM tech_watchlist ORDER BY watch_id"),
            integrations=_rows(conn, "SELECT * FROM tech_integrations ORDER BY id"),
            adoption=_rows(conn, "SELECT * FROM tech_adoption ORDER BY id"),
            gartner=_rows(conn, "SELECT * FROM tech_gartner ORDER BY id"),
            implications=_rows(conn, "SELECT * FROM tech_implications ORDER BY id"),
            estate_evidence=_rows(conn, "SELECT * FROM tech_estate_evidence ORDER BY id"),
            notes=_rows(conn, "SELECT * FROM screen_notes"),
        )
        data.sources = {r["id"]: r for r in _rows(conn, "SELECT * FROM tech_sources")}
        for r in _rows(conn, "SELECT row_type, row_id, source_id FROM tech_row_sources"):
            data.row_sources.setdefault((r["row_type"], r["row_id"]), []).append(r["source_id"])
        try:
            data.apps = _rows(conn, "SELECT * FROM tech_apps ORDER BY rank_no, name")
        except sqlite3.OperationalError:
            data.apps = []
    except sqlite3.OperationalError:
        return None
    if not data.eos and not data.incidents:
        return None
    return data


def window(today: date) -> tuple[date, date]:
    return today - timedelta(days=WINDOW_DAYS), today


def window_label(today: date) -> str:
    start, end = window(today)
    return f"{start.day} {start:%b} – {end.day} {end:%b %Y} · rolling window"


def min_conf(*levels: str | None) -> str:
    known = [lv for lv in levels if lv in RANK]
    if not known:
        return "L"
    return min(known, key=lambda lv: RANK[lv])


def parse_iso(text: str | None) -> date | None:
    if text and re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return date.fromisoformat(text)
    return None


# --- Tile 1: end of support ----------------------------------------------------------------


def eos_status(row: dict, today: date) -> tuple[str, str]:
    """(colour, text) for the milestone date against today: red passed, amber within 12 months,
    green more than 12 months or a floor, grey no date."""
    value = parse_iso(row.get("date_value"))
    if value is None:
        if row.get("is_floor") and row.get("date_value") is None:
            return "green", row.get("milestone_date_text") or ""
        return "grey", row.get("milestone_date_text") or "no date"
    if row.get("is_floor"):
        return "green", f"≥ {value.year}"
    if value < today:
        return "red", f"Ended {row['milestone_date_text']}"
    if value <= today + timedelta(days=365):
        return "amber", row["milestone_date_text"]
    return "green", row["milestone_date_text"]


EOS_ORDER = {"red": 0, "amber": 1, "green": 2, "grey": 3}


def eos_rows(data: TechData, today: date) -> list[dict]:
    """Tile 1 rows: EOS-08 is a note, not a row. Every row is shown; confidence is a label."""
    out = []
    for r in data.eos:
        if r["id"] == "EOS-08":
            continue
        conf = min_conf(r["estate_confidence"], r["date_confidence"])
        colour, text = eos_status(r, today)
        out.append({**r, "confidence": conf, "colour": colour, "status_text": text})
    out.sort(key=lambda x: (EOS_ORDER[x["colour"]], x["date_value"] or "9999"))
    return out


def eos_tile_rows(data: TechData, today: date) -> list[dict]:
    """Tile 1 rows: only rows with "Show on tile" = Yes (sheet column M). Other rows stay in the
    database and the applications ranking, never on the tile."""
    return [r for r in eos_rows(data, today) if str(r.get("show_on_tile") or "").startswith("Yes")]


def eos_note(data: TechData) -> str | None:
    """One line under the table from EOS-08 (the S/4HANA target, not an end-of-support item)."""
    return next((r["next_milestone"] for r in data.eos if r["id"] == "EOS-08"), None)


def gartner_release(data: TechData) -> str:
    """Release date of the Gartner list, as the sheet gives it (for the footnote)."""
    raw = next((g["release_date"] for g in data.gartner if g.get("release_date")), None)
    if not raw:
        return "release date to collect"
    d = parse_iso(raw)
    return f"{d.day} {d:%b %Y}" if d else raw


# --- Tile 2: exposure at vendors we use, last 30 days --------------------------------------


def _estate_confidence(data: TechData, watch_id: str) -> str:
    w = next((r for r in data.watchlist if r["watch_id"] == watch_id), None)
    return w["estate_confidence"] if w else "L"


def incident_score(data: TechData, row: dict) -> dict:
    estate = _estate_confidence(data, row["watchlist_id"])
    product = PRODUCT_MATCH.get(row["product_match"], 0)
    kind = TYPE_SCORE.get(row["type_for_score"], 0)
    estate_points = ESTATE_SCORE.get(estate, 0)
    total = product + kind + estate_points
    return {
        "estate": estate,
        "product": product,
        "type": kind,
        "estate_points": estate_points,
        "total": total,
    }


def relevance_label(score: int) -> tuple[str, str]:
    if score >= 6:
        return "High", "red"
    if score >= 4:
        return "Medium", "amber"
    return "Low", "grey"


def exposure(data: TechData, today: date) -> dict:
    """Tile 2. Shows in-window, corroborated incidents at watchlist vendors (max 6); counts the
    in-window rows awaiting confirmation. REF rows never show here."""
    start, end = window(today)
    watched = {r["watch_id"] for r in data.watchlist}
    shown, pending = [], []
    for r in data.incidents:
        if r.get("row_kind") == "reference":
            continue
        when = parse_iso(r["date_value"])
        if when is None or not (start <= when <= end):
            continue
        if r["watchlist_id"] not in watched:
            continue
        corroborated = int(r["tier_a_count"] or 0) >= 1 or int(r["tier_b_count"] or 0) >= 2
        score = incident_score(data, r)
        label, colour = relevance_label(score["total"])
        item = {
            **r,
            "days_old": (today - when).days,
            "score": score,
            "relevance": label,
            "relevance_colour": colour,
            "estate_confidence": score["estate"],
        }
        (shown if corroborated else pending).append(item)
    shown.sort(key=lambda x: (-x["score"]["total"], x["date_value"]), reverse=False)
    shown.sort(key=lambda x: (x["score"]["total"], x["date_value"]), reverse=True)
    return {"shown": shown, "pending": pending, "window": window_label(today)}


# --- Tile 3: integration readiness ---------------------------------------------------------

GROUPS = (
    ("API and event-ready", "api", "API and event-ready"),
    ("Mixed", "mixed", "Mixed: APIs plus batch files"),
    ("Legacy", "legacy", "Legacy or limited"),
)


def integration_groups(data: TechData) -> list[dict]:
    out = []
    for prefix, key, title in GROUPS:
        members = []
        for r in data.integrations:
            if not (r["readiness_group"] or "").startswith(prefix):
                continue
            conf = min_conf(r["estate_confidence"], r["capability_confidence"])
            members.append({**r, "confidence": conf})
        out.append({"key": key, "title": title, "members": members})
    return out


# --- Tile 4: adoption signals --------------------------------------------------------------


def adoption_rows(data: TechData) -> list[dict]:
    rows = []
    for r in data.adoption:
        if not r["id"].startswith("ADO"):
            continue
        rows.append(r)
    rows.sort(key=lambda r: (LEVEL_ORDER.get(r["level"], 9), r["id"]))
    return rows


def gartner_rows(data: TechData) -> list[dict]:
    by_id = {r["id"]: r for r in data.adoption}
    out = []
    for g in data.gartner:
        linked = re.findall(r"ADO-\d+", g["cytiva_danaher_signal"] or "")
        names = [
            {"id": a, "technology": by_id[a]["technology"], "level": by_id[a]["level"]}
            for a in linked
            if a in by_id
        ]
        out.append({**g, "linked": names, "none": not names})
    return out


# --- Tile 5: implications ------------------------------------------------------------------


def implication_rows(data: TechData) -> list[dict]:
    return list(data.implications)


# --- Evidence drawer -----------------------------------------------------------------------

_QUOTE_FIELDS = (
    "vendor_date_quote",
    "evidence_quote",
    "evidence",
    "vendor_interface_evidence",
    "evidence_quote",
)


def evidence_text(row: dict) -> str:
    for f in _QUOTE_FIELDS:
        if row.get(f):
            return row[f]
    return ""


def sources_for(data: TechData, row_type: str, row_id: str) -> list[dict]:
    return [
        data.sources[s] for s in data.row_sources.get((row_type, row_id), []) if s in data.sources
    ]


def estate_for(data: TechData, ids: list[str]) -> list[dict]:
    return [e for e in data.estate_evidence if e["id"] in ids]


def based_on(data: TechData, ids_text: str | None) -> list[str]:
    return re.findall(r"(?:EOS|INC|REF|INT|ADO|EST)-\d+", ids_text or "")
