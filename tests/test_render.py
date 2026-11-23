"""Render tests: every screen renders with no exception against the app database, and shows its
screen header. Each screen is rendered by Streamlit's AppTest (no browser). The visual baseline
at two widths is taken separately by scripts/visual_baseline.py.

Uses the repository's data/app.db (read only). Skips if it is not there."""

import re

import pytest
from streamlit.testing.v1 import AppTest

from src.ingest.refresh import DEFAULT_DB

SCREENS = [
    ("overview_screen", "Overview (screen 1 of 6)"),
    ("coverage_page", "Competitor coverage (screen 2 of 6)"),
    ("clusters_page", "Customer clusters (screen 3 of 6)"),
    ("demand_page", "Demand drivers (screen 4 of 6)"),
    ("technology_page", "Technology estate (screen 5 of 6)"),
    ("china_page", "China (screen 6 of 6)"),
]


def _script(function_name: str) -> str:
    # conftest points APP_DB_PATH at a temp file. The render uses the real database instead, and
    # the app module is imported afresh so that it reads that path.
    return (
        "import os, sys\n"
        f"sys.path.insert(0, {str(DEFAULT_DB.parents[1])!r})\n"
        f"os.environ['APP_DB_PATH'] = {str(DEFAULT_DB)!r}\n"
        "sys.modules.pop('src.app.streamlit_app', None)\n"
        "import src.app.streamlit_app as app\n"
        f"app.{function_name}()\n"
    )


@pytest.mark.skipif(not DEFAULT_DB.exists(), reason="data/app.db is not in this checkout")
@pytest.mark.parametrize(("function_name", "header"), SCREENS)
def test_screen_renders_without_exception(function_name, header):
    at = AppTest.from_string(_script(function_name), default_timeout=240).run()
    assert not at.exception, [e.value for e in at.exception]
    text = " ".join(m.value for m in at.markdown)
    assert header in text
    # Years are never shown with a thousands separator (2028, not 2,028).
    assert not re.search(r"(19|20),\d{3}", text), re.findall(r"(?:19|20),\d{3}", text)


@pytest.mark.skipif(not DEFAULT_DB.exists(), reason="data/app.db is not in this checkout")
def test_overview_tiles_with_an_evidence_drawer_show_their_button():
    at = AppTest.from_string(_script("overview_screen"), default_timeout=240).run()
    assert not at.exception, [e.value for e in at.exception]
    labels = [b.label for b in at.button]
    # Peer financials, layoffs and deal activity: each has an Evidence button.
    assert labels.count("Evidence") >= 3
