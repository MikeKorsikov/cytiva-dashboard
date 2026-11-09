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
        # Commentary and stock news that use deal words are not deals.
        ("Danaher Is Down 22% This Year. Is the Masimo Acquisition the Entry Point?", None),
        ("Danaher Business System and Acquisition History - Quartr", None),
        ("Stock Trades At A Discount Following Its 59% Five Year Decline", None),
        ("Merck KGaA pledges $50M to build new cardio biotech with eye to later acquisition", None),
        # Deal reports, including completions and partnerships.
        ("Danaher Completes Acquisition of Masimo Corporation", "M&A"),
        ("Merck KGaA to Acquire Bio-Techne for $11.3B", "M&A"),
        (
            "Merck KGaA eyes new Parkinson's disease assets with $3bn Valo partnership",
            "Collaboration",
        ),
        (
            "Merck KGaA drops pipeline assets from SpringWorks buyout, Hengrui licensing deal",
            "Licensing",
        ),
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
        conn, "Repligen", "M&A", "Repligen to acquire BioLife Solutions", "2027-02-01"
    )  # outside the duplicate window


def test_announcement_and_completion_of_one_deal_count_once(conn):
    _insert(
        conn,
        "Danaher",
        "Danaher buys patient monitoring specialist Masimo in $9.9B deal",
        "2026-02-18",
    )
    assert deals.is_duplicate(
        conn, "Danaher", "M&A", "Danaher Completes Acquisition of Masimo Corporation", "2026-06-10"
    )
    assert not deals.is_duplicate(
        conn, "Danaher", "M&A", "Danaher to acquire Abcam for $24.00 per share", "2026-06-10"
    )


def test_revalidate_removes_noise_and_duplicates(conn):
    _insert(
        conn,
        "Danaher",
        "Danaher buys patient monitoring specialist Masimo in $9.9B deal",
        "2026-02-18",
    )
    _insert(conn, "Danaher", "Danaher Completes Acquisition of Masimo Corporation", "2026-06-10")
    _insert(
        conn,
        "Danaher",
        "Danaher Is Down 22% This Year. Is the Masimo Acquisition the Entry Point?",
        "2026-06-24",
    )
    _insert(
        conn, "Danaher", "Danaher Business System and Acquisition History - Quartr", "2023-11-22"
    )
    run_id = store.start_run(conn, "manual")
    removed = deals.revalidate_stored(conn, run_id)
    assert removed == 3  # the completion (same deal), the stock article and the history article
    left = [r["headline"] for r in conn.execute("SELECT headline FROM deal")]
    assert left == ["Danaher buys patient monitoring specialist Masimo in $9.9B deal"]
    logged = conn.execute("SELECT COUNT(*) FROM change_log WHERE action = 'deleted'").fetchone()[0]
    assert logged == 3


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


def test_source_suffix_is_not_part_of_the_headline():
    assert deals.headline_text("Merck KGaA buys PostEra oral molecules - Chemical News") == (
        "Merck KGaA buys PostEra oral molecules"
    )
    # A dash inside a long title is kept: only a short trailing source name is removed.
    long = "Repligen to acquire BioLife in a long agreement - and it has many many words here"
    assert deals.headline_text(long) == long


def test_different_deals_from_one_source_are_not_duplicates():
    # Both titles end with the same source; the source name must not link them.
    first = "Merck KGaA buys PostEra oral molecules - Chemical Engineering News"
    second = "Merck KGaA to Acquire Bio-Techne for expanding tools - Genetic Engineering News"
    assert not deals.same_deal("Merck KGaA", first, second)


def test_collaboration_centres_are_not_collaborations():
    assert deals.categorize("Thermo Fisher Opens Advanced Therapies Collaboration Center") is None


def test_group_brand_deals_count_for_the_group(conn):
    # MilliporeSigma is the group's life-science brand; its deals count for Merck KGaA.
    _insert(conn, "Merck KGaA", "Merck KGaA to buy biotech SpringWorks for $3.9B", "2025-04-28")
    _insert(
        conn,
        "Merck KGaA",
        "MilliporeSigma to acquire chromatography business of JSR Life Sciences - Chemanager",
        "2025-10-15",
    )
    run_id = store.start_run(conn, "manual")
    assert deals.revalidate_stored(conn, run_id) == 0
    assert deals.buyer_names()["Merck KGaA"] == ("Merck KGaA", "MilliporeSigma")


def test_three_letter_target_names_identify_a_deal():
    first = "Thermo Fisher acquires clinical research services provider PPD for $17.4bn"
    second = "Thermo Fisher completes $17.4B acquisition of PPD"
    assert deals.same_deal("Thermo Fisher", first, second)
