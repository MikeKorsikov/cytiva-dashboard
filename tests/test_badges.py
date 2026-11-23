"""The badge rule (src/domain/confidence.py) and its use on every screen.

- Unit tests: FACT needs H and a Primary source; L is UNCONFIRMED; a tile shows its weakest row.
- Walk: on each screen, every row badge drawn is checked against the rule, with the source type
  read independently from the database (sheet_source_type). No network.
"""

import pytest
from streamlit.testing.v1 import AppTest

from src.app.design import BADGE_ROWS_KEY
from src.domain.confidence import (
    FACT,
    FACT_AND_SIGNAL,
    HYPOTHESIS,
    SIGNAL,
    UNCONFIRMED,
    is_primary,
    row_label,
    tile_label,
)
from src.ingest import store
from src.ingest.refresh import DEFAULT_DB
from src.metrics.source_types import source_types

# ---- the rule -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("confidence", "source_type", "expected"),
    [
        ("H", "Primary", FACT),
        ("H", "Primary filing", FACT),
        ("H", "Primary (company)", FACT),
        ("H", "Secondary, trade press", SIGNAL),
        ("H", "Commercial market report (summary page)", SIGNAL),
        ("H", "", SIGNAL),  # no known source type: never Fact
        ("H", None, SIGNAL),
        ("M", "Primary", SIGNAL),  # medium confidence is never Fact
        ("L", "Primary", UNCONFIRMED),  # L is always UNCONFIRMED
        ("L", "Secondary", UNCONFIRMED),
    ],
)
def test_row_label_follows_confidence_and_source_type(confidence, source_type, expected):
    assert row_label(confidence, source_type) == expected


def test_a_primary_source_type_is_recognised_by_its_first_word():
    assert is_primary("Primary")
    assert is_primary("primary data (WHO agency), secondary page")  # starts with Primary
    assert not is_primary("Secondary (data aggregator)")
    assert not is_primary(None)


@pytest.mark.parametrize(
    ("labels", "expected"),
    [
        ([FACT, FACT], FACT),
        ([FACT, SIGNAL], FACT_AND_SIGNAL),
        ([SIGNAL, SIGNAL], SIGNAL),
        ([FACT, UNCONFIRMED], UNCONFIRMED),
        ([HYPOTHESIS], HYPOTHESIS),
        ([], None),
    ],
)
def test_a_tile_shows_its_weakest_row(labels, expected):
    assert tile_label(labels) == expected


# ---- the walk over every rendered row, on every screen --------------------------------------

SCREENS = [
    "overview_screen",
    "coverage_page",
    "clusters_page",
    "demand_page",
    "technology_page",
    "china_page",
]


@pytest.mark.skipif(not DEFAULT_DB.exists(), reason="data/app.db is not in this checkout")
@pytest.mark.parametrize("function_name", SCREENS)
def test_every_rendered_row_badge_follows_the_rule(function_name):
    script = (
        "import os, sys\n"
        f"sys.path.insert(0, {str(DEFAULT_DB.parents[1])!r})\n"
        f"os.environ['APP_DB_PATH'] = {str(DEFAULT_DB)!r}\n"
        "sys.modules.pop('src.app.streamlit_app', None)\n"
        "import src.app.streamlit_app as app\n"
        f"app.{function_name}()\n"
    )
    at = AppTest.from_string(script, default_timeout=240).run()
    assert not at.exception, [e.value for e in at.exception]
    rows = at.session_state[BADGE_ROWS_KEY]
    conn = store.connect(DEFAULT_DB)
    try:
        types = source_types(conn)  # read straight from the database, not from the page
    finally:
        conn.close()
    for row in rows:
        expected = row_label(row["confidence"], types.get(row["url"] or "", ""))
        assert row["label"] == expected, (function_name, row)


@pytest.mark.skipif(not DEFAULT_DB.exists(), reason="data/app.db is not in this checkout")
def test_layoff_cells_on_the_overview_follow_the_rule_and_the_toggle():
    script = (
        "import os, sys\n"
        f"sys.path.insert(0, {str(DEFAULT_DB.parents[1])!r})\n"
        f"os.environ['APP_DB_PATH'] = {str(DEFAULT_DB)!r}\n"
        "sys.modules.pop('src.app.streamlit_app', None)\n"
        "import src.app.streamlit_app as app\n"
        "app.overview_screen()\n"
    )
    at = AppTest.from_string(script, default_timeout=240).run()
    assert not at.exception, [e.value for e in at.exception]
    conn = store.connect(DEFAULT_DB)
    try:
        types = source_types(conn)
        cells = conn.execute(
            "SELECT confidence, source_url FROM layoff_year WHERE source_url IS NOT NULL"
        ).fetchall()
    finally:
        conn.close()
    layoff_rows = [r for r in at.session_state[BADGE_ROWS_KEY] if r["url"] in {c[1] for c in cells}]
    # every visible layoff cell (not L) is drawn with its rule badge, from its own confidence
    assert layoff_rows
    for row in layoff_rows:
        assert row["confidence"] != "L"
        assert row["label"] == row_label(row["confidence"], types.get(row["url"], ""))
