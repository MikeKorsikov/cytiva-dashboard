"""Bioprocessing share for the market share tile (Competitor coverage, Tile 3).

Share = company bioprocessing revenue (USD) / market size (USD), for two market definitions:
- narrow_company_defined: the company's own framing (Repligen, $20bn+, a floor).
- broad_third_party: GMI's bioprocessing equipment market ($48.1bn, equipment only).

Others = market minus the named suppliers. If the named suppliers add up to more than the
market (possible when the inputs are floors), Others is capped at 0 and a warning is shown.
A supplier with no disclosed figure (Thermo Fisher, not disclosed separately) is not given a
value: it stays in Others and the tile says so. A missing supplier is never dropped silently.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field

# Suppliers in the numerator and denominator, in tile order. Danaher is the subject.
SUPPLIERS = ("Danaher", "Sartorius", "Merck KGaA", "Repligen")
OUT_OF_NAMED = ("Thermo Fisher",)  # not disclosed separately: sits in Others
SCOPES = ("narrow_company_defined", "broad_third_party")
SUBJECT = "Danaher"


@dataclass
class Supplier:
    company: str
    usd_m: float | None
    value_kind: str | None
    confidence: str | None
    source_url: str | None
    disclosure: str | None
    fx_rate: float | None
    fx_source_url: str | None
    note: str | None
    share: dict[str, float | None] = field(default_factory=dict)  # per scope, in percent


@dataclass
class Growth:
    company: str
    value: float | None
    basis: str | None
    confidence: str | None
    source_url: str | None
    disclosure: str | None
    note: str | None


@dataclass
class Market:
    scope: str
    value_usd_bn: float
    value_kind: str
    confidence: str
    definition: str
    disclosure: str
    source_url: str
    source_title: str
    base_year: int
    note: str | None


@dataclass
class ShareView:
    suppliers: list[Supplier]
    growth: list[Growth]
    markets: dict[str, Market]
    others_usd_m: dict[str, float]  # per scope, after the cap
    others_share: dict[str, float]  # per scope, percent of market
    warnings: list[str]
    include_merck: bool


def _rows(conn: sqlite3.Connection, sql: str) -> list[dict]:
    cur = conn.execute(sql)
    names = [d[0] for d in cur.description]
    return [dict(zip(names, row, strict=True)) for row in cur.fetchall()]


def read_tile_inputs(conn: sqlite3.Connection) -> tuple[list[dict], list[dict]]:
    """Revenue rows and market rows, or empty lists when the tables are missing."""
    try:
        revenue = _rows(conn, "SELECT * FROM revenue_observation")
        markets = _rows(conn, "SELECT * FROM market_size")
    except sqlite3.OperationalError:
        return [], []
    return revenue, markets


def build_view(
    revenue: list[dict],
    markets: list[dict],
    include_merck: bool = True,
) -> ShareView:
    """The tile's numbers. Pure: no database access, so it can be tested directly."""
    warnings: list[str] = []
    by_company = {r["company_id"]: r for r in revenue if r["metric"] == "bioprocessing_revenue"}
    growth_rows = {r["company_id"]: r for r in revenue if r["metric"] == "bioprocessing_growth"}
    market_by_scope = {m["scope"]: m for m in markets}

    included = [c for c in SUPPLIERS if include_merck or c != "Merck KGaA"]
    suppliers: list[Supplier] = []
    for company in included:
        r = by_company.get(company)
        if r is None:
            warnings.append(f"{company}: no revenue row loaded; it is missing from the tile")
            suppliers.append(Supplier(company, None, None, None, None, None, None, None, None))
            continue
        usd = r["value_usd"] if r["value_kind"] != "not_disclosed" else None
        if usd is None and r["value_kind"] != "not_disclosed":
            warnings.append(f"{company}: revenue has no USD value")
        suppliers.append(
            Supplier(
                company=company,
                usd_m=usd,
                value_kind=r["value_kind"],
                confidence=r["confidence"],
                source_url=r["source_url"],
                disclosure=r["disclosure"],
                fx_rate=r["fx_rate"],
                fx_source_url=r["fx_source_url"],
                note=r["note"],
            )
        )

    for company in OUT_OF_NAMED:
        warnings.append(
            f"{company}: bioproduction is not disclosed separately, so it is counted in Others"
        )

    markets_out: dict[str, Market] = {}
    others_usd: dict[str, float] = {}
    others_share: dict[str, float] = {}
    for scope in SCOPES:
        m = market_by_scope.get(scope)
        if m is None:
            warnings.append(f"{scope}: no market size loaded")
            continue
        markets_out[scope] = Market(
            scope=scope,
            value_usd_bn=m["value_usd_bn"],
            value_kind=m["value_kind"],
            confidence=m["confidence"],
            definition=m["definition"],
            disclosure=m["disclosure"],
            source_url=m["source_url"],
            source_title=m["source_title"],
            base_year=m["base_year"],
            note=m["note"],
        )
        market_usd_m = m["value_usd_bn"] * 1000
        named_sum = 0.0
        for s in suppliers:
            s.share.setdefault(scope, None)
            if s.usd_m is not None:
                s.share[scope] = s.usd_m / market_usd_m * 100
                named_sum += s.usd_m
        raw = market_usd_m - named_sum
        if raw < 0:
            warnings.append(
                f"{scope}: named suppliers ({named_sum:,.0f} m) exceed the market size; "
                "Others is capped at 0 and shares are indicative"
            )
        others = max(0.0, raw)
        others_usd[scope] = others
        others_share[scope] = others / market_usd_m * 100

    growth: list[Growth] = []
    for company in included:
        g = growth_rows.get(company)
        if g is None:
            growth.append(Growth(company, None, None, None, None, None, "no growth row loaded"))
            continue
        value = g["value"] if g["value_kind"] != "not_disclosed" else None
        growth.append(
            Growth(
                company=company,
                value=value,
                basis=g["basis"],
                confidence=g["confidence"],
                source_url=g["source_url"],
                disclosure=g["disclosure"],
                note=g["note"],
            )
        )
    return ShareView(
        suppliers=suppliers,
        growth=growth,
        markets=markets_out,
        others_usd_m=others_usd,
        others_share=others_share,
        warnings=warnings,
        include_merck=include_merck,
    )


def view_from_db(conn: sqlite3.Connection, include_merck: bool = True) -> ShareView | None:
    """The tile's view from the app database, or None when no rows are loaded yet."""
    revenue, markets = read_tile_inputs(conn)
    if not revenue or not markets:
        return None
    return build_view(revenue, markets, include_merck=include_merck)


def sources(view: ShareView) -> list[tuple[str, str, str]]:
    """(input, value text, URL) for every number the tile shows, for the sources table."""
    rows = []
    for s in view.suppliers:
        if s.source_url is None:
            continue
        value = "not disclosed" if s.usd_m is None else f"USD {s.usd_m:,.0f} m"
        rows.append((f"{s.company}: bioprocessing revenue ({s.value_kind})", value, s.source_url))
    for m in view.markets.values():
        rows.append((f"Market: {m.definition}", f"USD {m.value_usd_bn:.1f} bn", m.source_url))
    return rows
