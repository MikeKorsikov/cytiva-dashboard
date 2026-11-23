"""The coverage model the screens use: companies, product families, bioprocess steps (audit B-15).

These are the vocabulary of screens 2 and 6, not values. A test (tests/test_coverage_model.py)
checks each list against the grid stored from the sheet, so a rename in the sheet shows up.
"""

from __future__ import annotations

CYTIVA = "Cytiva"

# Companies in the footprint grid, with the short code the grid header shows.
COMPANIES: tuple[tuple[str, str], ...] = (
    (CYTIVA, "CYT"),
    ("Thermo Fisher", "TMO"),
    ("Sartorius", "SRT"),
    ("Repligen", "RGN"),
    ("Avantor", "AVT"),
    ("Merck KGaA", "MRK"),
)

# Product families (columns of the grid). Service is a step, not a family, so it is not listed.
FAMILIES: tuple[str, ...] = (
    "Media",
    "Single-use",
    "Resins",
    "Filtration",
    "Filling",
    "Genomic",
    "Systems",
    "Analytical",
)

# The eight bioprocess steps (rows of the steps matrix). A step needs the families in
# metrics.coverage.STEP_FAMILIES.
STEPS: tuple[str, ...] = (
    "1. Research tools",
    "2. Cell line and process dev.",
    "3. Upstream processing",
    "4. Downstream processing",
    "5. Formulation and fill-finish",
    "6. QC and release testing",
    "7. Facility and automation",
    "8. Service and support",
)
