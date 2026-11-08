"""Tests for the news loader. No network access: feeds are fixtures."""

import pytest

from src.ingest import news, store

FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>x</title>
<item><title>Sartorius reports Q3 results, guidance raised - Example</title>
<link>https://news.example.com/a1</link>
<pubDate>Fri, 23 Oct 2026 07:00:00 GMT</pubDate><source>Example</source></item>
<item><title>Danaher agrees to acquire StartupCo - Example Wire</title>
<link>https://news.example.com/a2</link>
<pubDate>Thu, 22 Oct 2026 07:00:00 GMT</pubDate><source>Example Wire</source></item>
<item><title>Thermo to build new plant in Ohio - Daily</title>
<link>https://news.example.com/a3</link>
<pubDate>Wed, 21 Oct 2026 07:00:00 GMT</pubDate><source>Daily</source></item>
<item><title>Analyst day scheduled</title>
<link>https://news.example.com/a4</link>
<pubDate>Tue, 20 Oct 2026 07:00:00 GMT</pubDate></item>
</channel></rss>"""


@pytest.mark.parametrize(
    ("headline", "tag"),
    [
        ("Sartorius reports Q3 results, guidance raised", "Results"),
        ("Danaher agrees to acquire StartupCo", "M&A"),
        ("Avantor explores sale of unit", "Deal talk"),
        ("Thermo to build new plant in Ohio", "Capacity"),
        ("Analyst day scheduled", "Other"),
    ],
)
def test_tag_headline(headline, tag):
    assert news.tag_headline(headline) == tag


def test_m_and_a_wins_over_results_when_both_appear():
    assert news.tag_headline("Repligen acquires firm after strong quarter") == "M&A"


def test_parse_feed_reads_title_link_date_and_publisher():
    items = news.parse_feed(FEED)
    assert len(items) == 4
    assert items[0] == {
        "title": "Sartorius reports Q3 results, guidance raised - Example",
        "link": "https://news.example.com/a1",
        "published": "2026-10-23",
        "publisher": "Example",
    }
    assert items[3]["publisher"] is None


def test_parse_feed_rejects_invalid_xml():
    with pytest.raises(news.NewsError, match="not valid XML"):
        news.parse_feed(b"<rss><channel>")


def test_news_url_encodes_the_query():
    assert "q=MilliporeSigma+Process+Solutions" in news.news_url("MilliporeSigma Process Solutions")


@pytest.fixture
def conn(tmp_path):
    connection = store.connect(tmp_path / "app.db")
    store.create_schema(connection)
    yield connection
    connection.close()


def test_load_news_stores_tagged_items_without_article_text(conn, monkeypatch):
    monkeypatch.setattr(news, "fetch_feed", lambda query: FEED)
    run_id = store.start_run(conn, "manual")

    written = news.load_news(conn, run_id)

    # The same four links come back for every company, so each link is stored once.
    assert written == 4
    row = conn.execute(
        "SELECT company_id, tag, summary, source_type, evidence_label FROM news_item "
        "WHERE url = 'https://news.example.com/a2'"
    ).fetchone()
    assert row["company_id"] == "Danaher"  # first company to return the link
    assert row["tag"] == "M&A"
    assert row["summary"] == "Example Wire"  # publisher only
    assert (row["source_type"], row["evidence_label"]) == ("news", "Signal")


def test_item_without_link_is_rejected(conn, monkeypatch):
    feed = b"""<rss><channel><item><title>No link here</title>
    <pubDate>Fri, 23 Oct 2026 07:00:00 GMT</pubDate></item></channel></rss>"""
    monkeypatch.setattr(news, "fetch_feed", lambda query: feed)
    run_id = store.start_run(conn, "manual")
    assert news.load_news(conn, run_id) == 0
    assert conn.execute("SELECT COUNT(*) FROM news_item").fetchone()[0] == 0
