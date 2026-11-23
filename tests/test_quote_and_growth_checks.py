"""Quote check rules (B-05, report only) and growth enforcement (B-06).

Covers the four owner rules for the quote check, and the refresh step that marks a row unverified
when its reported growth is outside +-50%.
"""

from __future__ import annotations

from scripts.report_checks import check_quote_text
from src.ingest import store
from src.ingest.checks import apply_growth_checks, growth_problems


def test_rule_a_only_a_verbatim_quote_is_checked():
    assert check_quote_text(524.0, "North America $524m").status == "not verbatim"


def test_rule_b_units_currency_and_rounding_are_normalised():
    assert check_quote_text(524.0, '"North America $524m"').status == "pass"
    assert check_quote_text(17.6985, '"about $17.7 billion"').status == "pass"
    # a billion value against a million quote: 1.2 bn is 1200 m
    assert check_quote_text(1.2, '"revenue $1,200 m"').status == "pass"
    assert check_quote_text(2.87, '"approximately 12%"').status == "fail"


def test_rule_b_digits_after_non_ascii_text_are_found():
    assert check_quote_text(80.0, '"未来80%在华销售"').status == "pass"


def test_rule_c_derived_evidence_is_skipped():
    assert check_quote_text(2.7, "Calculation: H-01 x H-02").status == "derived"
    assert check_quote_text(17.7, "Sum of SR-01 to SR-05").status == "derived"
    assert check_quote_text(8.0, "Same as screen 3 CDMO sites").status == "derived"


def test_rule_d_missing_evidence_is_a_data_gap():
    assert check_quote_text(14.3, None).status == "gap"
    assert check_quote_text(14.3, "  ").status == "gap"


def _insert_growth(conn, row_id: str, company: str, growth: float) -> None:
    conn.execute(
        "INSERT INTO cn_financial (id, company_id, company, period, confidence, "
        "revenue_yoy_pct, source_url, "
        "source_type, published_date, loaded_at, evidence_label, is_sample, verification_status, "
        "check_notes) VALUES (?, ?, ?, 'FY2025', 'M', ?, 'https://example.org/x', 'curated', "
        "'2026-01-01', '2026-01-01', 'Fact', 0, 'passed', '')",
        (row_id, company, company, growth),
    )


def test_growth_above_fifty_percent_is_stored_unverified(tmp_path):
    conn = store.connect(tmp_path / "app.db")
    store.create_schema(conn)
    run_id = store.start_run(conn, "manual")
    _insert_growth(conn, "F1", "C09", 80.0)
    _insert_growth(conn, "F2", "C10", 12.0)
    conn.commit()
    assert len(growth_problems(conn)) == 1
    assert apply_growth_checks(conn, run_id) == 1
    rows = conn.execute(
        "SELECT company_id, verification_status, check_notes FROM cn_financial ORDER BY company_id"
    ).fetchall()
    assert rows[0]["verification_status"] == "unverified"
    assert "outside plausible range" in rows[0]["check_notes"]
    assert rows[1]["verification_status"] == "passed"
    changed = conn.execute(
        "SELECT COUNT(*) FROM change_log WHERE run_id = ? AND action = 'unverified'", (run_id,)
    ).fetchone()[0]
    assert changed == 1
    conn.close()
