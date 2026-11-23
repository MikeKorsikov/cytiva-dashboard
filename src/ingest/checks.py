"""Automated checks for AI-populated data (CLAUDE.md, "AI-populated data").

A record passes only if every check passes. A record that fails any check is stored
with verification_status "unverified" and its check notes, and is not shown as a fact.
"""

import re
import sqlite3
from dataclasses import dataclass, field

from src.ingest.schema import EVIDENCE_LABELS, SOURCE_TYPES


@dataclass
class CheckResult:
    passed: bool
    notes: list[str] = field(default_factory=list)


def check_source(source_url: str | None, source_type: str, evidence_label: str) -> list[str]:
    """Check 1: every value has a source link, a known source type and an evidence label."""
    problems = []
    if evidence_label != "Hypothesis" and (not source_url or not source_url.startswith("https://")):
        problems.append("missing or non-https source_url")
    if source_type not in SOURCE_TYPES:
        problems.append(f"unknown source_type {source_type!r}")
    if evidence_label not in EVIDENCE_LABELS:
        problems.append(f"unknown evidence_label {evidence_label!r}")
    return problems


def _digits(text: str) -> str:
    return re.sub(r"[^0-9.\-]", "", text)


def check_quote(value: str, source_text: str | None) -> list[str]:
    """Check 2: the extracted figure appears in the source text.

    Commas, spaces and currency symbols are ignored, so "1,234" matches "1234".
    """
    if not source_text:
        return ["no source text available for quote check"]
    wanted = _digits(value)
    if not wanted:
        return []  # non-numeric values are checked by the caller
    if wanted not in _digits(source_text):
        return [f"value {value!r} not found in source text"]
    return []


def check_range(name: str, value: float | None, low: float, high: float) -> list[str]:
    """Check 3a: value lies within a plausible range."""
    if value is None:
        return []
    if not low <= value <= high:
        return [f"{name} {value} outside plausible range [{low}, {high}]"]
    return []


def check_segment_within_group(name: str, segment: float | None, group: float | None) -> list[str]:
    """Check 3b: a segment cannot exceed its group total."""
    if segment is None or group is None:
        return []
    if segment > group:
        return [f"{name}: segment {segment} exceeds group {group}"]
    return []


def check_yoy_change(
    name: str, current: float, previous: float, threshold: float = 0.5
) -> list[str]:
    """Check 3c: flag a year-on-year change above the threshold (50% by default)."""
    if previous == 0:
        return []
    change = abs(current - previous) / abs(previous)
    if change > threshold:
        return [f"{name}: change of {change:.0%} vs previous year needs review"]
    return []


def verdict(problems: list[str]) -> CheckResult:
    """Combine check results. Any problem makes the record unverified."""
    return CheckResult(passed=not problems, notes=problems)


# --- Enforced checks (refresh). A failing row is stored as unverified and moved to confidence L,
# so it is hidden by default and shown with UNCONFIRMED under the screens' toggle (23 Nov 2026).


def _mark_unverified(
    conn: sqlite3.Connection, run_id: int, table: str, rowid: int, notes: str
) -> None:
    from src.ingest import store  # local: store imports this module

    old = conn.execute(
        f"SELECT verification_status, confidence, check_notes FROM {table} WHERE rowid = ?",
        (rowid,),
    ).fetchone()
    conn.execute(
        f"UPDATE {table} SET verification_status = 'unverified', confidence = 'L', "
        "check_notes = ? WHERE rowid = ?",
        (notes, rowid),
    )
    store.log_change(
        conn,
        run_id,
        table,
        {"rowid": rowid},
        "unverified",
        dict(old),
        {"verification_status": "unverified", "confidence": "L", "check_notes": notes},
    )


# Check 3c (B-06): growth above 50% is flagged.
GROWTH_COLUMNS = (
    ("cn_financial", "revenue_yoy_pct"),
    ("ov_financial", "growth_reported_pct"),
    ("ov_financial", "organic_growth_pct"),
)
GROWTH_LIMIT_PCT = 50.0


def _has_table(conn: sqlite3.Connection, name: str) -> bool:
    return (
        conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (name,)
        ).fetchone()
        is not None
    )


def growth_problems(conn: sqlite3.Connection) -> list[dict]:
    """Rows whose reported growth is outside +-50%."""
    found: list[dict] = []
    for table, col in GROWTH_COLUMNS:
        if not _has_table(conn, table):
            continue
        for row in conn.execute(f"SELECT rowid AS rid, {col} AS v FROM {table}"):
            if row["v"] is None:
                continue
            problems = check_range(f"{table}.{col}", row["v"], -GROWTH_LIMIT_PCT, GROWTH_LIMIT_PCT)
            if problems:
                found.append({"table": table, "rowid": row["rid"], "problems": problems})
    return found


