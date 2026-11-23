"""Sheet tab names and labels the code relies on (audit B-20). Change a name here, once.

The names match the Google Sheet exactly; the seed exports in data/ use the same names.
"""

from __future__ import annotations

# The screen_notes tab for the Overview M&A notes (the 10-K notes under the deal tile).
OVERVIEW_MA_TAB = "Overview M&A"

# The screen_notes tab that holds the overview sheet's README rows (B-18: provenance text).
OVERVIEW_README_TAB = "Overview README"

# README rows the Overview screen shows, by their label in the sheet README tab. A label that is
# missing from the sheet shows "to collect" on the screen; no text is typed in the code.
README_PRICES = "Prices source"  # where the share prices come from, and when they refresh
README_SARTORIUS = "Sartorius basis"  # why Sartorius is Signal on the financials tile
README_RANKINGS = "Rankings status"  # the state of the Forbes Global 2000 ranks

# The README label that gives the sheet's date (the "Data as of" line on screen 5 and others).
AS_OF_LABEL = "As of"
