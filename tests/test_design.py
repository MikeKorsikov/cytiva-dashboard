"""Shared badge rule: FACT needs confidence H and a primary URL; no test touches the network."""

from src.app.design import evidence_badge, is_primary_url


def _label(html: str) -> str:
    return html.split(">")[1].split("<")[0]


def test_h_with_primary_url_is_fact():
    assert _label(evidence_badge("H", "https://www.sec.gov/x.htm")) == "FACT"


def test_h_without_url_is_signal():
    assert _label(evidence_badge("H", None)) == "SIGNAL"


def test_h_on_google_sheet_link_is_signal():
    url = "https://docs.google.com/spreadsheets/d/1MPccYB-6lvaNS5HbDMP0kMzfpmMvQbL5fdorRQi27KM"
    assert _label(evidence_badge("H", url)) == "SIGNAL"
    assert not is_primary_url(url)


def test_m_is_signal_even_with_url():
    assert _label(evidence_badge("M", "https://www.sec.gov/x.htm")) == "SIGNAL"


def test_l_is_unconfirmed():
    html = evidence_badge("L", "https://www.sec.gov/x.htm")
    assert _label(html) == "UNCONFIRMED"
    assert "b-unconfirmed" in html


def test_missing_confidence_is_signal():
    assert _label(evidence_badge(None, None)) == "SIGNAL"
