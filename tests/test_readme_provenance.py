"""Screen 1 provenance text comes from the overview sheet README rows (audit B-18)."""

from __future__ import annotations

from pathlib import Path

from src.domain.tabs import README_PRICES
from src.ingest import store
from src.ingest.overview_sheet import load_readme
from src.metrics.overview import readme_note

APP = Path(__file__).resolve().parents[1] / "src" / "app" / "streamlit_app.py"


def test_readme_rows_load_and_are_read_by_label(tmp_path):
    conn = store.connect(tmp_path / "app.db")
    store.create_schema(conn)
    written = load_readme(conn)
    assert written > 0
    assert readme_note(conn, "As of") == "2026-11-18"
    assert readme_note(conn, README_PRICES) is None  # the row is not in the sheet yet
    conn.close()


def test_the_typed_provenance_sentences_are_gone_from_the_screen():
    source = APP.read_text(encoding="utf-8")
    for sentence in (
        "Yahoo Finance via yfinance",
        "Sartorius is Signal",
        "Earlier hand-entered values",
    ):
        assert sentence not in source, sentence
