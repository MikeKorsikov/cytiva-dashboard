"""Acceptance check 5 (per tile): every tile on every screen has an Evidence button, and every row
the tile shows is in its evidence dialog with a public source, or marked "no public source".

The check reads what the screens record when they draw each tile (session key
src.app.ui.evidence.EVIDENCE_TILES). It runs each screen with AppTest against the repository's
data/app.db (read only) and skips when that file is not in the checkout.
"""

import pytest
from streamlit.testing.v1 import AppTest

from src.app.ui.evidence import EVIDENCE_TILES, is_public_source
from src.ingest.refresh import DEFAULT_DB

# Tiles per screen (each has one Evidence button). The KPI cards of screens 3 and 4, the
# headline cards of screen 6 and the region cards of screen 2 each have their own button.
EXPECTED_TILES = {
    "overview_screen": 8,
    "coverage_page": 5,
    "clusters_page": 8,
    "demand_page": 13,
    "technology_page": 5,
    "china_page": 8,
}

# A tile with no rows to show may have an empty drawer: nothing is displayed to list.
MAY_BE_EMPTY = {"tech-security"}  # "No corroborated exposures" is shown when nothing qualifies


def _script(function_name: str) -> str:
    # conftest points APP_DB_PATH at a temp file; the check uses the real database instead.
    return (
        "import os, sys\n"
        f"sys.path.insert(0, {str(DEFAULT_DB.parents[1])!r})\n"
        f"os.environ['APP_DB_PATH'] = {str(DEFAULT_DB)!r}\n"
        "sys.modules.pop('src.app.streamlit_app', None)\n"
        "import src.app.streamlit_app as app\n"
        f"app.{function_name}()\n"
    )


@pytest.mark.skipif(not DEFAULT_DB.exists(), reason="data/app.db is not in this checkout")
@pytest.mark.parametrize("function_name", list(EXPECTED_TILES))
def test_every_tile_has_an_evidence_drawer_with_sources_or_a_no_source_mark(function_name):
    at = AppTest.from_string(_script(function_name), default_timeout=240).run()
    assert not at.exception, [e.value for e in at.exception]
    tiles = at.session_state[EVIDENCE_TILES]
    assert len(tiles) == EXPECTED_TILES[function_name], sorted(tiles)
    for key, (title, items) in tiles.items():
        if key not in MAY_BE_EMPTY:
            assert items, f"{title}: the drawer lists no rows"
        for item in items:
            assert item.row and item.shown, f"{title}: a row has no text"
            # A link to the research sheet is never a public source. The drawer then marks the
            # row "no public source", so a Fact row must not carry one.
            research_link = bool(item.source_url) and not is_public_source(item.source_url)
            assert not (research_link and item.label == "Fact"), (
                f"{title}: a Fact row links to a research-sheet link"
            )
