"""Report-only quote check (refactor audit B-05) and the growth report (B-06).

Reads data/app.db (read only) and writes docs/check-report.md. Nothing here changes a row. The
growth check (B-06) is enforced in the refresh (src/ingest/checks.py, apply_growth_checks); this
report repeats it so the owner can see the same list.

Quote check rules (owner decision, 23 Nov 2026):
  (a) it runs only where the evidence cell is a verbatim quote (it contains quote marks);
  (b) separators, units (bn, m, L), currency symbols and rounding are normalised: a stored value
      matches when a number in the quote equals it, rounded to the quote's own decimal places,
      after converting between m and bn;
  (c) evidence that says Calculation, Sum, Derived or Same as is a derived figure: basis
      Derived, quote check skipped;
  (d) a row with no evidence text is a data gap, not a failure.
Anything else (evidence with no quote marks) is not checked and is listed as such.

Run: uv run python -m scripts.report_checks
"""

from __future__ import annotations

import os
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from src.ingest.checks import growth_problems

REPO_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.environ.get("APP_DB_PATH", REPO_ROOT / "data" / "app.db"))
OUT = REPO_ROOT / "docs" / "check-report.md"

# (table, value column, evidence column): the number shown must appear in its quote.
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


def _table(header: list[str], rows: list[list[str]]) -> list[str]:
    out = ["| " + " | ".join(header) + " |", "| " + " | ".join("---" for _ in header) + " |"]
    out += ["| " + " | ".join(r) + " |" for r in rows]
    return out


def write_report(quote_rows: list[dict], growth: list[dict], path: Path) -> None:
    def of(status: str) -> list[dict]:
        return [r for r in quote_rows if r["status"] == status]

    lines = [
        "# Check report: quote (B-05) and growth (B-06)",
        "",
        "Generated by `scripts/report_checks.py` from `data/app.db` (read only).",
        "",
        "- **B-06 growth** is enforced in the refresh: a failing row is stored as unverified and "
        "the change is logged.",
        "- **B-05 quote** is report only. It is not enforced; decision 11 is pending.",
        "",
        "## Quote check rules",
        "",
        "(a) runs only where the evidence cell has quote marks; (b) normalises separators, units "
        "(bn, m), currency symbols and rounding to the quote's decimal places; (c) evidence with "
        "Calculation, Sum, Derived or Same as is basis Derived and skipped; (d) no evidence text "
        "is a data gap.",
        "",
        "## Counts",
        "",
    ]
    lines += _table(
        ["Result", "Rows"],
        [
            ["Would fail (value not in the quote)", str(len(of("fail")))],
            ["Data gap (no evidence text)", str(len(of("gap")))],
            ["Basis Derived (skipped)", str(len(of("derived")))],
            ["Not a verbatim quote (not checked)", str(len(of("not verbatim")))],
            ["B-06 growth above 50% (enforced in refresh)", str(len(growth))],
        ],
    )
    lines += ["", "## Rows that would fail", ""]
    lines += _table(
        ["Table", "rowid", "Value", "Problem", "Evidence (first 140 characters)"],
        [
            [
                f"`{r['table']}`",
                str(r["rowid"]),
                r["value"],
                r["problem"],
                r["evidence"].replace("|", "/"),
            ]
            for r in of("fail")
        ]
        or [["none", "", "", "", ""]],
    )
    lines += ["", "## Data gaps (no evidence text)", ""]
    lines += _table(
        ["Table", "rowid", "Value"],
        [[f"`{r['table']}`", str(r["rowid"]), r["value"]] for r in of("gap")] or [["none", "", ""]],
    )
    lines += ["", "## Not checked: evidence has no quote marks", ""]
    lines += _table(
        ["Table", "rowid", "Value"],
        [[f"`{r['table']}`", str(r["rowid"]), r["value"]] for r in of("not verbatim")]
        or [["none", "", ""]],
    )
    lines += ["", "## Derived (skipped)", ""]
    lines += _table(
        ["Table", "rowid", "Value", "Evidence"],
        [
            [f"`{r['table']}`", str(r["rowid"]), r["value"], r["evidence"].replace("|", "/")]
            for r in of("derived")
        ]
        or [["none", "", "", ""]],
    )
    lines += ["", "## Growth above 50% (B-06)", ""]
    lines += _table(
        ["Table", "rowid", "Problem"],
        [[f"`{g['table']}`", str(g["rowid"]), "; ".join(g["problems"])] for g in growth]
        or [["none", "", ""]],
    )
    lines += [
        "",
        "## Numeric tables without a quote column",
        "",
        "The quote check cannot run on these yet: `cn_financial.revenue_rmb_m`, "
        "`ov_financial.revenue_local_m`, `revenue_observation.value`.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    conn = sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    quote_rows = quote_findings(conn)
    growth = growth_problems(conn)
    conn.close()
    write_report(quote_rows, growth, OUT)
    tally: dict[str, int] = {}
    for r in quote_rows:
        tally[r["status"]] = tally.get(r["status"], 0) + 1
    print("quote", tally, "growth", len(growth))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
