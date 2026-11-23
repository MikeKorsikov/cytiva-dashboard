"""EvidenceDrawer: the public-source rule, the row builders, and the Evidence buttons on the
Overview. No network: the overview data comes from the sheet loaded into a temp database."""

import pytest

from src.app.ui.evidence import (
    Evidence,
    deal_items,
    financial_items,
    is_public_source,
    layoff_items,
    sources_missing,
)
from src.ingest import company_deals, store
from src.ingest.overview_sheet import load_overview_sheet
from src.metrics import overview


def test_public_source_is_an_https_link_not_the_research_sheet():
    assert is_public_source("https://www.sec.gov/Archives/x.htm")
    assert not is_public_source("https://docs.google.com/spreadsheets/d/abc")
    assert not is_public_source("http://example.com/x")
    assert not is_public_source("")
    assert not is_public_source(None)


def test_rows_without_a_public_source_are_counted():
    items = [
        Evidence(row="a", shown="1", label="Fact", source_url="https://example.com/a"),
        Evidence(row="b", shown="2", label="Signal", source_url=None),
        Evidence(
            row="c",
            shown="3",
            label="Fact",
            source_url="https://docs.google.com/spreadsheets/d/abc",
        ),
    ]
    assert sources_missing(items) == 2


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "app.db"
    conn = store.connect(path)
    store.create_schema(conn)
    run = store.start_run(conn, "manual")
    company_deals.load_company_deals(conn, run)
    load_overview_sheet(conn, run)
    conn.close()
    return overview.connect_readonly(path)


def test_financial_rows_carry_their_basis_and_source(db):
    items = financial_items(overview.peer_financials(db))
    assert len(items) == 6
    by_row = {i.row.split(",")[0]: i for i in items}
    assert by_row["Danaher"].label == "Fact"
    assert by_row["Sartorius"].label == "Signal"
    assert all(is_public_source(i.source_url) for i in items)
    assert sources_missing(items) == 0


def test_layoff_rows_are_one_per_company_year(db):
    # Three cells are L (LO-04, LO-15, LO-18): hidden by default, listed with the toggle on.
    assert len(layoff_items(overview.layoff_marks(db))) == 15
    items = layoff_items(overview.layoff_marks(db), show_l=True)
    assert len(items) == 18
    thermo_2026 = next(i for i in items if i.row == "Thermo Fisher, 2026")
    assert thermo_2026.shown == "Yes"
    assert thermo_2026.label == "Signal"  # LO-01 is M confidence


def test_deal_rows_are_the_sheet_deals_and_the_feed_signals(db):
    items = deal_items(overview.sheet_deals(db), [])
    assert len(items) == 6
    # each deal's badge is derived from its confidence and its first source's type (the rule)
    labels = {}
    for i in items:
        labels.setdefault(i.row.split(",")[0], set()).add(i.label)
    assert labels == {
        "Danaher": {"Fact"},
        "Merck KGaA": {"Signal"},
        "Repligen": {"Signal"},
        "Sartorius": {"Signal"},
        "Thermo Fisher": {"Signal"},
    }
    signal = deal_items(
        [],
        [
            {
                "acquirer": "Danaher",
                "announced_date": "2026-10-01",
                "headline": "Feed item",
                "source_url": "https://news.example/x",
            }
        ],
    )
    assert signal[0].label == "Signal"
