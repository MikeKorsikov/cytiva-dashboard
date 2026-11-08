"""Values from the income statement text of a company's latest 10-K (SEC EDGAR).

Used only where XBRL does not tag a value. Thermo Fisher, for example, does not tag cost of
sales, but the income statement in its 10-K shows the numbers. The loader reads the table
rows, checks the revenue it finds against the XBRL revenue, and stores the derived value with
the 10-K document link. Figures in the 10-K are in millions unless stated otherwise.
"""

from __future__ import annotations

import html
import re

import requests

from src.ingest import edgar

TIMEOUT_SECONDS = 60
NUMBER = r"\(?\d{1,3}(?:,\d{3})*(?:\.\d+)?\)?"

# Income statement rows that make up cost of sales, per ticker (as labelled in the 10-K).
COST_OF_SALES_LABELS: dict[str, tuple[str, ...]] = {
    "TMO": ("Cost of product revenues", "Cost of service revenues"),
}


class TenKError(RuntimeError):
    """Raised when the 10-K cannot be fetched or the expected rows are not found."""


def latest_10k(cik: int) -> dict:
    """Accession number, primary document, filing date and period end of the latest 10-K."""
    try:
        response = requests.get(
            f"https://data.sec.gov/submissions/CIK{cik:010d}.json",
            headers=edgar._headers(),
            timeout=TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        raise TenKError(f"EDGAR submissions request failed for CIK {cik}: {exc}") from exc
    if response.status_code != 200:
        raise TenKError(f"EDGAR submissions for CIK {cik} returned HTTP {response.status_code}")
    recent = response.json()["filings"]["recent"]
    for i, form in enumerate(recent["form"]):
        if form == "10-K":
            return {
                "accession": recent["accessionNumber"][i],
                "primary_document": recent["primaryDocument"][i],
                "filed": recent["filingDate"][i],
                "period_end": recent["reportDate"][i],
            }
    raise TenKError(f"No 10-K found for CIK {cik}")


def document_url(cik: int, filing: dict) -> str:
    folder = filing["accession"].replace("-", "")
    return f"https://www.sec.gov/Archives/edgar/data/{cik}/{folder}/{filing['primary_document']}"


def fetch_text(url: str) -> str:
    """Document as plain text, with tags removed and whitespace collapsed."""
    try:
        response = requests.get(url, headers=edgar._headers(), timeout=TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        raise TenKError(f"10-K request failed: {exc}") from exc
    if response.status_code != 200:
        raise TenKError(f"10-K returned HTTP {response.status_code}")
    text = re.sub(r"<[^>]+>", " ", response.text)
    return html.unescape(re.sub(r"\s+", " ", text))


def row_values(text: str, label: str, count: int = 3) -> list[float]:
    """First `count` numbers after a table row label, in document order (latest year first)."""
    match = re.search(re.escape(label) + r"\s+(" + NUMBER + r"(?:\s+" + NUMBER + r"){0,2})", text)
    if not match:
        raise TenKError(f"Row '{label}' not found in the 10-K income statement")
    values = []
    for token in re.findall(NUMBER, match.group(1))[:count]:
        negative = token.startswith("(")
        number = float(token.strip("()").replace(",", ""))
        values.append(-number if negative else number)
    return values


def cost_of_sales_by_year(text: str, labels: tuple[str, ...], years: list[int]) -> dict[int, float]:
    """Sum of the cost rows, in USD (the 10-K reports millions)."""
    totals = [0.0] * len(years)
    for label in labels:
        values = row_values(text, label, count=len(years))
        for i, value in enumerate(values):
            totals[i] += value
    return {year: total * 1_000_000 for year, total in zip(years, totals, strict=True)}


def revenue_by_year(text: str, years: list[int]) -> dict[int, float]:
    values = row_values(text, "Total revenues", count=len(years))
    return {year: value * 1_000_000 for year, value in zip(years, values, strict=True)}
