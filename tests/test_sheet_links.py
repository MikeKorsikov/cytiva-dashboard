"""Sheet links (audit B-12, B-15, B-18): the links and labels the screens read exist in the data."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from src.domain.tabs import DEMAND_LABELS

DB = Path(__file__).resolve().parents[1] / "data" / "app.db"
needs_db = pytest.mark.skipif(not DB.exists(), reason="data/app.db is not in this checkout")


@needs_db
def test_every_end_of_support_application_is_in_the_application_list():
    conn = sqlite3.connect(DB)
    apps = {r[0] for r in conn.execute("SELECT name FROM tech_apps")}
    linked = [
        (eos_id, app) for eos_id, app in conn.execute("SELECT id, application FROM tech_eos") if app
    ]
    blank = conn.execute("SELECT application FROM tech_eos WHERE id = 'EOS-04'").fetchone()
    conn.close()
    assert [a for _, a in linked if a not in apps] == []
    assert blank is not None and not blank[0]  # EOS-04 (Windows 10) is deliberately blank


@needs_db
def test_every_demand_display_label_is_in_the_readme():
    conn = sqlite3.connect(DB)
    labels = {
        r[0] for r in conn.execute("SELECT label FROM screen_notes WHERE tab = 'Demand README'")
    }
    conn.close()
    missing = sorted(v for v in DEMAND_LABELS.values() if v not in labels)
    assert missing == []


@needs_db
def test_every_overview_provenance_row_is_in_the_readme():
    from src.domain.tabs import README_PRICES, README_RANKINGS, README_SARTORIUS

    conn = sqlite3.connect(DB)
    labels = {
        r[0] for r in conn.execute("SELECT label FROM screen_notes WHERE tab = 'Overview README'")
    }
    conn.close()
    assert {README_PRICES, README_SARTORIUS, README_RANKINGS} <= labels
