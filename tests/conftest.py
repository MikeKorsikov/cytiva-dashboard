"""Shared test fixtures.

Keeps every test away from the committed database (data/app.db): the refresh
default path and the app's database path are pointed at a temporary file.
"""

from pathlib import Path

import pytest

from src.ingest import refresh


@pytest.fixture(autouse=True)
def _isolate_app_database(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db = tmp_path / "isolated_app.db"
    monkeypatch.setattr(refresh, "DEFAULT_DB", db)
    monkeypatch.setenv("APP_DB_PATH", str(db))
    return db
