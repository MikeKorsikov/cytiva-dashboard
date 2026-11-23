# Screen 1 legacy exceptions

Closed on 22 Nov 2026. No Python literal holds a screen 1 value any more.

| Was | Now | Where |
| --- | --- | --- |
| Layoffs (`src/ingest/layoffs.py`, 18 rows) | Sheet tab "T6 Layoffs" (LO-01 to LO-18), loaded by `load_layoffs` in `src/ingest/overview_sheet.py` into `layoff_year`. File deleted | `data/overview/sheet/layoffs.csv` |
| Danaher 10-K notes (`DANAHER_10K_NOTES`, `DANAHER_10K_URL`) | Sheet tab "T2 M&A", rows labelled "10-K note" (3 rows, source S19). Notes in `screen_notes` for the Overview M&A tile, never deals or counts | `data/overview/sheet/t2_ma.csv`, `load_10k_notes` |
| Company deal literals (`COMPANY_DEALS`, `DEAL_VALUE_USD_M`) | Sheet tab "T2 M&A" (MA-nn rows) | `sheet_deals()` in `src/ingest/company_deals.py` |
| Rankings literal (`CURATED_RANKINGS`) | Sheet tab "T1 Rankings" | `src/ingest/rankings.py` |
| Annual-report config (`REPORTS`, labels) | Removed with the financial paths; peer financials are the sheet's T1 tab | `docs/phase0-migrations.md` |

Badges follow the FACT rule (`row_label` in `src/ingest/overview_sheet.py`): H confidence and a
Primary source type is Fact; otherwise Signal. Layoffs: 4 rows are Fact (LO-03, LO-11, LO-12,
LO-13). The review round expected 5; the sheet has 4 rows that are H and Primary.

Values before they moved: `docs/phase0-legacy-values.md`.
