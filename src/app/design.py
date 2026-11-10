"""Shared design system for the six screens: palette, styles and small HTML helpers.

Values follow the MVP design on the Miro board (the Overview and Competitor coverage HTML
frames): Arial text at 11px, page background #F4F6F8, white bordered boxes with 8px radius,
navy header band, 10px tables, 12px section headings, 9px notes. Purple marks hypotheses,
green verified items, amber signals and items not yet complete.
"""

from __future__ import annotations

import streamlit as st

NAVY = "#0F2A3A"
BLUE = "#1E4257"
BACKGROUND = "#F4F6F8"
TEXT = "#1B2430"
MUTED = "#6B7A88"
BORDER = "#E2E7EC"
ROW_LINE = "#EEF1F4"

CSS = f"""
<style>
/* Text as in the MVP design: Arial, 11px base. */
html, body, .stApp, .stApp p, .stApp td, .stApp th, .stApp li, .stApp span, .stApp div {{
  font-family: Arial, sans-serif;
}}
.stApp {{background: {BACKGROUND}; color: {TEXT};}}
/* Keep the header: it holds the screen navigation. Hide Streamlit's own menu and decoration. */
header[data-testid="stHeader"] {{background: #FFFFFF; border-bottom: 1px solid {BORDER};}}
/* Hide the menu and Deploy button only: hiding stToolbar itself also removes the page links. */
[data-testid="stAppDeployButton"], [data-testid="stMainMenu"],
[data-testid="stDecoration"], [data-testid="stStatusWidget"] {{display: none !important;}}
footer {{visibility: hidden;}}
.block-container {{padding-top: 3.6rem !important; padding-bottom: 0 !important;
  padding-left: 12px !important; padding-right: 12px !important;}}
div[data-testid="stHorizontalBlock"] {{gap: 8px !important;}}
div[data-testid="stVerticalBlock"] {{gap: 8px !important;}}
div[data-testid="stMarkdownContainer"] {{margin-bottom: 0 !important;}}
/* Boxes: each block sits in a white bordered box, as in the MVP. */
div[data-testid="stVerticalBlockBorderWrapper"] > div {{
  background: #FFFFFF; border: 1px solid {BORDER}; border-radius: 8px; padding: 6px 8px;
}}
.sec {{font-size: 12px; font-weight: 700; color: {TEXT}; margin: 0 0 4px 0; line-height: 1.2;}}
.ttl {{font-size: 15px; font-weight: 700; margin: 0; line-height: 1.2;}}
/* !important: Streamlit styles markdown paragraphs with a more specific selector. */
.note {{font-size: 9px !important; color: {MUTED}; margin: 2px 0 0 0 !important; line-height: 1.3;}}
div[data-testid="stMetricValue"] {{font-size: 15px !important;}}
div[data-testid="stMetricLabel"] p {{font-size: 9px !important; color: {MUTED};}}
div[data-testid="stMetricDelta"] {{font-size: 9px !important;}}
table.c {{border-collapse: collapse; width: 100%; font-size: 10px; margin: 0;}}
table.c.auto {{width: auto;}}
table.cov {{width: auto; font-size: 10px;}}
table.cov th, table.cov td {{text-align: center; padding: 2px 3px;
  border-top: 1px solid {ROW_LINE};}}
table.cov td:first-child, table.cov th:first-child {{text-align: left; white-space: nowrap;}}
table.cov th.rg {{font-size: 9px; font-weight: 700; text-transform: uppercase;}}
/* Region groups: a divider before each region (columns 2, 8, 14, 20). */
table.cov td:nth-child(6n+2), table.cov th:nth-child(6n+2), table.cov th.rg {{
  border-left: 1px solid #C9D2DA; padding-left: 8px;
}}
.partial {{color: #7A5A00; font-weight: 700; background: #FFE58A;
  padding: 0 3px; border-radius: 3px;}}
.tc {{color: {MUTED}; border: 1px dashed #9AA5B1; border-radius: 3px; padding: 0 4px;}}
table.c th {{text-align: left; color: {MUTED}; font-size: 9px; font-weight: 600;
  padding: 2px 3px; border-bottom: 1px solid {BORDER};}}
table.c td {{padding: 2px 3px; border-top: 1px solid {ROW_LINE}; white-space: nowrap;}}
table.c td.n, table.c th.n {{text-align: right;}}
.good, table.c td.good {{background: #E6F4EC; color: #1E6B45; font-weight: 700;}}
.weak, table.c td.weak {{background: #FBEAEA; color: #B23A2C; font-weight: 700;}}
.muted {{color: {MUTED};}}
.nw {{font-size: 9.5px !important; line-height: 1.3; margin: 0 0 4px 0; padding-top: 3px;
  border-top: 1px solid {ROW_LINE};}}
.nw a {{color: #1B5E9E; text-decoration: none;}}
.hyp {{font-size: 10px !important; line-height: 1.3; margin: 2px 0; color: #24414F;}}
.hdr {{background: {NAVY}; color: #FFFFFF; padding: 8px 14px; border-radius: 4px;
  margin-bottom: 6px;}}
.hdr .t {{font-size: 15px; font-weight: 700; line-height: 1.2;}}
.hdr .s {{font-size: 10px; color: #A9C1CF; line-height: 1.2;}}
.card {{background: #FFFFFF; border: 1px solid {BORDER}; border-radius: 8px;
  padding: 6px 8px; margin-bottom: 4px;}}
.badge {{display: inline-block; font-size: 8px; font-weight: 700; padding: 0 4px;
  border-radius: 6px; text-transform: uppercase; letter-spacing: 0.2px; vertical-align: middle;}}
.b-fact {{background: #E6F4EC; color: #1E6B45;}}
.b-signal {{background: #FFF4D6; color: #7A5A00;}}
.b-hyp {{background: #F1E9FB; color: #5B2E91;}}
.b-pending {{background: #EEF1F4; color: {MUTED};}}
.pending {{font-size: 10px; color: {MUTED}; border: 1px dashed #C9D2DA; border-radius: 6px;
  padding: 6px 8px; background: #FAFBFC;}}
.navlabel {{font-size: 9px; color: {MUTED};}}
/* MVP coverage look: note banner, region cards, boxed marks, tinted matrix bands. */
.banner {{background: #FFF4D6; border: 1px solid #F0D68A; color: #7A5A00; border-radius: 6px;
  padding: 6px 10px; font-size: 10.5px; font-weight: 600; margin-bottom: 6px;}}
.rcs {{display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-bottom: 8px;}}
.rc {{border: 1px solid; border-radius: 10px; padding: 8px 10px;}}
.rt {{font-size: 11px; font-weight: 700; text-transform: uppercase;}}
.rn {{font-size: 10px; color: #3A4A58; margin-top: 2px;}}
.big {{font-size: 18px; font-weight: 700; line-height: 1.1;}}
.rs {{font-size: 9.5px; color: {MUTED}; margin-top: 3px;}}
.mk {{display: inline-flex; align-items: center; justify-content: center;
  width: 24px; height: 15px;
  border-radius: 3px; font-style: normal; font-size: 10.5px; font-weight: 700;
  box-sizing: border-box;
  vertical-align: middle;}}
.mk.M {{background: #D7EFC2; border: 1px solid #6BA33F; color: #2F6B1E;}}
.mk.P {{background: #FFE58A; border: 1px dashed #E0A44A; color: #7A5A00;}}
.mk.N {{background: #FFFFFF; border: 1px dashed #E08A80; color: #B23A2C;}}
.mk.u {{background: #F1F3F5; border: 1px dashed #9AA5B1; color: {MUTED};}}
table.cov {{border-collapse: separate; border-spacing: 0; width: 100%; font-size: 10.5px;}}
table.cov th {{font-size: 9px; color: {MUTED}; text-transform: uppercase;
  padding: 2px 4px;}}
table.cov td {{padding: 3px 4px; border-top: 1px solid {ROW_LINE}; text-align: center;}}
table.cov td:first-child, table.cov th:first-child {{
  text-align: left; white-space: nowrap; font-weight: 600;}}
table.cov td.r0 {{background: #F1FAF5;}} table.cov td.r1 {{background: #F2F7FD;}}
table.cov td.r2 {{background: #F6F4FC;}} table.cov td.r3 {{background: #FDF8F0;}}
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
