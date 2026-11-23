"""Thresholds live in src/domain/thresholds.py (audit B-14). These tests pin the boundaries."""

from __future__ import annotations

from pathlib import Path

from src.app.shells import _score_bg
from src.domain import thresholds as t
from src.metrics.technology import relevance_label

SHELLS = Path(__file__).resolve().parents[1] / "src" / "app" / "shells.py"


def test_score_colour_boundaries_follow_the_thresholds():
    assert _score_bg(t.SCORE_GREEN_BELOW - 0.1) == "#E6F4EC"  # green below 2
    assert _score_bg(t.SCORE_GREEN_BELOW) == "#FFF4D6"  # amber from 2
    assert _score_bg(t.SCORE_AMBER_BELOW - 0.1) == "#FFF4D6"  # amber below 3.5
    assert _score_bg(t.SCORE_AMBER_BELOW) == "#FDECEA"  # red from 3.5


def test_relevance_boundaries_follow_the_thresholds():
    assert relevance_label(t.RELEVANCE_HIGH_FROM)[0] == "High"
    assert relevance_label(t.RELEVANCE_HIGH_FROM - 1)[0] == "Medium"
    assert relevance_label(t.RELEVANCE_MEDIUM_FROM)[0] == "Medium"
    assert relevance_label(t.RELEVANCE_MEDIUM_FROM - 1)[0] == "Low"


def test_no_threshold_literals_in_the_screens():
    source = SHELLS.read_text(encoding="utf-8")
    for literal in ("idx >= 2.5", "score < 2:", "score < 3.5", "below 2.0"):
        assert literal not in source, literal
