"""Source types of every public source in the sheets, keyed by URL.

Each sheet's Sources tab gives a Type for each source ID (for example "Primary" or "Secondary,
trade press"). The badge rule needs the type of a row's source (src/domain/confidence.py), so
the refresh stores one lookup: URL to source type. Technology's Sources tab has no Type column
yet, so its URLs have an empty type: their rows are not Fact until the sheet gives a type.
"""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"

# (sheet file, sheet name, (URL column, Type column) pairs). A sheet can hold more than one pair:
# the register gives each site its source and its service source, each with its own type.
SOURCE_FILES: tuple[tuple[str, str, tuple[tuple[str, str], ...]], ...] = (
    ("demand/sheet/sources.csv", "demand", (("URL or endpoint", "Type"),)),
    ("overview/sheet/sources.csv", "overview", (("URL", "Type"),)),
    ("china/sheet/sources.csv", "china", (("URL", "Type"),)),
    ("coverage/sheet/sources.csv", "coverage", (("URL", "Type"),)),
    ("clusters/sheet/data_sources.csv", "clusters", (("URL or endpoint", "Source type"),)),
    ("technology/sheet/sources.csv", "technology", (("URL", "Type"),)),
    ("overview/sheet/layoffs.csv", "layoffs", (("Source URL", "Source type"),)),
    (
        "coverage/sheet/register_sites.csv",
        "register",
        (
            ("Source URL", "Source type (column P)"),
            ("Service source URL", "Service source type (column U)"),
        ),
    ),
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS sheet_source_type (
    url TEXT PRIMARY KEY,
    sheet TEXT NOT NULL,
    source_type TEXT NOT NULL
)
"""


def load_source_types(conn: sqlite3.Connection, run_id: int) -> int:
    """Rebuild the URL to source type lookup from every Sources tab. Returns rows written."""
    conn.execute(SCHEMA)
    conn.execute("DELETE FROM sheet_source_type")
    written = 0
    for path, sheet, pairs in SOURCE_FILES:
        with (DATA_DIR / path).open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        for row in rows:
            for url_col, type_col in pairs:
                url = (row.get(url_col) or "").strip()
                if not url.startswith("http"):
                    continue
                source_type = (row.get(type_col) or "").strip()
                conn.execute(
                    "INSERT OR REPLACE INTO sheet_source_type (url, sheet, source_type) "
                    "VALUES (?, ?, ?)",
                    (url, sheet, source_type),
                )
                written += 1
    conn.commit()
    return written
