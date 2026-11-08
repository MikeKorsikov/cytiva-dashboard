"""Annual financials for IFRS peers, read from their published annual report PDFs (CD-3).

Sartorius (EUR) and Getinge (SEK) do not file XBRL with the SEC, so the figures come from the
report itself. Each report is pinned by URL and page number. The loader reads the income
statement and the cash-flow statement, takes the two most recent years from each table, and
stores the values in local currency with the USD equivalent at that year's average rate.

Each value is read from the cited page text, so it appears there by construction. The
gross-profit-within-revenue check runs on every stored year.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import requests

from src.ingest import store
from src.ingest.checks import check_segment_within_group
from src.ingest.prices import fetch_history

REPO_ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = REPO_ROOT / "data" / "cache" / "reports"
TIMEOUT_SECONDS = 120
NUMBER = re.compile(r"[-–]?\d{1,3}(?:,\d{3})+(?:\.\d+)?|[-–]?\d+(?:\.\d+)?")


class ReportError(RuntimeError):
    """Raised when a report cannot be downloaded, or a figure is not found on its page."""


@dataclass(frozen=True)
class Report:
    company_id: str
    name: str
    country: str
    currency: str  # ISO code of the reporting currency
    fiscal_year: int  # latest year in the report
    url: str
    income_page: int  # 1-based PDF page of the income statement
    cash_flow_page: int  # 1-based PDF page of the cash-flow statement
    level: str = "group"  # "group" or "segment"


# Each row label must match the report's own wording on the cited page.
INCOME_LABELS = {
    "revenue": {
        "Sartorius": "Sales revenue",
        "Getinge": "Net sales",
        "Merck Life Science": "Net sales",
    },
    "gross_profit": {
        "Sartorius": "Gross profit on sales",
        "Getinge": "Gross profit",
        "Merck Life Science": "Gross profit",
    },
    "net_income": {
        "Sartorius": "Equity holders of Sartorius AG",
        "Getinge": "Parent Company's shareholders",
    },
}
CASH_LABELS = {
    "operating_cash_flow": {
        "Sartorius": "Cash flow from operating activities",
        "Getinge": "Cash flow from operating activities",
    },
    "capex": {
        "Sartorius": "Investments in intangible and tangible assets",
        "Getinge": "Investments in intangible assets and tangible assets",
    },
}

# Where a table has extra columns (adjustments), the positions of the latest and prior IFRS
# values on the line, counted from the first number. Other reports use the last two numbers.
POSITIONS: dict[str, dict[str, tuple[int, int]]] = {
    "Merck Life Science": {"revenue": (0, 2), "gross_profit": (0, 3)},
}

REPORTS: tuple[Report, ...] = (
    Report(
        company_id="Sartorius",
        name="Sartorius",
        country="DE",
        currency="EUR",
        fiscal_year=2025,
        url="https://www.sartorius.com/download/1796536/fy-2025-download-annual-report-sag-en-data.pdf",
        income_page=266,
        cash_flow_page=269,
    ),
    Report(
        company_id="Merck Life Science",
        name="Merck Life Science",
        country="DE",
        currency="EUR",
        fiscal_year=2025,
        url="https://reports.emdgroup.com/en/annualreport/2025/_assets/downloads/lsc-life-science-emd-ar25.pdf",
        income_page=3,  # reconciliation table with IFRS and adjusted columns
        cash_flow_page=3,  # segment reports no cash flow; this page is read for nothing else
        level="segment",
    ),
)


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace(" ", " ")).strip()


def values_on_line(
    page_text: str, label: str, positions: tuple[int, int] | None = None
) -> tuple[float, float]:
    """Latest and prior year values on the line that contains `label` (note numbers ignored).

    Only that line is read. By default the two last numbers are the year columns, latest first.
    `positions` picks them by index from the first number, for tables with extra columns.
    """
    for raw_line in page_text.splitlines():
        line = _normalise(raw_line)
        index = line.find(label)
        if index < 0:
            continue
        tokens = [t.replace("–", "-") for t in NUMBER.findall(line[index + len(label) :])]
        if positions is None:
            if len(tokens) < 2:
                raise ReportError(f"Row '{label}' has fewer than two values")
            latest, prior = tokens[-2], tokens[-1]
        else:
            if len(tokens) <= max(positions):
                raise ReportError(f"Row '{label}' has too few values for the cited columns")
            latest, prior = tokens[positions[0]], tokens[positions[1]]
        return float(latest.replace(",", "")), float(prior.replace(",", ""))
    raise ReportError(f"Row '{label}' not found on the cited page")


def fx_by_year(currency: str) -> dict[int, float]:
    """Average USD value of one unit of `currency`, by calendar year (from daily closes)."""
    if currency == "USD":
        return {}
    history = fetch_history(f"{currency}USD=X", period="2y")
    closes = history["Close"].copy()
    closes.index = pd.to_datetime(closes.index).tz_localize(None)
    return {
        int(year): float(value) for year, value in closes.groupby(closes.index.year).mean().items()
    }


def pdf_pages(report: Report) -> dict[int, str]:
    """Text of the two cited pages, from the cached PDF (downloaded once per report URL)."""
    from pypdf import PdfReader

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / f"{report.company_id}-FY{report.fiscal_year}.pdf"
    if not cache_file.exists():
        try:
            response = requests.get(
                report.url, timeout=TIMEOUT_SECONDS, headers={"User-Agent": "cytiva-dashboard/0.1"}
            )
        except requests.RequestException as exc:
            raise ReportError(f"Annual report download failed for {report.name}: {exc}") from exc
        if response.status_code != 200:
            raise ReportError(
                f"Annual report for {report.name} returned HTTP {response.status_code}"
            )
        cache_file.write_bytes(response.content)
    reader = PdfReader(str(cache_file))
    pages = {}
    for number in (report.income_page, report.cash_flow_page):
        pages[number] = reader.pages[number - 1].extract_text() or ""
    return pages


def load_annual_reports(conn: sqlite3.Connection, run_id: int) -> int:
    """Load income and cash-flow metrics for each IFRS report. Returns rows written."""
    written = 0
    for report in REPORTS:
        company_row = {
            "company_id": report.company_id,
            "name": report.name,
            "ticker": None,
            "country": report.country,
            "reporting_standard": "IFRS",
            "fiscal_year_end": "12-31",
            "group_or_segment": report.level,
            "source_url": report.url,
            "source_type": "document",
            "published_date": None,
            "evidence_label": "Fact",
        }
        store.upsert(conn, run_id, "company", company_row)

        pages = pdf_pages(report)
        income_text = pages[report.income_page]
        cash_text = pages[report.cash_flow_page]
        fx = fx_by_year(report.currency)

        positions = POSITIONS.get(report.company_id, {})
        values: dict[str, tuple[float, float]] = {}
        for metric, labels in INCOME_LABELS.items():
            if report.company_id not in labels:
                continue
            values[metric] = values_on_line(
                income_text, labels[report.company_id], positions.get(metric)
            )
        for metric, labels in CASH_LABELS.items():
            if report.company_id not in labels:
                continue  # the segment does not report this line
            pair = values_on_line(cash_text, labels[report.company_id])
            values[metric] = (abs(pair[0]), abs(pair[1]))  # capex is reported as a negative outflow

        revenue_latest = values["revenue"][0]
        for offset in (0, 1):
            year = report.fiscal_year - offset
            rate = fx.get(year)
            for metric, pair in values.items():
                local = pair[offset] * 1_000_000  # reports are in millions
                problems = []
                if metric == "gross_profit" and offset == 0:
                    problems += check_segment_within_group(
                        "gross_profit", local, revenue_latest * 1e6
                    )
                row = {
                    "company_id": report.company_id,
                    "fiscal_year": year,
                    "metric": metric,
                    "value_local": local,
                    "value_usd": local * rate if rate else None,
                    "currency": report.currency,
                    "source_url": report.url,
                    "source_type": "document",
                    "published_date": None,
                    "evidence_label": "Fact",
                }
                if row["value_usd"] is None:
                    problems.append(f"no {report.currency}/USD average rate for {year}")
                status = store.upsert(
                    conn, run_id, "financial_metric", row, extra_problems=problems
                )
                if status != "rejected":
                    written += 1
    return written