def apply_growth_checks(conn: sqlite3.Connection, run_id: int) -> int:
    """Refresh step: mark each failing growth row unverified. Returns the count."""
    flagged = growth_problems(conn)
    for item in flagged:
        _mark_unverified(conn, run_id, item["table"], item["rowid"], "; ".join(item["problems"]))
    return len(flagged)


# Check 2 (B-05): the quote check. Enforced: only the rows that fail are marked unverified. Gaps,
# derived rows and rows without quote marks are not enforced (see docs/check-report.md).
QUOTE_PAIRS = [
    ("s2_biotech_sales", "value_m", "quote"),
    ("s2_market_size", "value_usd_bn", "quote"),
    ("s2_supplier_revenue", "revenue_reported_m", "quote"),
    ("cn_headline", "value_text", "evidence"),
    ("demand_pipeline", "value", "evidence"),
    ("demand_top_drug", "sales_fy2025_usd_bn", "evidence"),
    ("demand_approval", "value", "evidence"),
    ("demand_capacity", "pledge_or_capacity", "evidence"),
    ("market_signal", "value", "evidence"),
    ("cluster_fact", "value", "evidence"),
    ("cdmo_site", "capacity_l", "evidence"),
]

DERIVED_WORDS = re.compile(r"\b(calculation|calculated|sum|derived|same as)\b", re.IGNORECASE)
QUOTE_MARKS = re.compile(r"[\"“”]")
NUMBER = re.compile(
    r"(?<![\d.,])(\d[\d,]*(?:\.\d+)?)\s*(bn|billion|m|million|k|%|L)?", re.IGNORECASE
)
# Scale of the unit word relative to millions: bn and billion are 1000 times m.
BILLION_UNITS = {"bn", "billion"}
MILLION_UNITS = {"m", "million"}


@dataclass(frozen=True)
class QuoteResult:
    status: str  # "pass", "fail", "derived", "not verbatim" or "gap"
    problem: str = ""


def _numbers(text: str) -> list[tuple[float, int, str]]:
    """Every number in the text: (value, decimal places, unit word in lower case)."""
    found = []
    for match in NUMBER.finditer(text):
        raw = match.group(1).replace(",", "")
        decimals = len(raw.split(".")[1]) if "." in raw else 0
        found.append((float(raw), decimals, (match.group(2) or "").lower()))
    return found


def check_quote_text(value: float, evidence: str | None) -> QuoteResult:
    """Classify one stored value against its evidence cell (rules a to d)."""
    if evidence is None or not evidence.strip():
        return QuoteResult("gap", "no evidence text stored")
    if DERIVED_WORDS.search(evidence):
        return QuoteResult("derived", "derived figure (Calculation, Sum, Derived or Same as)")
    if not QUOTE_MARKS.search(evidence):
        return QuoteResult("not verbatim", "evidence has no quote marks, so it is not checked")
    quoted = " ".join(QUOTE_MARKS.split(evidence)[1::2]) or evidence
    for number, decimals, unit in _numbers(quoted):
        # The stored value in the quote's unit: a billion figure is 1000 times the million one.
        if unit in BILLION_UNITS:
            candidates = {value, value / 1000.0}  # the stored value may be in millions
        elif unit in MILLION_UNITS:
            candidates = {value, value * 1000.0}  # the stored value may be in billions
        else:
            candidates = {value}
        if any(round(c, decimals) == round(number, decimals) for c in candidates):
            return QuoteResult("pass")
    return QuoteResult("fail", f"value {value:g} is not in the quote")


def quote_findings(conn: sqlite3.Connection) -> list[dict]:
    """Every row that is not a pass, with its classification."""
    rows = []
    for table, value_col, evidence_col in QUOTE_PAIRS:
        query = f"SELECT rowid AS rid, {value_col} AS v, {evidence_col} AS e FROM {table}"  # noqa: S608
        for row in conn.execute(query):
            raw = row["v"]
            if raw is None:
                continue
            if isinstance(raw, str):  # a text cell: its first number is the value
                numbers = _numbers(raw)
                if not numbers:
                    continue  # no number to check, for example "n/d"
                value, shown = numbers[0][0], raw
            else:
                value, shown = float(raw), f"{raw:g}"
            result = check_quote_text(value, row["e"])
            if result.status == "pass":
                continue
            rows.append(
                {
                    "table": table,
                    "rowid": row["rid"],
                    "value": shown,
                    "evidence": (row["e"] or "")[:140],
                    "status": result.status,
                    "problem": result.problem,
                }
            )
    return rows


def apply_quote_checks(conn: sqlite3.Connection, run_id: int) -> int:
    """Refresh step: mark each row whose value is not in its quote as unverified."""
    failing = [r for r in quote_findings(conn) if r["status"] == "fail"]
    for item in failing:
        _mark_unverified(conn, run_id, item["table"], item["rowid"], item["problem"])
    return len(failing)
