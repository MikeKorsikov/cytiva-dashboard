"""Tests for the deal loader and counts. No network access."""

from datetime import date

import pytest

from src.ingest import deals, store
from src.metrics.deals import CATEGORIES, deal_counts


@pytest.mark.parametrize(
    ("headline", "category"),
    [
        ("Danaher acquires StartupCo for $1.2 billion", "M&A"),
        ("Repligen to acquire BioLife Solutions", "M&A"),
        ("Thermo Fisher agrees to buy Acme Bio", "M&A"),
        ("Sartorius licenses cell culture platform to Acme", "Licensing"),
        ("Avantor signs collaboration with Beta Labs", "Collaboration"),
        ("Avantor explores sale of unit", None),  # deal talk: not counted
        ("Analyst day scheduled", None),
    ],
)
def test_categorize(headline, category):
    assert deals.categorize(headline) == category


@pytest.mark.parametrize(
    ("headline", "name", "expected"),
    [
        ("Danaher acquires StartupCo", "Danaher", True),
        ("Danaher's unit acquires", "Danaher", False),  # possessive, not the company as subject
        ("Merck buys Bio-Techne", "Danaher", False),  # buyer is not the subject
        ("MilliporeSigma to acquire Acme", "MilliporeSigma", True),
    ],
)
def test_is_subject(headline, name, expected):
    assert deals.is_subject(headline, name) is expected


@pytest.fixture
def conn(tmp_path):
    connection = store.connect(tmp_path / "app.db")
    store.create_schema(connection)
    yield connection
    connection.close()


def _insert(conn, acquirer, headline, day, category="M&A", status="announced"):
    run_id = store.start_run(conn, "manual")
    store.upsert(
        conn,
        run_id,
        "deal",
        {
            "acquirer": acquirer,
            "announced_date": day,
            "category": category,
            "headline": headline,
            "value_usd": None,
            "status": status,
            "source_url": f"https://news.example.com/{abs(hash(headline))}",
            "source_type": "news",
            "published_date": day,
            "evidence_label": "Signal",
        },
    )


def test_deal_counts_by_category_and_window(conn):
    as_of = date(2026, 11, 8)
    _insert(conn, "Danaher", "Danaher acquires A", "2026-06-01")  # M&A, 12 months
    _insert(conn, "Danaher", "Danaher buys B", "2024-03-01")  # M&A, 5 years only
    _insert(conn, "Danaher", "Danaher licenses C", "2025-01-10", category="Licensing")
    _insert(conn, "Danaher", "Danaher talks D", "2026-07-01", status="deal talk")  # not counted
    _insert(conn, "Danaher", "Danaher old E", "2019-01-01")  # outside 5 years
    counts = deal_counts(conn, "Danaher", as_of)
    assert set(counts) == set(CATEGORIES)
    assert counts["M&A"] == {"last_12m": 1, "last_5y": 2}
    assert counts["Licensing"] == {"last_12m": 0, "last_5y": 1}
    assert counts["Collaboration"] == {"last_12m": 0, "last_5y": 0}


def test_same_deal_under_different_headlines_is_duplicate(conn):
    _insert(
        conn, "Repligen", "Repligen to acquire BioLife Solutions for $1.5 billion", "2026-07-22"
    )
    assert deals.is_duplicate(
        conn, "Repligen", "M&A", "Repligen completes acquisition of BioLife Solutions", "2026-07-23"
    )
    assert not deals.is_duplicate(
        conn, "Repligen", "M&A", "Repligen acquires Other Corp", "2026-07-22"
    )
    assert not deals.is_duplicate(
        conn, "Repligen", "M&A", "Repligen to acquire BioLife Solutions", "2026-08-30"
    )  # outside 3 days


def test_load_deals_stores_subject_headlines_once(conn, monkeypatch):
    feed = [
        {
            "title": "Danaher acquires StartupCo for $1.2 billion",
            "link": "https://n.example/1",
            "published": "2026-02-18",
        },
        {
            "title": "Merck buys Bio-Techne",
            "link": "https://n.example/2",
            "published": "2026-02-17",
        },
    ]
    monkeypatch.setattr(deals, "_candidates", lambda name: feed if name == "Danaher" else [])
    run_id = store.start_run(conn, "manual")
    assert deals.load_deals(conn, run_id) == 1
    row = conn.execute("SELECT acquirer, category, headline FROM deal").fetchone()
    assert (row["acquirer"], row["category"]) == ("Danaher", "M&A")
