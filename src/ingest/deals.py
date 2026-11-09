"""Deal announcements for the Overview screen (tile 2): M&A, licensing and collaborations.

Sources (free): Google News RSS and the GDELT DOC API. A deal counts when the peer company is
the subject of the headline ("Danaher acquires ...", "Repligen licenses ..."). Target names are
not parsed: each deal is stored with its headline and link, and its category comes from
keywords. Deal values are stored only where the source states them (none yet).

Counts build up over time: every refresh adds new deals, and the Google feed returns about 30
items per query, so earlier years may be incomplete at first.
"""

from __future__ import annotations

import re
import sqlite3
import time
from datetime import date, timedelta

import requests

from src.ingest import news, store

# (company_id, name used in searches and matched at the start of headlines)
DEAL_BUYERS: tuple[tuple[str, str], ...] = (
    ("Danaher", "Danaher"),
    ("Thermo Fisher", "Thermo Fisher"),
    ("Sartorius", "Sartorius"),
    ("Repligen", "Repligen"),
    ("Avantor", "Avantor"),
    ("Merck KGaA", "Merck KGaA"),  # group, as the other buyers; headlines must start with it
)
GOOGLE_QUERIES: tuple[str, ...] = (
    "{name} acquires when:5y",
    "{name} to acquire when:5y",
    "{name} licenses when:5y",
    "{name} collaboration when:5y",
)
GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
GDELT_QUERY = '"{name}" AND (acquires OR acquisition OR licensing OR collaboration OR partnership)'
GDELT_PAUSE_SECONDS = 6  # GDELT allows one request every five seconds
TIMEOUT_SECONDS = 30

# First matching category wins; checked in this order.
CATEGORY_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("M&A", ("acquir", "acquisition", "to buy", "buys ", "agrees to buy", "merger", "takeover")),
    ("Licensing", ("licens", "licence")),
    ("Collaboration", ("collaborat", "partnership", "partners with", "alliance")),
)
_GENERIC = {"business", "company", "group", "corporation", "limited", "agreement", "announces"}


class DealError(RuntimeError):
    """Raised when a deal source cannot be read. The loader skips that source and continues."""


def categorize(headline: str) -> str | None:
    text = headline.lower()
    for category, keywords in CATEGORY_KEYWORDS:
        if any(keyword in text for keyword in keywords):
            return category
    return None


def is_subject(headline: str, name: str) -> bool:
    """True if the headline starts with the company name, i.e. the company is the subject."""
    head = headline.strip().lower()
    prefix = name.lower()
    return head.startswith(prefix) and (len(head) == len(prefix) or head[len(prefix)].isspace())


def distinctive_words(headline: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]+", headline.lower()) if len(w) >= 5 and w not in _GENERIC}


def is_duplicate(
    conn: sqlite3.Connection, acquirer: str, category: str, headline: str, day: str
) -> bool:
    """True if a stored deal of the same category, within 3 days, shares two distinctive words."""
    center = date.fromisoformat(day)
    rows = conn.execute(
        "SELECT headline FROM deal WHERE acquirer = ? AND category = ? "
        "AND announced_date BETWEEN ? AND ?",
        (
            acquirer,
            category,
            (center - timedelta(days=3)).isoformat(),
            (center + timedelta(days=3)).isoformat(),
        ),
    ).fetchall()
    words = distinctive_words(headline)
    return any(len(words & distinctive_words(r["headline"])) >= 2 for r in rows)


def fetch_gdelt(name: str) -> list[dict]:
    """Articles mentioning the company with deal terms, from GDELT (last five years)."""
    time.sleep(GDELT_PAUSE_SECONDS)
    params = {
        "query": GDELT_QUERY.format(name=name),
        "mode": "artlist",
        "maxrecords": 50,
        "format": "json",
        "timespan": "5y",
        "sort": "DateDesc",
    }
    try:
        response = requests.get(
            GDELT_URL,
            params=params,
            timeout=TIMEOUT_SECONDS,
            headers={"User-Agent": news.USER_AGENT},
        )
    except requests.RequestException as exc:
        raise DealError(f"GDELT request failed for '{name}': {exc}") from exc
    if response.status_code != 200:
        raise DealError(f"GDELT returned HTTP {response.status_code} for '{name}'")
    try:
        articles = response.json().get("articles", [])
    except ValueError as exc:
        raise DealError(f"GDELT response for '{name}' is not JSON") from exc
    return [
        {
            "title": a.get("title", "").strip(),
            "link": a.get("url", "").strip(),
            "published": f"{a['seendate'][:4]}-{a['seendate'][4:6]}-{a['seendate'][6:8]}",
        }
        for a in articles
        if a.get("seendate") and a.get("url")
    ]


def _candidates(name: str) -> list[dict]:
    """Google News results for each query, then GDELT. Each source that fails is skipped."""
    items: list[dict] = []
    for template in GOOGLE_QUERIES:
        try:
            items += news.parse_feed(news.fetch_feed(template.format(name=name)))
        except news.NewsError:
            continue
    try:
        items += fetch_gdelt(name)
    except DealError:
        pass
    return items


def load_deals(conn: sqlite3.Connection, run_id: int) -> int:
    """Store deal announcements for each buyer. Returns rows written."""
    written = 0
    seen: set[str] = set()
    for company_id, name in DEAL_BUYERS:
        for item in _candidates(name):
            if item["link"] in seen or not item["published"] or not item["title"]:
                continue
            seen.add(item["link"])
            if not is_subject(item["title"], name):
                continue
            category = categorize(item["title"])
            if category is None:
                continue
            if is_duplicate(conn, company_id, category, item["title"], item["published"]):
                continue
            row = {
                "acquirer": company_id,
                "announced_date": item["published"],
                "category": category,
                "headline": item["title"],
                "value_usd": None,
                "status": "announced",
                "source_url": item["link"],
                "source_type": "news",
                "published_date": item["published"],
                "evidence_label": "Signal",
            }
            if store.upsert(conn, run_id, "deal", row) != "rejected":
                written += 1
    return written
