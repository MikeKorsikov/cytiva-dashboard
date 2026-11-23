"""Shared design system for the six screens: palette, styles and small HTML helpers.

Values follow the MVP design on the Miro board (the Overview and Competitor coverage HTML
frames): Arial text at 11px, page background #F4F6F8, white bordered boxes with 8px radius,
navy header band, 10px tables, 12px section headings, 9px notes. Purple marks hypotheses,
green verified items, amber signals and items not yet complete.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator
from contextlib import contextmanager

import streamlit as st

from src.domain.confidence import FACT as FACT_LABEL
from src.domain.confidence import FACT_AND_SIGNAL as FACT_AND_SIGNAL_LABEL
from src.domain.confidence import HYPOTHESIS as HYPOTHESIS_LABEL
from src.domain.confidence import SIGNAL as SIGNAL_LABEL
from src.domain.confidence import UNCONFIRMED as UNCONFIRMED_LABEL
from src.domain.confidence import row_label, tile_label

NAVY = "#0F2A3A"
BLUE = "#1E4257"
BACKGROUND = "#F4F6F8"
TEXT = "#1B2430"
MUTED = "#6B7A88"
BORDER = "#E2E7EC"
ROW_LINE = "#EEF1F4"

CSS = f"""
<style>
@import url("https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap");
/* Text as in the MVP design: Inter (screen 4 MVP), Arial as fallback. */
html, body, .stApp, .stApp p, .stApp td, .stApp th, .stApp li, .stApp span, .stApp div {{
  font-family: Inter, Arial, sans-serif;
}}
.stApp {{background: {BACKGROUND}; color: {TEXT};}}
/* Keep the header: it holds the screen navigation. Hide Streamlit's own menu and decoration. */
header[data-testid="stHeader"] {{background: #FFFFFF; border-bottom: 1px solid {BORDER};}}
/* Hide the menu and Deploy button only: hiding stToolbar itself also removes the page links. */
[data-testid="stAppDeployButton"], [data-testid="stMainMenu"],
[data-testid="stDecoration"], [data-testid="stStatusWidget"] {{display: none !important;}}
/* No sidebar in this app. Its expand button shows at narrow widths with an icon name as text
   when the icon font is not loaded, so the button is hidden. */
[data-testid="stExpandSidebarButton"],
[data-testid="stSidebarCollapsedControl"] {{display: none !important;}}
footer {{visibility: hidden;}}
/* Page gutter: Streamlit 1.66 uses the main block container, not .block-container. */
.block-container, [data-testid="stMainBlockContainer"] {{padding-top: 3.6rem !important;
  padding-bottom: 0 !important; padding-left: 12px !important; padding-right: 12px !important;}}
/* Action buttons (Evidence) as compact text links, so lists do not leave large gaps. */
div[data-testid="stButton"] button {{min-height: 0 !important; padding: 0 4px !important;
  font-size: 10px !important; color: #1B5E9E !important;}}
div[data-testid="stButton"] {{margin: 0 !important;}}
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
.covwrap {{overflow-x: auto; max-width: 100%;}}
table.cov {{table-layout: fixed;}}
table.cov col.first {{width: 215px;}}
.legend {{display: flex; flex-wrap: wrap; gap: 6px 16px; margin: 8px 0 0;
  font-size: 11px; color: {MUTED};}}
.legend span {{display: inline-flex; align-items: center; gap: 6px;}}
.needs {{margin-top: 14px; font-size: 11px; color: {MUTED};}}
.needs .need {{display: grid; grid-template-columns: 210px 1fr; align-items: center;
  padding: 3px 0; border-top: 1px solid {ROW_LINE};}}
.needs .need b {{color: #1B2430;}}
.mkt {{font-size: 12px; margin: 0 0 8px; line-height: 1.4;}}
.chip {{display: inline-block; background: #F1F3F5; border: 1px solid #C9D1D9;
  border-radius: 3px; padding: 0 6px; margin-right: 4px; font-size: 10px;}}
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
.b-fact {{background: #E7F1F6; color: #1E4257;}}
.b-signal {{background: #FFF4D6; color: #7A5A00;}}
.b-hyp {{background: #F1E9FB; color: #5B2E91;}}
.b-pending {{background: #EEF1F4; color: {MUTED};}}
.b-unconfirmed {{background: #F4F6F8; color: {MUTED}; border: 1px dashed #9AA5B1;}}
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
/* Text sizes for list rows and notes, so screens do not set sizes inline. */
.t-strong {{font-size: 10px; color: {TEXT};}}
.t-body {{font-size: 10px; color: #3A4A58;}}
.t-meta {{font-size: 10px; color: {MUTED};}}
.t-foot {{font-size: 10px; color: {MUTED}; margin-top: 4px;}}
.t-row {{font-size: 10px; border-top: 1px solid {ROW_LINE}; padding: 3px 0;}}
/* Card label: small caps line above the value, as the metric labels on the Overview. */
.lb {{font-size: 9px; font-weight: 600; color: {MUTED}; text-transform: uppercase;
  letter-spacing: 0.2px; line-height: 1.3; margin-bottom: 2px;}}
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


APP_TITLE = "Danaher / Cytiva Competitive Monitor"
LEGEND = "Fact = filings and prices · Signal = news and estimates · Hypothesis = to test"


def header(title: str, subtitle: str) -> None:
    st.markdown(
        f"<div class='hdr'><div class='t'>{title}</div><div class='s'>{subtitle}</div></div>",
        unsafe_allow_html=True,
    )


def screen_header(number: int, name: str) -> None:
    """The header used on every screen, as on the Overview: app title, then the screen name
    and number, then the evidence legend."""
    header(APP_TITLE, f"{name} (screen {number} of 6) · {LEGEND}")


def html_table(
    headers: list[str],
    rows: list[list[str]],
    classes: dict | None = None,
    auto_width: bool = False,
) -> str:
    """Compact HTML table, the same look on every screen. `classes` maps (row, col) to a CSS
    class for highlighting. `auto_width` sizes the table to its content. The first column is
    left-aligned; any other column is right-aligned when its values are numbers (placeholders
    such as n/d or to collect are ignored), and left-aligned when it holds text."""
    classes = classes or {}
    numeric = [False]
    for c in range(1, len(headers)):
        values = [_plain(row[c]) for row in rows if c < len(row)]
        real = [v for v in values if v not in _PLACEHOLDERS]
        numeric.append(not real or all(_is_number(v) for v in real))
    head = "".join(
        f'<th class="{"n" if numeric[i] else ""}">{h}</th>' for i, h in enumerate(headers)
    )
    body = ""
    for r, row in enumerate(rows):
        cells = ""
        for c, value in enumerate(row):
            css = " ".join(filter(None, ["n" if numeric[c] else "", classes.get((r, c), "")]))
            cells += f'<td class="{css}">{value}</td>'
        body += f"<tr>{cells}</tr>"
    table_class = "c auto" if auto_width else "c"
    # Every table sits in a box as wide as its card and scrolls inside it, so a wide table never
    # runs over the next card (review: screen 4 approvals, screen 5 integration readiness).
    table = f'<table class="{table_class}"><tr>{head}</tr>{body}</table>'
    return f"<div style='width:100%;max-width:100%;overflow-x:auto'>{table}</div>"


_PLACEHOLDERS = {"", "n/d", "to collect", "NA", "–", "&ndash;", "—", "none", "No"}
_NUMBER = re.compile(r"[+\-–]?\$?[+\-–]?\d[\d,]*(\.\d+)?\s*(%|bn|m|x|pp)?( \(.*\))?")


def _plain(value: str) -> str:
    """The text of a table cell, without its tags."""
    return re.sub(r"<[^>]+>", "", str(value)).strip()


def _is_number(text: str) -> bool:
    return bool(_NUMBER.fullmatch(text.replace("&ndash;", "–")))


def source_link(url: str | None) -> str:
    """A table cell that links to its public source, or a dash when there is none."""
    if not url or "docs.google.com/spreadsheets" in url:
        return "&ndash;"
    return f"<a href='{url}'>source</a>"


def kpi_card(
    label: str, value: str, sub: str = "", footer: Callable[[], None] | None = None
) -> None:
    """A headline card: label, big value and a short line, on the same grid as the Overview.
    The footer (the Evidence link) is drawn inside the card, at the bottom."""
    with st.container(border=True):
        st.markdown(
            f"<div class='lb'>{label}</div><div class='big'>{value}</div>"
            + (f"<div class='rs'>{sub}</div>" if sub else ""),
            unsafe_allow_html=True,
        )
        if footer is not None:
            footer()


def is_primary_url(url: str | None) -> bool:
    """A primary source is a public https link. A Google Sheets link is a pointer, not a source."""
    return bool(url) and url.startswith("https://") and "docs.google.com" not in url


SOURCE_TYPES_KEY = "_source_types"  # session: URL -> source type, set by each page
BADGE_ROWS_KEY = "_badge_rows"  # session: every row badge drawn on the page, for the tests
SHOW_UNCONFIRMED_KEY = "show_unconfirmed"  # session: the screen-level L toggle
BADGE_HTML = {
    FACT_LABEL: ("b-fact", "FACT"),
    SIGNAL_LABEL: ("b-signal", "SIGNAL"),
    UNCONFIRMED_LABEL: ("b-unconfirmed", "UNCONFIRMED"),
    HYPOTHESIS_LABEL: ("b-hyp", "HYPOTHESIS"),
}


def remember_source_types(types: dict[str, str]) -> None:
    """Called at the start of each page: the source type of every URL, and a fresh badge log."""
    st.session_state[SOURCE_TYPES_KEY] = types
    st.session_state[BADGE_ROWS_KEY] = []


def source_type_of(url: str | None) -> str:
    """The sheet's source type for a URL ("" when the URL is not a sheet source)."""
    return st.session_state.get(SOURCE_TYPES_KEY, {}).get(url or "", "")


def row_basis(confidence: str | None, url: str | None) -> str:
    """The badge label for one row, from its confidence and its source type (the shared rule)."""
    label = row_label(confidence, source_type_of(url))
    st.session_state.setdefault(BADGE_ROWS_KEY, []).append(
        {"confidence": confidence, "url": url, "label": label}
    )
    return label


def badge_html(label: str) -> str:
    """Badge HTML for a label: FACT, SIGNAL, UNCONFIRMED or HYPOTHESIS."""
    css, text = BADGE_HTML.get(label, ("b-pending", "TO COLLECT"))
    return f"<span class='badge {css}'>{text}</span>"


def row_basis_typed(confidence: str | None, source_type: str | None, url: str | None) -> str:
    """The label for a row whose source type is already known (a sheet Source type column, not a
    URL lookup). Records it for the tile heading and the rule test."""
    label = row_label(confidence, source_type)
    st.session_state.setdefault(BADGE_ROWS_KEY, []).append(
        {"confidence": confidence, "url": url, "label": label, "source_type": source_type}
    )
    return label


def row_badge_typed(confidence: str | None, source_type: str | None, url: str | None) -> str:
    """The badge for a row whose source type is already known (for example China's sources)."""
    return badge_html(row_basis_typed(confidence, source_type, url))


def record_label(label: str) -> str:
    """Record a row's label on the page without drawing a badge (the tile heading uses it).

    For rows whose label is fixed by the sheet: they have no confidence to apply the rule to."""
    st.session_state.setdefault(BADGE_ROWS_KEY, []).append(
        {"confidence": None, "url": None, "label": label, "stored": True}
    )
    return label


def stored_label_badge(label: str) -> str:
    """The badge for a row whose label is stored (not computed by the rule): hypotheses and the
    attention items. Records the label for the tile heading."""
    return badge_html(record_label(label))


def row_badge(confidence: str | None, url: str | None) -> str:
    """The badge HTML for one row, computed from its confidence and source type."""
    return badge_html(row_basis(confidence, url))


def evidence_badge(confidence: str | None, primary_url: str | None) -> str:
    """Badge HTML for one row (kept for the callers that pass a URL)."""
    return row_badge(confidence, primary_url)


def unconfirmed_toggle() -> bool:
    """The screen-level toggle for L rows. Off by default: L rows are hidden, and shown with the
    UNCONFIRMED badge when it is on."""
    return st.toggle("Show unconfirmed (L)", value=False, key=SHOW_UNCONFIRMED_KEY)


def visible(confidence: str | None, show_unconfirmed: bool) -> bool:
    """A row is hidden by default when its confidence is L."""
    return show_unconfirmed or confidence != "L"


@contextmanager
def tile_box(title: str) -> Iterator[None]:
    """A bordered tile whose heading badge is the weakest row badge drawn inside it (the shared
    rule: FACT, FACT AND SIGNAL, SIGNAL or UNCONFIRMED). The heading is written after the rows,
    into a slot reserved at the top of the tile."""
    with st.container(border=True):
        slot = st.empty()
        log = st.session_state.setdefault(BADGE_ROWS_KEY, [])
        start = len(log)
        yield
        label = tile_label([r["label"] for r in st.session_state.get(BADGE_ROWS_KEY, [])[start:]])
        tile_badge = (
            f" <span class='badge b-{_TILE_CSS[label]}'>{_TILE_TEXT[label]}</span>" if label else ""
        )
        slot.markdown(f"<div class='sec'>{title}{tile_badge}</div>", unsafe_allow_html=True)


_TILE_CSS = {
    FACT_LABEL: "fact",
    SIGNAL_LABEL: "signal",
    UNCONFIRMED_LABEL: "unconfirmed",
    HYPOTHESIS_LABEL: "hyp",
    FACT_AND_SIGNAL_LABEL: "fact",
}
_TILE_TEXT = {
    FACT_LABEL: "Fact",
    SIGNAL_LABEL: "Signal",
    UNCONFIRMED_LABEL: "Unconfirmed",
    HYPOTHESIS_LABEL: "Hypothesis",
    FACT_AND_SIGNAL_LABEL: "Fact and Signal",
}


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
