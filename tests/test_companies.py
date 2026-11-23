"""The Overview company lists (audit B-16) match the company table; the order covers them."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from src.domain.companies import DEAL_BUYERS, NEWS_COMPANIES, PEER_ORDER, RANKING_COMPANIES

DB = Path(__file__).resolve().parents[1] / "data" / "app.db"


@pytest.mark.skipif(not DB.exists(), reason="data/app.db is not in this checkout")
def test_every_listed_company_is_in_the_company_table_or_is_cytiva():
    conn = sqlite3.connect(DB)
    names = {r[0] for r in conn.execute("SELECT name FROM company")}
    conn.close()
    listed = set(NEWS_COMPANIES) | set(DEAL_BUYERS) | set(RANKING_COMPANIES) | set(PEER_ORDER)
    unknown = sorted(n for n in listed if n not in names and n != "Cytiva")
    assert unknown == []


def test_the_order_covers_every_list():
    listed = set(NEWS_COMPANIES) | set(DEAL_BUYERS) | set(RANKING_COMPANIES)
    assert listed <= set(PEER_ORDER)
    assert len(set(PEER_ORDER)) == len(PEER_ORDER)
