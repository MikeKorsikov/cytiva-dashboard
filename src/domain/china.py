"""China constants shared by the loader, the metrics and the screen.

Kept here so that metrics and the app never import the ingest package (CLAUDE.md, B-24).
"""

from __future__ import annotations

# Assumed RMB per USD for every RMB figure. Replace with the PBoC 2025 annual average when loaded.
CNY_USD_RATE = 7.2

# Sheet product codes -> the family names used by the screen 2 step rule (metrics.coverage).
FAMILY_NAMES = {
    "Med": "Media",
    "SU": "Single-use",
    "Res": "Resins",
    "Filt": "Filtration",
    "Fill": "Filling",
    "Gen": "Genomic",
    "Sys": "Systems",
    "Anl": "Analytical",
}
