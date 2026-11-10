"""Tile 3 on the Competitor coverage screen: bioprocessing market size and share.

Two flat donut charts (narrow and broad market definitions), a growth bar chart, a Merck
toggle, warnings for missing or not-disclosed inputs, and a sources and definitions table.
Every number comes from the app database with its source URL. Nothing is estimated here.
"""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from src.app.design import section
from src.metrics import market_share as ms

COLOURS = {
    "Danaher": "#1E3F73",
    "Sartorius": "#6BA33F",
    "Merck KGaA": "#B07A1E",
    "Repligen": "#7A5AB0",
    "Others": "#C9D1D9",
}
TITLES = {
    "narrow_company_defined": "Narrow market (~$20bn+, company-defined)",
    "broad_third_party": "Broad market ($48.1bn, third-party)",
}
CONFIDENCE_TEXT = {"H": "H (high)", "M": "M (medium)", "L": "L (low)"}


def _donut(view: ms.ShareView, scope: str) -> go.Figure | None:
    market = view.markets.get(scope)
    if market is None:
        return None
    labels, values, colours = [], [], []
    for s in view.suppliers:
        if s.usd_m is None:
            continue
        labels.append(s.company)
        values.append(s.usd_m)
        colours.append(COLOURS.get(s.company, "#888888"))
    labels.append("Others (incl. Thermo Fisher)")
    values.append(view.others_usd_m[scope])
    colours.append(COLOURS["Others"])
    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.55,
            marker={"colors": colours, "line": {"color": "white", "width": 1}},
            sort=False,
            textinfo="label+percent",
            texttemplate="%{label}<br>%{percent:.0%}<br>$%{value:,.0f}m",
            hovertemplate="%{label}<br>$%{value:,.0f} m<br>%{percent}<extra></extra>",
        )
    )
    fig.update_layout(
        title={"text": TITLES[scope], "font": {"size": 14}},
        showlegend=False,
        margin={"l": 10, "r": 10, "t": 50, "b": 10},
        height=380,
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def _growth_bar(view: ms.ShareView) -> go.Figure | None:
    rows = [g for g in view.growth if g.value is not None]
    if not rows:
        return None
    fig = go.Figure(
        go.Bar(
            x=[g.value for g in rows],
            y=[g.company for g in rows],
            orientation="h",
            marker={
                "color": [COLOURS.get(g.company, "#888888") for g in rows],
                "line": {"color": "white", "width": 0},
            },
            text=[f"+{g.value:.1f}% ({g.basis.replace('_', ' ')})" for g in rows],
            textposition="outside",
            hovertemplate="%{y}: %{x:.1f}%<extra></extra>",
        )
    )
    fig.update_layout(
        xaxis={"title": "FY2025 growth, %", "rangemode": "tozero"},
        yaxis={"autorange": "reversed"},
        margin={"l": 10, "r": 80, "t": 10, "b": 40},
        height=260,
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def _headline(view: ms.ShareView) -> str:
    danaher = next((s for s in view.suppliers if s.company == "Danaher"), None)
    narrow = danaher.share.get("narrow_company_defined") if danaher else None
    broad = danaher.share.get("broad_third_party") if danaher else None
    if narrow is None or broad is None:
        return "Danaher bioprocessing share: to collect"
    low, high = sorted([narrow, broad])
    return f"Danaher bioprocessing share: ~{low:.0f}% (broad) to ~{high:.0f}% (narrow), indicative"


def _sources_table(view: ms.ShareView) -> str:
    rows = [
        "| Input | Value | Confidence | Source |",
        "| --- | --- | --- | --- |",
    ]
    for s in view.suppliers:
        if s.source_url is None:
            continue
        value = "not disclosed" if s.usd_m is None else f"USD {s.usd_m:,.0f} m"
        extra = ""
        if s.fx_rate and s.fx_rate != 1.0:
            extra = f" (EUR at {s.fx_rate:.4f}, ECB 2025 average)"
        rows.append(
            f"| {s.company}: bioprocessing revenue, FY2025 ({s.value_kind}) | "
            f"{value}{extra} | {CONFIDENCE_TEXT.get(s.confidence or '', '-')} | "
            f"[link]({s.source_url}) |"
        )
    for g in view.growth:
        if g.source_url is None or g.value is None:
            continue
        rows.append(
            f"| {g.company}: growth, FY2025 ({g.basis.replace('_', ' ')}) | "
            f"+{g.value:.1f}% | {CONFIDENCE_TEXT.get(g.confidence or '', '-')} | "
            f"[link]({g.source_url}) |"
        )
    for scope, m in view.markets.items():
        rows.append(
            f"| Market: {TITLES[scope]} | USD {m.value_usd_bn:.1f} bn (base {m.base_year}) | "
            f"{CONFIDENCE_TEXT.get(m.confidence, '-')} | [link]({m.source_url}) |"
        )
    return "\n".join(rows)


def market_share_tile(revenue: list[dict], markets: list[dict]) -> None:
    """Render Tile 3. Called with the database rows; the Merck toggle recomputes the view."""
    section("Market size and share", "signal")
    st.markdown(
        "<span class='badge b-signal'>Indicative</span> "
        "<span class='note'>Supply-side shares. Numerator: bioprocessing revenue, not the "
        "Biotechnology segment.</span>",
        unsafe_allow_html=True,
    )
    include_merck = st.toggle("Include Merck KGaA (Process Solutions)", value=True)
    view = ms.build_view(revenue, markets, include_merck=include_merck)

    st.markdown(f"**{_headline(view)}**")
    for w in view.warnings:
        st.warning(w)

    left, right = st.columns(2)
    for col, scope in ((left, "narrow_company_defined"), (right, "broad_third_party")):
        with col:
            fig = _donut(view, scope)
            if fig is None:
                st.caption(f"{TITLES[scope]}: to collect")
            else:
                st.plotly_chart(fig, use_container_width=True)

    st.markdown("**FY2025 bioprocessing growth, by company**")
    bar = _growth_bar(view)
    if bar is None:
        st.caption("Growth figures: to collect")
    else:
        st.plotly_chart(bar, use_container_width=True)
    missing = [g.company for g in view.growth if g.value is None]
    caption = "Peers growing faster than Danaher = share loss."
    if missing:
        caption += f" To collect for: {', '.join(missing)}."
    st.caption(caption)

    with st.expander("Sources and definitions"):
        st.markdown(
            "**Numerator:** bioprocessing revenue reported by each supplier for FY2025. "
            "Danaher is at least $6bn (a floor, not an exact figure). Cytiva alone is not "
            "disclosed, so the tile shows Danaher bioprocessing (Cytiva and Pall)."
        )
        st.markdown(
            "**Denominator:** the supply-side market, which is the sum of the revenues shown. "
            "Unlisted suppliers are not in it. Others is the market minus the named suppliers, "
            "capped at zero. Thermo Fisher does not disclose bioproduction separately, so it "
            "is in Others."
        )
        st.markdown(
            "**Market definitions differ.** The narrow market is Repligen's company framing. "
            "The broad market is GMI's bioprocessing equipment market, which excludes "
            "consumables that the supplier revenues include."
        )
        st.markdown("**FX:** EUR converted at the ECB 2025 annual average (1.1300 USD per EUR).")
        st.markdown(_sources_table(view))
