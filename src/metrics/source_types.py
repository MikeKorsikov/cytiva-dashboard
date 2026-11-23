"""URL to source type, read from the database for the badge rule (src/domain/confidence.py).

The loader that fills the table is src/ingest/source_types.py. The app and tests read it here.
"""

from __future__ import annotations

import sqlite3


def source_types(conn: sqlite3.Connection) -> dict[str, str]:
    """URL to source type, for the app's badge rule. Empty when the table is not loaded yet."""
    try:
        rows = conn.execute("SELECT url, source_type FROM sheet_source_type").fetchall()
    except sqlite3.OperationalError:
        return {}
    return {r["url"]: r["source_type"] for r in rows}
