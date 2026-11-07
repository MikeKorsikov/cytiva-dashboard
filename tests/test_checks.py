"""Tests for the AI-populated data checks. No network access."""

from src.ingest.checks import (
    check_quote,
    check_range,
    check_segment_within_group,
    check_source,
    check_yoy_change,
    verdict,
)


def test_source_passes_with_https_link_and_known_labels():
    assert check_source("https://example.com/report", "document", "Fact") == []


def test_source_rejects_missing_or_insecure_link():
    assert check_source(None, "document", "Fact")
    assert check_source("http://example.com", "document", "Fact")


def test_source_rejects_unknown_type_or_label():
    assert check_source("https://example.com", "guess", "Fact")
    assert check_source("https://example.com", "document", "Opinion")


def test_quote_matches_formatted_number():
    assert check_quote("1,234", "Revenue rose to $1,234 million in 2025.") == []


def test_quote_rejects_number_not_in_source():
    assert check_quote("1,235", "Revenue rose to $1,234 million in 2025.")


def test_quote_needs_source_text():
    assert check_quote("12", None)


def test_range_flags_out_of_bounds_value():
    assert check_range("gross margin", 120.0, 0, 100)
    assert check_range("gross margin", 59.1, 0, 100) == []


def test_range_ignores_missing_value():
    assert check_range("gross margin", None, 0, 100) == []


def test_segment_cannot_exceed_group():
    assert check_segment_within_group("biotech", 8.0, 7.0)
    assert check_segment_within_group("biotech", 7.0, 24.6) == []


def test_yoy_change_above_threshold_is_flagged():
    assert check_yoy_change("revenue", 200.0, 100.0)  # +100%
    assert check_yoy_change("revenue", 103.0, 100.0) == []  # +3%


def test_verdict_is_unverified_when_any_problem():
    assert verdict([]).passed is True
    result = verdict(["value not found in source text"])
    assert result.passed is False
    assert result.notes == ["value not found in source text"]
