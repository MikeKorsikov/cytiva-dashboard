"""Market share tile (Competitor coverage, Tile 3): seed rows, FX, share maths, Others cap,
Merck toggle, missing and not-disclosed inputs, growth. No network."""

from src.ingest import bioprocess_share as seed
from src.ingest import store
from src.metrics import market_share as ms


def _rev(company, value_usd, kind="reported", metric="bioprocessing_revenue", **extra):
    row = {
        "company_id": company,
        "metric": metric,
        "fiscal_period": "FY2025",
        "value": value_usd,
        "currency": "USD",
        "value_usd": value_usd,
        "fx_rate": 1.0,
        "fx_source_url": None,
        "value_kind": kind,
        "basis": None,
        "disclosure": "test disclosure",
        "confidence": "H",
        "source_url": "https://example.com/source",
        "note": None,
    }
    row.update(extra)
    return row


def _market(scope, bn, kind="reported"):
    return {
        "scope": scope,
        "base_year": 2025,
        "value_usd_bn": bn,
        "value_kind": kind,
        "confidence": "M",
        "definition": f"{scope} definition",
        "disclosure": "test",
        "source_title": "test",
        "source_url": "https://example.com/market",
        "note": None,
    }


def _rows(**usd):
    """Revenue rows for the four named suppliers with the given USD millions."""
    out = []
    for company, value in usd.items():
        out.append(_rev(company.replace("_", " "), value))
    return out


# --- Seed rows -----------------------------------------------------------------


def test_seed_rows_pass_validation():
    assert seed.validate_all() == []


def test_every_seed_row_has_a_source_url():
    for row in seed.REVENUE_OBSERVATIONS:
        assert row[10].startswith("https://"), row[0]
    for row in seed.MARKET_SIZES:
        assert row[8].startswith("https://"), row[0]


def test_forecast_year_denominator_is_rejected():
    row = ("broad_third_party", 2026, 60.0, "reported", "d", "M", "x", "t", "https://e.com", None)
    assert any("forecast" in p for p in seed.validate_market(row))


def test_missing_source_url_is_rejected():
    row = (
        "Sartorius",
        "bioprocessing_revenue",
        "FY2025",
        2865,
        "EUR",
        "reported",
        None,
        "H",
        "text",
        "title",
        "",
        1.13,
        seed.ECB_FX_SOURCE,
        None,
    )
    assert any("no source URL" in p for p in seed.validate_revenue(row))


def test_not_disclosed_row_must_not_carry_a_number():
    row = (
        "Thermo Fisher",
        "bioprocessing_revenue",
        "FY2025",
        5000,
        "USD",
        "not_disclosed",
        None,
        "L",
        "text",
        "title",
        "https://e.com",
        None,
        None,
        None,
    )
    assert any("must not carry a value" in p for p in seed.validate_revenue(row))


def test_non_usd_value_needs_an_fx_rate_and_source():
    row = (
        "Sartorius",
        "bioprocessing_revenue",
        "FY2025",
        2865,
        "EUR",
        "reported",
        None,
        "H",
        "text",
        "title",
        "https://e.com",
        None,
        None,
        None,
    )
    assert any("FX rate" in p for p in seed.validate_revenue(row))


# --- FX and storage ------------------------------------------------------------


def test_sartorius_is_converted_at_the_ecb_2025_average(tmp_path):
    conn = store.connect(tmp_path / "app.db")
    store.create_schema(conn)
    run_id = store.start_run(conn, "manual")
    seed.load_bioprocess_share(conn, run_id)
    revenue, markets = ms.read_tile_inputs(conn)
    sartorius = next(
        r
        for r in revenue
        if r["company_id"] == "Sartorius" and r["metric"] == "bioprocessing_revenue"
    )
    assert sartorius["fx_rate"] == seed.FX_EUR_2025 == 1.13
    assert sartorius["value_usd"] == round(2865 * 1.13, 2)
    assert len(markets) == 2


def test_every_stored_number_has_a_source_url(tmp_path):
    conn = store.connect(tmp_path / "app.db")
    store.create_schema(conn)
    run_id = store.start_run(conn, "manual")
    seed.load_bioprocess_share(conn, run_id)
    revenue, markets = ms.read_tile_inputs(conn)
    for r in revenue + markets:
        if r.get("value") is not None or r.get("value_usd_bn") is not None:
            assert r["source_url"], r
    assert (
        conn.execute(
            "SELECT COUNT(*) FROM revenue_observation "
            "WHERE value IS NOT NULL AND source_url IS NULL"
        ).fetchone()[0]
        == 0
    )


