"""The companies the Overview screen lists, and the order of each list (audit B-16).

The names are the company_id values used in the database, and each one is checked against the
`company` table by tests/test_companies.py. Cytiva has no row of its own in `company` (it is part
of Danaher); its figures come from Danaher's segment rows.
"""

from __future__ import annotations

# Columns of the news list on the Overview (Danaher and Cytiva first, then the peers).
NEWS_COMPANIES: tuple[str, ...] = (
    "Danaher",
    "Cytiva",
    "Thermo Fisher",
    "Sartorius",
    "Repligen",
    "Avantor",
    "Merck KGaA",
)

# Rows of the M&A count table: the buyers whose announced deals are counted. Cytiva is not a
# buyer; Danaher makes the deals for it.
DEAL_BUYERS: tuple[str, ...] = (
    "Danaher",
    "Thermo Fisher",
    "Sartorius",
    "Repligen",
    "Avantor",
    "Merck KGaA",
)

# Rows of the Forbes Global 2000 rank table. Merck KGaA is ranked at group level, as Danaher is.
RANKING_COMPANIES: tuple[str, ...] = (
    "Danaher",
    "Merck KGaA",
    "Thermo Fisher",
    "Sartorius",
    "Repligen",
    "Avantor",
)

# Order on every Overview tile: largest to smallest by FY2025 revenue in USD, the one size measure
# all tiles share. Cytiva is part of Danaher and has no revenue of its own, so it comes last.
PEER_ORDER: tuple[str, ...] = (
    "Thermo Fisher",
    "Merck KGaA",
    "Danaher",
    "Avantor",
    "Sartorius",
    "Repligen",
    "Cytiva",
)
