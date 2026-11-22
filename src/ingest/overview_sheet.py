"""Screen 1 (overview) from the research sheet: peer financials (T1), the share-price list (T3),
competitor news (T4), implications (T5) and the attention items (Attention tab).

Every tab is read through its section map (sheet_headers.OVERVIEW_TABS). Labels follow one rule:

- Peer financials and news: Fact where the row's confidence is H and its first source is a
  primary document (company filing, release or official source). Otherwise Signal. A row
  keeps the sheet's own confidence and source URL.
- Implications: Hypothesis, always.
- Attention items: the sheet's own label (FACT, SIGNAL or HYPOTHESIS), shown as Fact, Signal or
  Hypothesis.
- Share prices: the sheet holds no values (the price feed fills them). Rows are stored with the
  state "awaiting feed".

A row without a source URL is rejected by store.upsert (financials and news).
"""

from __future__ import annotations

import re
import sqlite3

from src.ingest import store
from src.ingest.sheet_headers import DATA_ROOT, read_tab

SHEET_DIR = DATA_ROOT / "overview" / "sheet"
NOT_AVAILABLE = {"", "n/d", "NA", "-"}
ATTENTION_LABELS = {"FACT": "Fact", "SIGNAL": "Signal", "HYPOTHESIS": "Hypothesis"}


def num(text: str | None) -> float | None:
    """A sheet number: "24,568.0", "59.1135%", "-530.2". Blanks and n/d are None."""
    if text is None or text.strip() in NOT_AVAILABLE:
        return None
    return float(text.replace(",", "").replace("%", "").replace("$", "").strip())


def first_source(source_ids: str) -> str:
    """The first Source ID of a row ("S05, S06" gives S05)."""
    ids = [i.strip() for i in re.split(r"[,;]", source_ids) if i.strip()]
    return ids[0] if ids else ""


def row_label(confidence: str, source_type: str) -> str:
    """Fact when H and the first source is primary; otherwise Signal."""
    return "Fact" if confidence == "H" and source_type.startswith("Primary") else "Signal"


def _sources() -> dict[str, tuple[str, str]]:
    rows = read_tab(SHEET_DIR / "sources.csv").rows["source"]
    return {r["id"]: (r["url"], r["type"]) for r in rows if re.fullmatch(r"S\d{2}", r["id"])}


def _clear(conn: sqlite3.Connection) -> None:
    for table in ("ov_financial", "ov_price", "ov_news", "ov_implication", "ov_attention"):
        conn.execute(f"DELETE FROM {table}")


def load_financials(conn: sqlite3.Connection, run_id: int, sources: dict) -> int:
    written = 0
    for r in read_tab(SHEET_DIR / "t1_peer_financials.csv").rows["financials"]:
        if not re.fullmatch(r"PF-\d+", r["id"]):
            continue
        sid = first_source(r["source_ids"])
        if sid not in sources:
            raise ValueError(f"{r['id']}: source {sid!r} is not in the Overview Sources tab")
        url, source_type = sources[sid]
        revenue_local = num(r["revenue_m"])
        revenue_usd = num(r["revenue_usd_m"])
        fcf_local = num(r["free_cash_flow_m"])
        fields = {
            "id": r["id"],
            "company": r["company"],
            "ticker": r["ticker"],
            "fiscal_year": r["fy"],
            "currency": r["currency"],
            "revenue_local_m": revenue_local,
            "growth_reported_pct": num(r["revenue_growth_reported_pct"]),
            "organic_growth_pct": num(r["organic_growth_pct"]),
            "gross_profit_local_m": num(r["gross_profit_m"]),
            "net_income_local_m": num(r["net_income_m"]),
            "operating_cash_flow_local_m": num(r["operating_cash_flow_m"]),
            "free_cash_flow_local_m": fcf_local,
            "revenue_usd_m": revenue_usd,
            "gross_margin_pct": num(r["gross_margin_pct"]),
            "net_margin_pct": num(r["net_margin_pct"]),
            "fcf_margin_pct": num(r["fcf_margin_pct"]),
            "source_ids": r["source_ids"],
            "confidence": r["confidence"],
            "notes": r["notes"],
        }
        row = {
            **fields,
            "source_url": url,
            "source_type": "document",
            "published_date": None,
            "evidence_label": row_label(r["confidence"], source_type),
        }
        if store.upsert(conn, run_id, "ov_financial", row) != "rejected":
            written += 1
    return written


