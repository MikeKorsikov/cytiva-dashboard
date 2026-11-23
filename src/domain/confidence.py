"""The evidence badge rule, in one place (CLAUDE.md, "Evidence labels on screens").

Row badge, per row:
- UNCONFIRMED when the row's confidence is L (hidden by default; shown with the screen toggle).
- FACT only when the confidence is H AND the row's source is Primary.
- SIGNAL otherwise (medium or high confidence from a secondary source, or no known source type).

Tile badge: the weakest row badge shown on the tile. Mixed Fact and Signal rows give
"Fact and Signal". Hypothesis rows are a separate label and do not enter this rule.
"""

from __future__ import annotations

FACT = "Fact"
SIGNAL = "Signal"
UNCONFIRMED = "Unconfirmed"
HYPOTHESIS = "Hypothesis"
FACT_AND_SIGNAL = "Fact and Signal"


def is_primary(source_type: str | None) -> bool:
    """A Primary source type, as the sheets' Sources tabs give it (e.g. "Primary", "Primary
    filing", "Primary (company)"). A secondary or trade source is never primary."""
    return bool(source_type) and source_type.strip().lower().startswith("primary")


def row_label(confidence: str | None, source_type: str | None) -> str:
    """The badge for one row."""
    if confidence == "L":
        return UNCONFIRMED
    if confidence == "H" and is_primary(source_type):
        return FACT
    return SIGNAL


def tile_label(labels: list[str]) -> str | None:
    """The badge for a tile: the weakest row badge shown. None when the tile shows no row."""
    shown = set(labels)
    if not shown:
        return None
    if shown == {FACT}:
        return FACT
    if shown == {HYPOTHESIS}:
        return HYPOTHESIS
    if UNCONFIRMED in shown:
        return UNCONFIRMED
    if SIGNAL in shown:
        return FACT_AND_SIGNAL if FACT in shown else SIGNAL
    return FACT
