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


# Check 3c (B-06): growth above 50% is flagged. Enforced on every refresh: a failing row is
# stored as unverified with its notes, and the change is logged.
GROWTH_COLUMNS = (
    ("cn_financial", "revenue_yoy_pct"),
    ("ov_financial", "growth_reported_pct"),
    ("ov_financial", "organic_growth_pct"),
)
GROWTH_LIMIT_PCT = 50.0


def growth_problems(conn: sqlite3.Connection) -> list[dict]:
    """Rows that fail the growth check: reported growth outside +-50%, or a revenue figure that
    moved more than 50% against the same metric one fiscal year earlier."""
    found: list[dict] = []
    if not _has_table(conn, "revenue_observation"):
        # revenue_observation is a legacy table with no loader in the current schema (see the
        # audit): the YoY part of the check has no rows to read until one is loaded again.
        return _growth_columns(conn, found)
    return _growth_columns(conn, found) + _revenue_yoy(conn)


def _has_table(conn: sqlite3.Connection, name: str) -> bool:
    return (
        conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (name,)
        ).fetchone()
        is not None
    )


def _growth_columns(conn: sqlite3.Connection, found: list[dict]) -> list[dict]:
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


def _revenue_yoy(conn: sqlite3.Connection) -> list[dict]:
    found: list[dict] = []
    for row in conn.execute(
        "SELECT rowid AS rid, company_id, metric, fiscal_period, value FROM revenue_observation"
    ):
        year = re.search(r"(\d{4})", row["fiscal_period"] or "")
        if year is None or row["value"] is None:
            continue
        prior = conn.execute(
            "SELECT value FROM revenue_observation WHERE company_id = ? AND metric = ? "
            "AND fiscal_period LIKE ? AND value IS NOT NULL",
            (row["company_id"], row["metric"], f"%{int(year.group(1)) - 1}%"),
        ).fetchone()
        if prior is None:
            continue
        name = f"revenue_observation {row['company_id']} {row['metric']} {row['fiscal_period']}"
        problems = check_yoy_change(
            name, row["value"], prior["value"], threshold=GROWTH_LIMIT_PCT / 100
        )
        if problems:
            found.append(
                {"table": "revenue_observation", "rowid": row["rid"], "problems": problems}
            )
    return found


def apply_growth_checks(conn: sqlite3.Connection, run_id: int) -> int:
    """Refresh step: store each failing row as unverified, with its notes. Returns the count."""
    from src.ingest import store  # local: store imports this module

    flagged = growth_problems(conn)
    for item in flagged:
        table, rowid = item["table"], item["rowid"]
        old = conn.execute(
            f"SELECT verification_status, check_notes FROM {table} WHERE rowid = ?", (rowid,)
        ).fetchone()
        notes = "; ".join(item["problems"])
        conn.execute(
            f"UPDATE {table} SET verification_status = 'unverified', "
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
            {"verification_status": "unverified", "check_notes": notes},
        )
    return len(flagged)
