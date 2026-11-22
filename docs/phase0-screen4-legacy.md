# Screen 4 legacy exceptions

Screen 4 (demand drivers) reads every figure from the research sheet. The items below are on the
screen but not from the sheet. Each is listed here, and where a test applies it is named.

## 1. Implications for Finance & IT (text, Hypothesis)

- **Shown:** "Can we report revenue by medicine type?" and "Customer pipeline as demand signal?",
  badged Hypothesis.
- **Why it is legacy:** the sheet has no tab for these questions. They are typed in
  `src/app/shells.py` (`demand_screen`).
- **Figures:** none. The text is questions, not values.
- **Failing-when-fixed test:** `tests/test_demand.py::test_legacy_implications_are_text_until_the_sheet_has_a_tab`.
  It fails once a tab with "Implication" in its name is added to the screen 4 tab list in
  `seed_sheet_gids.yaml`. At that point, move the two questions into the sheet and delete the
  typed text.

## Not legacy (for the record)

- **Tile 8, product use:** the sheet's T8 rows are loaded with confidence Hypothesis and no source
  URL, as a Hypothesis row. The rows are hidden by default and counted as awaiting confirmation.
  This is not a legacy exception: the data comes from the sheet.
- **Map positions** (`COUNTRY_CENTRE` in `src/metrics/demand.py`): approximate country centres for
  the map dots. They are positions, not figures, and do not appear as values. The sheet has no
  coordinates. Nigeria was added with the other countries.
- **Captions** such as "FY2025, Pharma 50 (secondary source)" and "pledges, not spend": typed
  descriptions of the source tab. The period and source name also come from the sheet rows.
