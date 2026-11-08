"""News for the Overview screen (CD-3, tile 4), from Google News RSS (free, no key).

Each company has one search feed. Headlines, links, dates and publisher names are stored.
Article text is not stored (paywall rule). Items are tagged Results, M&A, Capacity,
Deal talk or Other from keywords in the headline. Items are deduplicated by link.
"""

from __future__ import annotations

import sqlite3
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus

import requests

from src.ingest import store

FEED_URL = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
TIMEOUT_SECONDS = 30
USER_AGENT = "cytiva-dashboard/0.1"  # generic client name; no personal contact details
ITEMS_PER_COMPANY = 20

# (company_id, search query). Merck Life Science is searched by its Process Solutions name.
NEWS_COMPANIES: tuple[tuple[str, str], ...] = (
    (
        "Danaher",
        '"Danaher Corporation"',
    ),  # quoted full name: avoids unrelated people with the surname
    ("Cytiva", "Cytiva"),
    ("Thermo Fisher", "Thermo Fisher Scientific"),
    ("Sartorius", "Sartorius AG"),
    ("Repligen", "Repligen"),
    ("Avantor", "Avantor"),
    ("Merck Life Science", "MilliporeSigma Process Solutions"),
)

# Tags in priority order: the first tag whose keywords appear in the headline wins.
TAG_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("M&A", ("acquir", "acquisition", "merger", "divest", "to buy", "buys ")),
    (
        "Deal talk",
        ("talks", "considering", "explore sale", "sale of", "activist", "pushes for sale"),
    ),
    (
        "Capacity",
        ("plant", "facility", "capacity", "expansion", "invest in", "invests in", "investment in"),
    ),
    ("Results", ("earnings", "results", "quarter", "revenue", "guidance", "profit")),
)


class NewsError(RuntimeError):
    """Raised when a news feed cannot be fetched or parsed."""


def news_url(query: str) -> str:
    return FEED_URL.format(query=quote_plus(query))


def tag_headline(headline: str) -> str:
    text = headline.lower()
    for tag, keywords in TAG_KEYWORDS:
        if any(keyword in text for keyword in keywords):
            return tag
    return "Other"


def fetch_feed(query: str) -> bytes:
    try:
        response = requests.get(
            news_url(query), timeout=TIMEOUT_SECONDS, headers={"User-Agent": USER_AGENT}
        )
    except requests.RequestException as exc:
        raise NewsError(f"News feed request failed for '{query}': {exc}") from exc
    if response.status_code != 200:
        raise NewsError(f"News feed for '{query}' returned HTTP {response.status_code}")
    return response.content


def parse_feed(xml_bytes: bytes) -> list[dict]:
    """Items from an RSS document: title, link, published date (ISO) and publisher."""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise NewsError(f"News feed is not valid XML: {exc}") from exc
    items = []
    for element in root.findall("./channel/item")[:ITEMS_PER_COMPANY]:
        pub = element.findtext("pubDate")
        published = parsedate_to_datetime(pub).date().isoformat() if pub else None
        items.append(
            {
                "title": (element.findtext("title") or "").strip(),
                "link": (element.findtext("link") or "").strip(),
                "published": published,
                "publisher": (element.findtext("source") or "").strip() or None,
            }
        )
    return items


def load_news(conn: sqlite3.Connection, run_id: int) -> int:
    """Load recent headlines for each company. Returns rows written (not rejected)."""
    written = 0
    seen: set[str] = set()
    for company_id, query in NEWS_COMPANIES:
        for item in parse_feed(fetch_feed(query)):
            if item["link"] in seen:
                continue  # same story can appear under several companies
            seen.add(item["link"])
            row = {
                "url": item["link"],
                "company_id": company_id,
                "item_date": item["published"],
                "tag": tag_headline(item["title"]),
                "headline": item["title"],
                "summary": item["publisher"],  # publisher name only; no article text
                "source_url": item["link"],
                "source_type": "news",
                "published_date": item["published"],
                "evidence_label": "Signal",
            }
            status = store.upsert(conn, run_id, "news_item", row)
            if status != "rejected":
                written += 1
    return written
