"""Years and source names in the screens come from the data (audit B-12, partly done)."""

from __future__ import annotations

from pathlib import Path

from src.app.shells import _column_year
from src.metrics import demand as dm

SHELLS = Path(__file__).resolve().parents[1] / "src" / "app" / "shells.py"


def test_a_year_comes_from_the_column_it_is_named_for():
    assert _column_year("sales_fy2025_usd_bn") == "FY2025"
    assert _column_year("new_cancer_cases_2024") == "2024"


def test_map_points_carry_the_year_of_the_cases_column():
    country = next(iter(dm.COUNTRY_CENTRE))
    data = dm.DemandData(
        burden=[
            {
                "country": country,
                "map_region": "North America",
                "new_cancer_cases_2024": "1,000",
            }
        ]
    )
    points = dm.map_points(data)
    assert points and points[0]["year"] == "2024"


def test_the_typed_labels_are_gone():
    source = SHELLS.read_text(encoding="utf-8")
    for label in (
        "(2022)",
        "Pharma 50 (secondary source)",
        "Q2 2026, ASGCT",
        "Q1 2026: to collect",
    ):
        assert label not in source, label
