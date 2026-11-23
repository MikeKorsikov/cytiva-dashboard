"""Tile 3 on the Competitor coverage screen: Danaher share of the bioprocessing market.

Shell only. No figure is shown until it is sourced: the Danaher bioprocessing revenue (not yet
found in a primary filing) and a sourced market size. Mockup values are not used in the app.
"""

from __future__ import annotations

import streamlit as st

from src.app.design import placeholder, section
from src.app.ui.evidence import Evidence, evidence_button


def market_share_tile() -> None:
    """Render Tile 3 as a shell: the title and what it will show, with no values."""
    section("Market size and share", "signal")
    st.markdown(
        "<div class='lb'>Danaher bioprocessing share</div><div class='big'>to collect</div>",
        unsafe_allow_html=True,
    )
    placeholder(
        "Needs two sourced figures: Danaher bioprocessing revenue (primary filing, not yet found) "
        "and a sourced market size with its scope. Peers' bioprocessing revenue is in the "
        "coverage research. No sample values are shown."
    )
    evidence_button(
        "cov-market",
        "Market size and share",
        [
            Evidence(
                row="Danaher bioprocessing revenue",
                shown="to collect",
                label="To collect",
            ),
            Evidence(row="Sourced market size and scope", shown="to collect", label="To collect"),
        ],
    )
