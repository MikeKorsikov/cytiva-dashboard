"""Shared design system for the six screens: palette, styles and small HTML helpers.

Palette follows the Miro design: navy header, white cards, light background, purple for
hypotheses, green for verified items, amber for signals and items not yet complete.
"""

from __future__ import annotations

import streamlit as st

NAVY = "#0F2A3A"
BLUE = "#1E4257"
BACKGROUND = "#F4F6F8"
TEXT = "#1B2430"
MUTED = "#6B7A88"
BORDER = "#E2E7EC"

CSS = f"""
<style>
/* Keep the header: it holds the screen navigation. Hide Streamlit's own menu and decoration. */
header[data-testid="stHeader"] {{background: #FFFFFF; border-bottom: 1px solid {BORDER};}}
/* Hide the menu and Deploy button only: hiding stToolbar itself also removes the page links. */
[data-testid="stAppDeployButton"], [data-testid="stMainMenu"],
[data-testid="stDecoration"], [data-testid="stStatusWidget"] {{display: none !important;}}
footer {{visibility: hidden;}}
.block-container {{padding-top: 3.6rem !important; padding-bottom: 0 !important;}}
div[data-testid="stHorizontalBlock"] {{gap: 0.5rem !important;}}
div[data-testid="stVerticalBlock"] {{gap: 0.4rem !important;}}
div[data-testid="stMarkdownContainer"] {{margin-bottom: 0 !important;}}
.sec {{font-size: 0.85rem; font-weight: 700; color: {TEXT};
  margin: 0.3rem 0 0.1rem 0; line-height: 1.2;}}
.ttl {{font-size: 1.15rem; font-weight: 700; margin: 0; line-height: 1.2;}}
div[data-testid="stMetricValue"] {{font-size: 1.1rem !important;}}
div[data-testid="stMetricLabel"] p {{font-size: 0.7rem !important;}}
div[data-testid="stMetricDelta"] {{font-size: 0.7rem !important;}}
/* !important: Streamlit styles markdown paragraphs with a more specific selector. */
.note {{font-size: 0.7rem !important; color: {MUTED}; margin: 0; line-height: 1.2;}}
table.c {{border-collapse: collapse; width: 100%; font-size: 0.8rem; margin: 0;}}
table.c.auto {{width: auto;}}
table.c th {{text-align: left; color: {MUTED}; font-weight: 600;
  border-bottom: 1px solid {BORDER}; padding: 2px 5px;}}
table.c td {{padding: 2px 5px; border-bottom: 1px solid #EEF1F4; white-space: nowrap;}}
table.c td.n, table.c th.n {{text-align: right;}}
.good {{background: #E6F4EC; color: #1E6B45; font-weight: 600;}}
.weak {{background: #FBEAEA; color: #B23A2C; font-weight: 600;}}
.muted {{color: {MUTED};}}
.nw {{font-size: 0.72rem !important; line-height: 1.3; margin: 0 0 0.35rem 0;}}
.nw a {{color: #1B5E9E; text-decoration: none;}}
.hyp {{font-size: 0.75rem !important; line-height: 1.3; margin: 0.15rem 0;}}
.hdr {{background: {NAVY}; color: #FFFFFF; padding: 6px 10px; border-radius: 4px;
  margin-bottom: 4px;}}
.hdr .t {{font-size: 1.0rem; font-weight: 700; line-height: 1.2;}}
.hdr .s {{font-size: 0.68rem; color: #A9C1CF; line-height: 1.2;}}
.card {{background: #FFFFFF; border: 1px solid {BORDER}; border-radius: 8px;
  padding: 6px 8px; margin-bottom: 4px;}}
.badge {{display: inline-block; font-size: 0.55rem; font-weight: 700; padding: 0 5px;
  border-radius: 6px; text-transform: uppercase; letter-spacing: 0.2px; vertical-align: middle;}}
.b-fact {{background: #E6F4EC; color: #1E6B45;}}
.b-signal {{background: #FFF4D6; color: #7A5A00;}}
.b-hyp {{background: #F1E9FB; color: #5B2E91;}}
.b-pending {{background: #EEF1F4; color: {MUTED};}}
.pending {{font-size: 0.7rem; color: {MUTED}; border: 1px dashed #C9D2DA; border-radius: 6px;
  padding: 6px 8px; background: #FAFBFC;}}
.navlabel {{font-size: 0.65rem; color: {MUTED};}}
</style>
"""

BADGES = {"fact": "Fact", "signal": "Signal", "hyp": "Hypothesis", "pending": "To collect"}


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def header(title: str, subtitle: str) -> None:
    st.markdown(
        f"<div class='hdr'><div class='t'>{title}</div><div class='s'>{subtitle}</div></div>",
        unsafe_allow_html=True,
    )


def section(title: str, kind: str | None = None) -> None:
    """Section title with an optional evidence badge."""
    badge = f" <span class='badge b-{kind}'>{BADGES[kind]}</span>" if kind else ""
    st.markdown(f"<div class='sec'>{title}{badge}</div>", unsafe_allow_html=True)


def note(text: str) -> None:
    st.markdown(f"<p class='note'>{text}</p>", unsafe_allow_html=True)


def placeholder(text: str) -> None:
    """Visible marker for content that is not loaded yet. Never shows an estimate."""
    st.markdown(f"<div class='pending'>{text}</div>", unsafe_allow_html=True)


def hypothesis(text: str) -> None:
    st.markdown(f"<p class='hyp'><b>Hypothesis:</b> {text}</p>", unsafe_allow_html=True)