# --- Share maths ---------------------------------------------------------------


def test_danaher_share_is_its_revenue_over_the_market():
    view = ms.build_view(
        _rows(Danaher=6000, Sartorius=3000, Merck_KGaA=4000, Repligen=738),
        [_market("narrow_company_defined", 20.0), _market("broad_third_party", 48.1)],
    )
    danaher = next(s for s in view.suppliers if s.company == "Danaher")
    assert abs(danaher.share["narrow_company_defined"] - 30.0) < 1e-9
    assert abs(danaher.share["broad_third_party"] - 6000 / 48100 * 100) < 1e-9


def test_others_is_the_market_minus_named_suppliers():
    view = ms.build_view(
        _rows(Danaher=6000, Sartorius=3000, Merck_KGaA=4000, Repligen=738),
        [_market("narrow_company_defined", 20.0)],
    )
    assert abs(view.others_usd_m["narrow_company_defined"] - (20000 - 13738)) < 1e-9


def test_others_is_capped_at_zero_with_a_warning():
    view = ms.build_view(
        _rows(Danaher=6000, Sartorius=9000, Merck_KGaA=5000, Repligen=738),
        [_market("narrow_company_defined", 20.0)],
    )
    assert view.others_usd_m["narrow_company_defined"] == 0.0
    assert any("capped at 0" in w for w in view.warnings)


def test_merck_toggle_changes_the_named_set_and_others():
    rows = _rows(Danaher=6000, Sartorius=3000, Merck_KGaA=4000, Repligen=738)
    markets = [_market("broad_third_party", 48.1)]
    on = ms.build_view(rows, markets, include_merck=True)
    off = ms.build_view(rows, markets, include_merck=False)
    assert "Merck KGaA" in [s.company for s in on.suppliers]
    assert "Merck KGaA" not in [s.company for s in off.suppliers]
    assert off.others_usd_m["broad_third_party"] > on.others_usd_m["broad_third_party"]


def test_missing_supplier_is_warned_not_silently_dropped():
    rows = _rows(Danaher=6000, Sartorius=3000, Repligen=738)  # Merck row missing
    view = ms.build_view(rows, [_market("broad_third_party", 48.1)])
    assert any("Merck KGaA" in w for w in view.warnings)
    merck = next(s for s in view.suppliers if s.company == "Merck KGaA")
    assert merck.usd_m is None


def test_thermo_is_not_given_a_value_and_stays_in_others():
    rows = _rows(Danaher=6000, Sartorius=3000, Merck_KGaA=4000, Repligen=738)
    view = ms.build_view(rows, [_market("broad_third_party", 48.1)])
    assert "Thermo Fisher" not in [s.company for s in view.suppliers]
    assert any("Thermo Fisher" in w and "Others" in w for w in view.warnings)


def test_at_least_value_is_used_as_a_floor_and_flagged():
    rows = _rows(Repligen=738) + [_rev("Danaher", 6000, kind="at_least")]
    view = ms.build_view(rows, [_market("narrow_company_defined", 20.0, kind="at_least")])
    danaher = next(s for s in view.suppliers if s.company == "Danaher")
    assert danaher.value_kind == "at_least"
    assert danaher.share["narrow_company_defined"] == 30.0


# --- Growth -------------------------------------------------------------------


def test_growth_is_not_invented_for_danaher():
    rows = _rows(Repligen=738) + [
        _rev("Danaher", None, kind="not_disclosed", metric="bioprocessing_growth"),
        _rev("Sartorius", 9.5, metric="bioprocessing_growth", basis="constant_currency"),
    ]
    view = ms.build_view(rows, [_market("broad_third_party", 48.1)])
    danaher = next(g for g in view.growth if g.company == "Danaher")
    sartorius = next(g for g in view.growth if g.company == "Sartorius")
    assert danaher.value is None
    assert sartorius.value == 9.5 and sartorius.basis == "constant_currency"


def test_no_rows_means_no_view(tmp_path):
    conn = store.connect(tmp_path / "empty.db")
    store.create_schema(conn)
    assert ms.view_from_db(conn) is None
