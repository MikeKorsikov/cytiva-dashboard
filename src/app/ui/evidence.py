"""EvidenceDrawer: the evidence behind a tile, opened from a button on the tile.

A tile has one "Evidence" button. It opens a dialog that lists every row the tile shows, with
the value as displayed, its evidence label (Fact, Signal or Hypothesis), its confidence and its
source. A row with no public source says so; it is never shown as sourced.

Public source rule (as in design.source_link): an https link that is not a research-sheet link.
"""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from src.app.design import BADGES

BADGE_CLASS = {"Fact": "fact", "Signal": "signal", "Hypothesis": "hyp"}
NO_SOURCE = "No public source yet: to collect"


@dataclass(frozen=True)
class Evidence:
    """One displayed row: what it says, how it is labelled, and where it comes from."""

    row: str  # what the row is, for example "Danaher, FY2025"
    shown: str  # the value as displayed in the tile
    label: str  # Fact, Signal or Hypothesis
    confidence: str | None = None
    source_url: str | None = None
    source_name: str | None = None


def is_public_source(url: str | None) -> bool:
    """A public https link, not a link to the research sheet."""
    return bool(url) and url.startswith("https://") and "docs.google.com/spreadsheets" not in url


def sources_missing(items: list[Evidence]) -> int:
    """How many displayed rows have no public source (they are shown as to collect)."""
    return sum(1 for item in items if not is_public_source(item.source_url))


def badge(label: str) -> str:
    """The evidence badge as the rest of the app draws it (same classes as design.section)."""
    kind = BADGE_CLASS.get(label, "pending")
    return f"<span class='badge b-{kind}'>{BADGES.get(kind, label)}</span>"


@st.dialog("Evidence")
def _drawer(title: str, items: list[Evidence]) -> None:
    st.markdown(f"**{title}**")
    st.markdown(
        f"{len(items)} rows shown. {sources_missing(items)} without a public source.",
    )
    rows = []
    for item in items:
        if is_public_source(item.source_url):
            source = f"<a href='{item.source_url}'>{item.source_name or 'source'}</a>"
        else:
            source = f"<span class='muted'>{NO_SOURCE}</span>"
        rows.append(
            f"<tr><td>{item.row}</td><td>{item.shown}</td><td>{badge(item.label)}</td>"
            f"<td>{item.confidence or 'n/d'}</td><td>{source}</td></tr>"
        )
    st.markdown(
        "<table class='c'><tr><th>Row</th><th>Shown</th><th>Basis</th><th>Confidence</th>"
        "<th>Source</th></tr>" + "".join(rows) + "</table>",
        unsafe_allow_html=True,
    )


def evidence_button(key: str, title: str, items: list[Evidence]) -> None:
    """The tile's Evidence button. Opens the drawer with every row of the tile."""
    if st.button("Evidence", key=f"ev-{key}", type="tertiary"):
        _drawer(title, items)


def financial_items(rows: list[dict]) -> list[Evidence]:
    """One drawer row per peer in the financials tile."""
    items = []
    for r in rows:
        revenue = "n/d" if r["revenue_usd"] is None else f"{r['revenue_usd'] / 1e6:,.0f} $m"
        items.append(
            Evidence(
                row=f"{r['company']}, {r['fiscal_year'] or 'n/d'}",
                shown=f"revenue {revenue}",
                label=r["evidence_label"],
                confidence=r["confidence"],
                source_url=r["source_url"],
                source_name="primary source"
                if r["evidence_label"] == "Fact"
                else "secondary source",
            )
        )
    return items


def layoff_items(marks: list[dict]) -> list[Evidence]:
    """One drawer row per layoff cell shown (company and year)."""
    items = []
    for row in marks:
        for year, cell in sorted(row["years"].items(), reverse=True):
            items.append(
                Evidence(
                    row=f"{row['company']}, {year}",
                    shown=cell["mark"],
                    label=cell["label"],
                    source_url=cell["url"],
                    source_name="layoff source",
                )
            )
    return items


def deal_items(deals: list[dict], signals: list[dict]) -> list[Evidence]:
    """Company-reported deals (Fact) and the unverified feed signals (Signal) the tile lists."""
    items = [
        Evidence(
            row=f"{d['acquirer']}, announced {d['announced_date']}",
            shown=d["headline"],
            label="Fact",
            source_url=d["source_url"],
            source_name="company release",
        )
        for d in deals
    ]
    items += [
        Evidence(
            row=f"{s['acquirer']}, {s['announced_date']} (feed)",
            shown=s["headline"],
            label="Signal",
            source_url=s["source_url"],
            source_name="feed item",
        )
        for s in signals
    ]
    return items
