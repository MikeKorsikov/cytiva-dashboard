"""Every threshold the app applies, in one place (audit B-14).

Each value says what it decides. The screens, the metrics and the footnotes read these names, so
a threshold is changed here and nowhere else. Change a value only with the owner's agreement.
"""

from __future__ import annotations

# Country barrier index (screen 3): scores run from 1 (low barrier) to 5 (high barrier).
BARRIER_RED_FROM = 2.5  # barrier index at or above this is drawn in red (country table)
LOW_BARRIER_BELOW = 2.0  # barrier index below this is a low barrier (the hub rule, screen 3)

# Score colour scale (country table, screen 3): a score below SCORE_GREEN_BELOW is green, below
# SCORE_AMBER_BELOW is amber, and anything higher is red.
SCORE_GREEN_BELOW = 2
SCORE_AMBER_BELOW = 3.5

# Tariff score (WTO applied MFN rate, 2025, screen 3): below 5% scores 1, 5 to 10% scores 3,
# 10% and above scores 5. The bounds are the percentages where the score steps.
TARIFF_STEP_LOW_PCT = 5  # below this: score 1
TARIFF_STEP_HIGH_PCT = 10  # at or above this: score 5 (between: score 3)

# Technology relevance (screen 5): the incident score totals that give each relevance level.
RELEVANCE_HIGH_FROM = 6  # total score at or above this is High (red)
RELEVANCE_MEDIUM_FROM = 4  # total score at or above this is Medium (amber); below is Low

# Incident corroboration (screen 5): an incident is corroborated by at least this many tier A
# sources, or this many tier B sources.
CORROBORATED_TIER_A = 1
CORROBORATED_TIER_B = 2
