"""Automated checks for AI-populated data (CLAUDE.md, "AI-populated data").

A record passes only if every check passes. A record that fails any check is stored
with verification_status "unverified" and its check notes, and is not shown as a fact.
"""

import re
from dataclasses import dataclass, field

from src.ingest.schema import EVIDENCE_LABELS, SOURCE_TYPES


@dataclass
class CheckResult:
    passed: bool
    notes: list[str] = field(default_factory=list)


def check_source(source_url: str | None, source_type: str, evidence_label: str) -> list[str]:
    """Check 1: every value has a source link, a known source type and an evidence label."""
    problems = []
    if not source_url or not source_url.startswith("https://"):
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
