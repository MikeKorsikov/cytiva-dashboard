"""The coverage model (audit B-15) matches the footprint grid stored from the sheet."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from src.domain.coverage_model import COMPANIES, FAMILIES, STEPS

DB = Path(__file__).resolve().parents[1] / "data" / "app.db"


@pytest.mark.skipif(not DB.exists(), reason="data/app.db is not in this checkout")
def test_companies_and_families_match_the_grid():
    conn = sqlite3.connect(DB)
    companies = {r[0] for r in conn.execute("SELECT DISTINCT company_id FROM s2_grid")}
    families = {r[0] for r in conn.execute("SELECT DISTINCT family FROM s2_grid")}
    conn.close()
    assert {name for name, _ in COMPANIES} == companies
    # the grid also lists Service, which is a step rather than a family
    assert set(FAMILIES) == families - {"Service"}


def test_the_model_sizes_are_the_sheet_sizes():
    assert len(COMPANIES) == 6
    assert len(FAMILIES) == 8
    assert len(STEPS) == 8
