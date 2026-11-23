"""Shared display components: the status chip and the empty state.

Used by the screens instead of each screen keeping its own copy of the markup.
"""

from __future__ import annotations

import streamlit as st


def status_chip(text: str, bg: str, fg: str) -> str:
    """A status chip: a short coloured label (a date status, a level). Returns HTML."""
    return (
        f"<span style='background:{bg};color:{fg};padding:1px 6px;border-radius:8px;"
        f"font-weight:600;white-space:nowrap'>{text}</span>"
    )


def empty_state(message: str) -> None:
    """Shown in a tile that has no rows to list. It says why, and never shows a value."""
    st.markdown(f"<div class='t-meta'>{message}</div>", unsafe_allow_html=True)
