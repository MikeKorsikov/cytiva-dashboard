# Screen 1 legacy exceptions

Screen 1 (overview) reads its tables from the research sheet "Screen 1 – Overview data" through
section maps (`src/ingest/sheet_headers.py`, `OVERVIEW_TABS`). The Python literals below have no
sheet tab, so they stay in code as legacy exceptions. Under the owner's rule for these, every
value they feed is badged Signal at most.

## 1. Layoffs (`src/ingest/layoffs.py`)

- **Literals:** `FY2025_10K` (four 10-K links) and `LAYOFFS` (company, year, Yes/No/Unknown mark,
  source URL, note). The research log is `docs/layoffs_research.md`.
- **Why legacy:** the sheet has no layoffs tab.
- **Badge:** Signal (already so in the loader).
- **Test:** `tests/test_layoffs.py`.
- **Values:** `docs/phase0-legacy-values.md`.

## 2. Danaher 10-K acquisition notes (`src/ingest/company_deals.py`)

- **Literals:** `DANAHER_10K_URL` and `DANAHER_10K_NOTES` (three sourced statements from the FY2025
  10-K, including the Abcam price of about $5.6 billion and the FY2024 $558 million).
- **Why legacy:** the sheet's M&A tab does not hold 10-K statements that are not single dated
  deals.
- **Badge changed:** the notes were stored as Fact; now Signal.
- **Test:** `tests/test_danaher_10k.py`.
- **Values:** `docs/phase0-legacy-values.md`.

## Not legacy (for the record)

- **Company deals:** from the sheet's T2 M&A tab (`sheet_deals()`). The literal list is gone.
  Four deals were re-worded and stay (Masimo, Bio-Techne, BioLife, Clario). Seven literal rows
  are not in the sheet and are removed: Danaher StatLab (2026), Genedata (2024), Abcam (2023; its
  price stays in the 10-K note), Aldevron (2021), Merck KGaA Silence (2026), MilliporeSigma and JSR
  (2025), Merck KGaA SpringWorks (2025). Deal rows: 11 company-reported before, 6 after.
  The M&A tile counts are unchanged (they match the sheet's own count rows).
- **Rankings:** from the sheet's T1 Rankings tab. The tab holds no values, so every rank shows
  To collect. The literal `CURATED_RANKINGS` (empty) is gone.

- **Peer financials, share prices, news and implications** come from the sheet (ov_* tables). The EDGAR, annual-report and tenk-text paths that fed the old financial table are removed (see docs/phase0-migrations.md).
