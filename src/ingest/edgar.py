"""SEC EDGAR XBRL company facts loader (US filers).

Run a single-company access check from the repo root:

    uv run python -m src.ingest.edgar --ticker DHR
"""

import argparse
import json
import sys

import requests

from src.ingest.config import edgar_user_agent

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
TIMEOUT_SECONDS = 30


class EdgarError(RuntimeError):
    """Raised when EDGAR cannot be reached or returns unexpected data."""


def _headers() -> dict[str, str]:
    return {"User-Agent": edgar_user_agent(), "Accept-Encoding": "gzip, deflate"}


def cik_for_ticker(ticker: str) -> int:
    """Look up the CIK for a ticker in SEC's public ticker list."""
    response = requests.get(TICKERS_URL, headers=_headers(), timeout=TIMEOUT_SECONDS)
    if response.status_code != 200:
        raise EdgarError(f"Ticker lookup failed: HTTP {response.status_code}")
    wanted = ticker.upper()
    for entry in response.json().values():
        if entry["ticker"].upper() == wanted:
            return int(entry["cik_str"])
    raise EdgarError(f"Ticker {wanted} not found in SEC ticker list")


def fetch_company_facts(cik: int) -> dict:
    """Fetch the XBRL company facts JSON for one CIK."""
    response = requests.get(FACTS_URL.format(cik=cik), headers=_headers(), timeout=TIMEOUT_SECONDS)
    if response.status_code != 200:
        raise EdgarError(f"Company facts failed for CIK {cik}: HTTP {response.status_code}")
    return response.json()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check EDGAR access for one company.")
    parser.add_argument("--ticker", default="DHR", help="US ticker to check (default: DHR)")
    args = parser.parse_args(argv)
    try:
        cik = cik_for_ticker(args.ticker)
        facts = fetch_company_facts(cik)
    except (EdgarError, requests.RequestException) as exc:
        print(f"EDGAR check failed: {exc}", file=sys.stderr)
        return 1
    us_gaap = facts.get("facts", {}).get("us-gaap", {})
    print(
        json.dumps(
            {
                "ticker": args.ticker.upper(),
                "cik": cik,
                "entity_name": facts.get("entityName"),
                "us_gaap_concepts": len(us_gaap),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
