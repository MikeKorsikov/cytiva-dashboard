"""Enforced checks (refresh): a failing row is unverified and is treated like L (23 Nov 2026).

An unverified row is hidden by default and shown with the UNCONFIRMED badge when the screen's
"Show unconfirmed (L)" toggle is on.
"""

from __future__ import annotations

from src.app.design import visible
from src.domain.confidence import UNCONFIRMED, row_label
from src.ingest import store
from src.ingest.checks import apply_quote_checks


def _insert_headline(conn, run_id: int, row_id: str, value_text: str, evidence: str) -> None:
    store.upsert(
        conn,
        run_id,
        "cn_headline",
        {
            "id": row_id,
            "metric": "test metric",
            "value_text": value_text,
            "value_num": float(value_text),
            "unit": "%",
            "period": "FY2025",
            "show_on_tile": "No",
            "evidence_label": "Fact",
            "evidence": evidence,
            "source_note": "test",
            "confidence": "H",
            "source_url": "https://example.org/headline",
            "source_type": "curated",
            "published_date": "2026-01-01",
        },
    )


def test_a_failing_quote_row_is_unverified_and_hidden_like_l(tmp_path):
    conn = store.connect(tmp_path / "app.db")
    store.create_schema(conn)
    run_id = store.start_run(conn, "manual")
    _insert_headline(conn, run_id, "T-1", "80", '"the company said 12%"')  # 80 is not in the quote
    _insert_headline(conn, run_id, "T-2", "12", '"the company said 12%"')  # matches
    conn.commit()

    assert apply_quote_checks(conn, run_id) == 1
    rows = {
        r["id"]: r
        for r in conn.execute("SELECT id, confidence, verification_status FROM cn_headline")
    }
    assert rows["T-1"]["verification_status"] == "unverified"
    assert rows["T-1"]["confidence"] == "L"
    assert rows["T-2"]["verification_status"] == "passed"
    assert rows["T-2"]["confidence"] == "H"

    # hidden by default; with the toggle on it is shown with the UNCONFIRMED badge
    assert visible(rows["T-1"]["confidence"], show_unconfirmed=False) is False
    assert visible(rows["T-1"]["confidence"], show_unconfirmed=True) is True
    assert row_label(rows["T-1"]["confidence"], "Primary") == UNCONFIRMED
    conn.close()
