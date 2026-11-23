"""Report-only checks for AI-populated values (refactor audit B-05 quote check, B-06 YoY range).

Reads data/app.db (read only) and writes docs/check-report.md. Nothing is enforced: no row is
changed, hidden or marked unverified. The report lists the rows that would fail each check and
the status each would move to, so the owner can decide before any check is turned on
(refactor audit decision 11).

Run: uv run python -m scripts.report_checks
"""

from __future__ import annotations

import os
import re
import sqlite3
from pathlib import Path

from src.ingest.checks import check_quote, check_range, check_yoy_change

REPO_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.environ.get("APP_DB_PATH", REPO_ROOT / "data" / "app.db"))
OUT = REPO_ROOT / "docs" / "check-report.md"

# (table, value column, quote column): the number shown must appear in its quote.
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

# Tables with a number but no quote column: they cannot pass the quote check until one exists.
NO_QUOTE_COLUMN = [
    ("cn_financial", "revenue_rmb_m"),
    ("ov_financial", "revenue_local_m"),
    ("revenue_observation", "value"),
]

# Reported year-on-year growth columns: flag |growth| above 50% (CLAUDE.md, AI-populated data 3).
GROWTH_COLUMNS = [
    ("cn_financial", "revenue_yoy_pct"),
    ("ov_financial", "growth_reported_pct"),
    ("ov_financial", "organic_growth_pct"),
]
YOY_LIMIT_PCT = 50.0


def number_text(value) -> str:
    """The number as a source would write it: 524.0 becomes 524."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def quote_findings(conn: sqlite3.Connection) -> list[dict]:
    rows = []
    for table, value_col, quote_col in QUOTE_PAIRS:
        for row in conn.execute(
            f"SELECT rowid, {value_col} AS v, {quote_col} AS q, "
            f"verification_status AS s FROM {table}"
        ):
            if row["v"] is None:
                continue
            problems = check_quote(number_text(row["v"]), row["q"])
            if problems:
                rows.append(
                    _finding("B-05 quote", table, row, number_text(row["v"]), row["q"], problems)
                )
    return rows


def growth_findings(conn: sqlite3.Connection) -> list[dict]:
    rows = []
    for table, col in GROWTH_COLUMNS:
        for row in conn.execute(f"SELECT rowid, {col} AS v, verification_status AS s FROM {table}"):
            if row["v"] is None:
                continue
            problems = check_range(f"{table}.{col}", row["v"], -YOY_LIMIT_PCT, YOY_LIMIT_PCT)
            if problems:
                rows.append(_finding("B-06 growth", table, row, f"{row['v']}%", None, problems))
    rows += revenue_yoy_findings(conn)
    return rows


def revenue_yoy_findings(conn: sqlite3.Connection) -> list[dict]:
    """Compare each revenue figure with the same metric one fiscal year earlier."""
    rows = []
    cols = "rowid, company_id, metric, fiscal_period, value, verification_status AS s"
    for row in conn.execute(f"SELECT {cols} FROM revenue_observation"):
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
            name, row["value"], prior["value"], threshold=YOY_LIMIT_PCT / 100
        )
        if problems:
            rows.append(
                _finding(
                    "B-06 YoY",
                    "revenue_observation",
                    row,
                    number_text(row["value"]),
                    None,
                    problems,
                )
            )
    return rows


def _finding(
    check: str, table: str, row, value: str, quote: str | None, problems: list[str]
) -> dict:
    status = row["s"]
    return {
        "check": check,
        "table": table,
        "rowid": row["rowid"],
        "value": value,
        "quote": (quote or "")[:140],
        "problem": "; ".join(problems),
        "status": status or "",
        "change": f"{status or 'unset'} -> unverified"
        if status != "unverified"
        else "already unverified",
    }


def write_report(findings: list[dict], path: Path) -> None:
    lines = [
        "# Check report: quote (B-05) and YoY (B-06), report only",
        "",
        "Nothing here is enforced. Each row is a value that would **fail** the check if run",
        "on load. Note: the quote check compares the value with its evidence column, which in some "
        "tables is a note rather than a verbatim quote, so some failures are column mismatches.",
        "and the status it would move to. The owner decides whether to turn checks on",
        "(refactor audit decision 11). Generated by `scripts/report_checks.py` from `data/app.db`.",
        "",
        "## Not checked",
        "",
        "These tables have numbers but no quote column, so the quote check cannot run on them yet:",
        "",
    ]
    lines += [f"- `{t}.{c}`" for t, c in NO_QUOTE_COLUMN]
    lines += ["", "## Counts", "", "| Check | Rows that would fail |", "| --- | ---: |"]
    for check in ("B-05 quote", "B-06 growth", "B-06 YoY"):
        n = sum(1 for f in findings if f["check"] == check)
        lines.append(f"| {check} | {n} |")
    lines += [
        "",
        "## Rows",
        "",
        "| Check | Table | rowid | Value | Problem | Quote (first 140 characters) | Change |",
        "| --- | --- | ---: | --- | --- | --- | --- |",
    ]
    for f in findings:
        quote = f["quote"].replace("|", "/") or "(none stored)"
        lines.append(
            f"| {f['check']} | `{f['table']}` | {f['rowid']} | {f['value']} | {f['problem']} | "
            f"{quote} | {f['change']} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    conn = sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    findings = quote_findings(conn) + growth_findings(conn)
    conn.close()
    write_report(findings, OUT)
    for check in ("B-05 quote", "B-06 growth", "B-06 YoY"):
        print(check, sum(1 for f in findings if f["check"] == check))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
