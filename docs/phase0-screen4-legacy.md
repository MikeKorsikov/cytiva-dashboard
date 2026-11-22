# Screen 4 legacy exceptions

Closed on 22 Nov 2026. The two Finance and IT implication questions moved to the sheet
(tab "T9 Implications", I-01 and I-02, always Hypothesis). They load into `demand_implication`
(`src/ingest/demand.py`) and the screen reads them from there. The legacy test
(`test_legacy_implications_are_text_until_the_sheet_has_a_tab`) flipped when the tab was added to
the export config, and was then removed, as planned.

Not legacy (the data comes from the sheet):
- Tile 8 product use: Hypothesis rows from the sheet's T8 tab, hidden by default, counted as awaiting confirmation.
- Map positions (`COUNTRY_CENTRE` in `src/metrics/demand.py`): approximate positions for the map dots. They are not figures and the sheet has no coordinates.
- Captions such as "FY2025, Pharma 50 (secondary source)": typed descriptions of the sheet's source tab. The period and source name also come from sheet rows.

Values before they moved: `docs/phase0-legacy-values.md`.
