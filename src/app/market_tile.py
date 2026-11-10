"""Tile 3 on the Competitor coverage screen: Danaher share of the market (MVP layout).

One pie chart. The values are SAMPLE values from the MVP mockup, not sourced data:
- Danaher numerator: USD 7.5 bn, Biotechnology segment (sample).
- Market size: USD 37.5 bn, derived, no source (sample).
Replace both with sourced data before release (CLAUDE.md, sample values).
"""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from src.app.design import section

SAMPLE_DANAHER_BN = 7.5  # Danaher Biotechnology segment, mockup sample
SAMPLE_MARKET_BN = 37.5  # market size, derived, no source
DANAHER_COLOUR = "#1E3F73"
REST_COLOUR = "#C9D1D9"


def share_pct() -> float:
    return SAMPLE_DANAHER_BN / SAMPLE_MARKET_BN * 100


def _pie() -> go.Figure:
    rest = SAMPLE_MARKET_BN - SAMPLE_DANAHER_BN
    fig = go.Figure(
        go.Pie(
            labels=["Danaher (Biotechnology, sample)", "Rest of market (sample)"],
            values=[SAMPLE_DANAHER_BN, rest],
            marker={
                "colors": [DANAHER_COLOUR, REST_COLOUR],
                "line": {"color": "white", "width": 1},
            },
            sort=False,
            textinfo="label+percent",
            texttemplate="%{label}<br>%{percent:.0%}<br>$%{value:.1f}bn",
            hovertemplate="%{label}<br>$%{value:.1f} bn<br>%{percent}<extra></extra>",
        )
    )
    fig.update_layout(
        showlegend=False,
        margin={"l": 10, "r": 10, "t": 10, "b": 10},
        height=360,
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def market_share_tile() -> None:
    """Render Tile 3: headline, one pie, and the sample-value note."""
    section("Market size and share", "signal")
    st.markdown(
        f"**Danaher share of the market: ~{share_pct():.0f}%** "
        "<span class='badge b-signal'>Sample values</span>",
        unsafe_allow_html=True,
    )
    st.plotly_chart(_pie(), use_container_width=True)
