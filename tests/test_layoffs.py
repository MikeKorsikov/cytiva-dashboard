"""Layoffs tile and peer order on the Overview. No network: curated rows only."""

from src.ingest import store
from src.ingest.layoffs import LAYOFFS, load_layoffs
from src.metrics import overview


def test_every_mark_has_a_source_and_a_known_value():
    for _company, year, mark, url, note in LAYOFFS:
        assert url.startswith("https://")
        assert mark in {"Yes", "No", "Unknown"}
        assert note
        assert 2024 <= year <= 2026


def test_no_company_year_is_entered_twice():
    keys = [(c, y) for c, y, *_ in LAYOFFS]
    assert len(keys) == len(set(keys))


def test_layoff_marks_follow_peer_order(tmp_path):
    conn = store.connect(tmp_path / "app.db")
    store.create_schema(conn)
    run_id = store.start_run(conn, "manual")
    assert load_layoffs(conn, run_id) == len(LAYOFFS)
    names = [row["company"] for row in overview.layoff_marks(conn)]
    assert names == sorted(names, key=lambda n: overview.PEER_ORDER.index(n))
    thermo = next(r for r in overview.layoff_marks(conn) if r["company"] == "Thermo Fisher")
    assert thermo["years"][2026]["mark"] == "Yes"


def test_peer_order_is_largest_to_smallest_by_revenue():
    # FY2025 revenue in USD, $m: Thermo Fisher 44,556; Merck KGaA 24,588; Danaher 24,568;
    # Avantor 6,552; Sartorius 4,123; Repligen 738.
    assert overview.PEER_ORDER[:6] == (
        "Thermo Fisher",
        "Merck KGaA",
        "Danaher",
        "Avantor",
        "Sartorius",
        "Repligen",
    )
