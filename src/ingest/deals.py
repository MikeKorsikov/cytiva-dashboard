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

# (company_id, name used in searches and matched at the start of headlines). A company can have
# several names: a group's deals are often announced under a life-science brand (MilliporeSigma).
DEAL_BUYERS: tuple[tuple[str, str], ...] = (
    ("Danaher", "Danaher"),
    # Danaher's operating companies announce deals under their own names; they count for the group.
    ("Danaher", "Cytiva"),
    ("Danaher", "Leica Biosystems"),
    ("Danaher", "Beckman Coulter"),
    ("Danaher", "Cepheid"),
    ("Danaher", "Pall Corporation"),  # not "Pall": that matches Pall Mall
    ("Danaher", "Abcam"),
    ("Danaher", "Aldevron"),
    ("Danaher", "Radiometer"),
    ("Danaher", "Molecular Devices"),
    ("Thermo Fisher", "Thermo Fisher"),
    ("Sartorius", "Sartorius"),
    ("Repligen", "Repligen"),
    ("Avantor", "Avantor"),
    ("Merck KGaA", "Merck KGaA"),  # group, as the other buyers; headlines must start with it
    ("Merck KGaA", "MilliporeSigma"),  # life-science brand of the group
)


def buyer_names() -> dict[str, tuple[str, ...]]:
    """Every name each company is known by in deal headlines, keyed by company_id."""
    names: dict[str, list[str]] = {}
    for company_id, name in DEAL_BUYERS:
        names.setdefault(company_id, []).append(name)
    return {company_id: tuple(values) for company_id, values in names.items()}


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

# A headline counts only if it reports a deal. Commentary, analysis, history and stock news use
# the same words as deal reports, so they are excluded before any category is assigned.
EXCLUDED = re.compile(
    r"\b(?:history|buyback|ratings?|price target|stocks?|shares|trades?|trading|analysts?|"
    r"outlook|opinion|why|could|may|should|might|eye to|pledges?|tracker|layoffs?|down|up|"
    r"is the)\b|collaboration cent(?:er|re)s?\b",
    re.IGNORECASE,
)
# First matching category wins; checked in this order.
CATEGORY_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "M&A",
        re.compile(
            r"\b(?:acquires?|acquired|acquiring|acquisition of|to acquire|buys?|bought|to buy|"
            r"completes? (?:the )?acquisition|agrees? to (?:buy|acquire)|mergers?|"
            r"merges? with|takeover)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Licensing",
        re.compile(r"\blicen[cs](?:es?|ed|ing)\b|\blicen[cs]e agreement\b", re.IGNORECASE),
    ),
    (
        "Collaboration",
        re.compile(
            r"\b(?:collaborat\w*|partnerships?|partners? with|alliance|strategic partner\w*)\b",
            re.IGNORECASE,
        ),
    ),
)
# Words that do not identify a deal: generic terms, corporate suffixes and deal verbs.
_GENERIC = {
    "business",
    "company",
    "group",
    "corporation",
    "limited",
    "agreement",
    "announces",
    "acquires",
    "acquire",
    "acquired",
    "acquisition",
    "completes",
    "completed",
    "completion",
    "buys",
    "buy",
    "deal",
    "billion",
    "million",
    "strategic",
    "partnership",
    "collaboration",
    "license",
    "licensing",
    "licenses",
    "solutions",
    "systems",
    "technologies",
    "technology",
    "holdings",
    "sciences",
    "science",
    "therapeutics",
    "pharmaceuticals",
    "medical",
    "biotech",
    "inc",
    "ltd",
    "plc",
    "corp",
    "international",
    "global",
}
# Two headlines about the same deal within this many days are one deal.
DUPLICATE_DAYS = 180


class DealError(RuntimeError):
    """Raised when a deal source cannot be read. The loader skips that source and continues."""


def headline_text(title: str) -> str:
    """The headline without the source name that news feeds add after ' - ' (e.g. ' - Fierce')."""
    head, sep, source = title.rpartition(" - ")
    return head if sep and len(source.split()) <= 5 else title


def categorize(headline: str) -> str | None:
    text = headline_text(headline)
    if EXCLUDED.search(text):
        return None
    for category, pattern in CATEGORY_PATTERNS:
        if pattern.search(text):
            return category
    return None