def load_prices(conn: sqlite3.Connection, run_id: int) -> int:
    """The price list. The sheet's values are blank (the feed fills them), so each row is
    stored as awaiting feed. Nothing is estimated."""
    written = 0
    for r in read_tab(SHEET_DIR / "t3_share_prices.csv").rows["prices"]:
        if not re.fullmatch(r"SP-\d+", r["id"]):
            continue
        conn.execute(
            "INSERT INTO ov_price (id, company, ticker, exchange, currency, last_close, "
            "close_date, change_12m_pct, low_52w, high_52w, refresh_rule, state, source_url, "
            "source_type, evidence_label, loaded_at, verification_status) VALUES "
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'awaiting feed', '', 'document', 'Fact', ?, "
            "'passed')",
            (
                r["id"],
                r["company"],
                r["ticker"],
                r["exchange"],
                r["currency"],
                num(r["last_close"]),
                r["close_date"] or None,
                num(r["change_12m_pct"]),
                num(r["low_52w"]),
                num(r["high_52w"]),
                r["refresh"],
                store.now_iso(),
            ),
        )
        written += 1
    return written


def load_news(conn: sqlite3.Connection, run_id: int) -> int:
    written = 0
    for r in read_tab(SHEET_DIR / "t4_competitor_news.csv").rows["news"]:
        if not re.fullmatch(r"CN-\d+", r["id"]):
            continue
        # Company-issued items with high confidence are Fact; trade press is Signal.
        label = (
            "Fact"
            if r["confidence"] == "H" and r["source_type"].startswith("Company")
            else "Signal"
        )
        row = {
            "id": r["id"],
            "company": r["company"],
            "feed": r["feed"],
            "search_query": r["search_query"],
            "headline": r["headline"],
            "item_date": r["date"],
            "tag": r["tag"],
            "source_kind": r["source_type"],
            "confidence": r["confidence"],
            "source_url": r["url"],
            "source_type": "news",
            "published_date": r["date"],
            "evidence_label": label,
        }
        if store.upsert(conn, run_id, "ov_news", row) != "rejected":
            written += 1
    return written


def load_implications(conn: sqlite3.Connection, run_id: int) -> int:
    written = 0
    for r in read_tab(SHEET_DIR / "t5_implications.csv").rows["implications"]:
        if not re.fullmatch(r"I-\d+", r["id"]):
            continue
        row = {
            "id": r["id"],
            "hypothesis": r["hypothesis"],
            "based_on": r["based_on"],
            "confirm_or_refute": r["confirm_or_refute"],
            "area": r["area"],
            "confidence": r["confidence"],
            "source_url": "",
            "source_type": "curated",
            "published_date": None,
            "evidence_label": "Hypothesis",
        }
        if store.upsert(conn, run_id, "ov_implication", row) != "rejected":
            written += 1
    return written


def load_attention(conn: sqlite3.Connection, run_id: int) -> int:
    written = 0
    for r in read_tab(SHEET_DIR / "attention.csv").rows["attention"]:
        if not re.fullmatch(r"AT-\d+", r["id"]):
            continue
        if r["action"] not in ("ACT", "MONITOR"):
            raise ValueError(f"{r['id']}: action {r['action']!r} is not ACT or MONITOR")
        label = ATTENTION_LABELS.get(r["evidence_label"].upper())
        if label is None:
            raise ValueError(f"{r['id']}: evidence label {r['evidence_label']!r} is not known")
        conn.execute(
            "INSERT INTO ov_attention (id, issue, action, why_it_matters, key_fact, "
            "detail_lives_in, source_text, review_by, source_url, source_type, evidence_label, "
            "loaded_at, verification_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, '', 'curated', ?, ?, "
            "'passed')",
            (
                r["id"],
                r["issue"],
                r["action"],
                r["why_it_matters"],
                r["key_fact"],
                r["detail_lives_in"],
                r["source"],
                r["review_by"],
                label,
                store.now_iso(),
            ),
        )
        written += 1
    return written


def load_overview_sheet(conn: sqlite3.Connection, run_id: int) -> int:
    """Load the screen 1 tables from the sheet. Clears them first, so the database holds exactly
    what the sheet holds. Returns the number of rows accepted."""
    sources = _sources()
    _clear(conn)
    written = load_financials(conn, run_id, sources)
    written += load_prices(conn, run_id)
    written += load_news(conn, run_id)
    written += load_implications(conn, run_id)
    written += load_attention(conn, run_id)
    conn.commit()
    return written