def is_subject(headline: str, name: str) -> bool:
    """True if the headline starts with the company name, i.e. the company is the subject."""
    head = headline.strip().lower()
    prefix = name.lower()
    return head.startswith(prefix) and (len(head) == len(prefix) or head[len(prefix)].isspace())


def _buyer_words(acquirer: str) -> set[str]:
    return set(re.findall(r"[a-z]+", acquirer.lower()))


def distinctive_words(headline: str, acquirer: str) -> set[str]:
    """Lower-case words of 5+ letters that are not generic and not part of the buyer's name."""
    buyer = _buyer_words(acquirer)
    return {
        w
        for w in re.findall(r"[a-z]+", headline_text(headline).lower())
        if len(w) >= 5 and w not in _GENERIC and w not in buyer
    }


def proper_nouns(headline: str, acquirer: str) -> set[str]:
    """Capitalised words after the first word, e.g. the target's name. Buyer's name excluded."""
    buyer = _buyer_words(acquirer)
    words = re.findall(r"[A-Z][A-Za-z\-]{2,}", headline_text(headline))[1:]  # 3+ letters, e.g. PPD
    return {w.lower() for w in words if w.lower() not in _GENERIC | buyer}


def same_deal(acquirer: str, first: str, second: str) -> bool:
    """Headlines describe one deal if they name the same target or share two distinctive words."""
    if proper_nouns(first, acquirer) & proper_nouns(second, acquirer):
        return True
    return len(distinctive_words(first, acquirer) & distinctive_words(second, acquirer)) >= 2


def is_duplicate(
    conn: sqlite3.Connection, acquirer: str, category: str, headline: str, day: str
) -> bool:
    """True if a stored deal of the same category, within DUPLICATE_DAYS, is the same deal."""
    center = date.fromisoformat(day)
    window = timedelta(days=DUPLICATE_DAYS)
    rows = conn.execute(
        "SELECT headline FROM deal WHERE acquirer = ? AND category = ? "
        "AND announced_date BETWEEN ? AND ?",
        (acquirer, category, (center - window).isoformat(), (center + window).isoformat()),
    ).fetchall()
    return any(same_deal(acquirer, headline, r["headline"]) for r in rows)


def revalidate_stored(conn: sqlite3.Connection, run_id: int) -> int:
    """Apply the current rules to deals already stored: drop headlines the rules now reject,
    recategorise the rest, and keep one row per deal. Returns the number of rows removed."""
    names = buyer_names()
    # Company-reported (Fact) rows are checked when they are entered, and come first so that a
    # news (Signal) report of the same deal is the one that is removed.
    rows = conn.execute(
        "SELECT acquirer, announced_date, headline, category, evidence_label FROM deal "
        "ORDER BY CASE WHEN evidence_label = 'Fact' THEN 0 ELSE 1 END, announced_date"
    ).fetchall()
    kept: list[tuple[str, str, str, str]] = []  # (acquirer, category, headline, date)
    removed = 0
    for row in rows:
        acquirer, headline, day = row["acquirer"], row["headline"], row["announced_date"]
        if row["evidence_label"] == "Fact":
            category = row["category"]
            valid = acquirer in names
        else:
            category = categorize(headline)
            valid = (
                acquirer in names
                and any(is_subject(headline, name) for name in names[acquirer])
                and category
            )
        duplicate = valid and any(
            k_acq == acquirer
            and k_cat == category
            and abs((date.fromisoformat(k_day) - date.fromisoformat(day)).days) <= DUPLICATE_DAYS
            and same_deal(acquirer, headline, k_head)
            for k_acq, k_cat, k_head, k_day in kept
        )
        if not valid or duplicate:
            store.log_delete(
                conn,
                run_id,
                "deal",
                {"acquirer": acquirer, "announced_date": day, "headline": headline},
                {"category": row["category"]},
            )
            conn.execute(
                "DELETE FROM deal WHERE acquirer = ? AND announced_date = ? AND headline = ?",
                (acquirer, day, headline),
            )
            removed += 1
            continue
        if category != row["category"]:
            conn.execute(
                "UPDATE deal SET category = ? WHERE acquirer = ? AND announced_date = ? "
                "AND headline = ?",
                (category, acquirer, day, headline),
            )
        kept.append((acquirer, category, headline, day))
    return removed


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
    revalidate_stored(conn, run_id)  # stored rows follow the current rules
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
