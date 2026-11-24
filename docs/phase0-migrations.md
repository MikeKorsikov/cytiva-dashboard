# Phase 0 migration record

One record per affected table: what changed, when, in which commit, and the row counts before and
after. "Before" is the committed `data/app.db` at the start of the Phase 0 session (commit
`2a463d2`, 21 Nov 2026 state). "After" is `data/app.db` at the commit named. Row-level history is
not reconstructed (no change_log rows were written for the direct loads, see the note at the end).

## Screen 4 and migrations on the demand load (22 Nov 2026, commit 4fae85a)

| Table | Change | Rows before | Rows after |
| --- | --- | --- | --- |
| demand_burden | Layout: +new_cancer_cases_2024, +cancer_2024_source_url. Reloaded from the sheet | 19 | 20 |
| demand_pipeline | Layout: +change. Reloaded from the sheet | 8 | 14 |
| demand_approval | Reloaded from the sheet (2025 and 2026 year to date) | 8 | 10 |
| demand_expiry | Reloaded from the sheet (Ocrevus rejected: no source) | 4 | 4 |
| demand_policy | Reloaded from the sheet | 6 | 6 |
| demand_top_drug | Reloaded from the sheet | 15 | 15 |
| demand_capacity | Reloaded from the sheet (13 pledges, 3 built sites) | 16 | 16 |
| demand_product_use | Reloaded from the sheet (Hypothesis, no source) | 5 | 5 |
| country_demand | Layout migration applied by the schema on that load: +nature_index_share_2025. Rows kept | 21 | 21 |
| country_barrier_index | Layout migration: +display_on_tile, +legacy_fields, +sheet_barrier_index, +sheet_scores_available, +source_ids. Rows kept | 11 | 11 |
| tech_eos | Layout migration: +reason, +show_on_tile, +tile_note. Rows kept | 8 | 8 |
| tech_incidents | Layout migration: +application. Rows kept | 9 | 9 |
| tech_watchlist | Layout migration: +applications. Rows kept | 14 | 14 |
| tech_estate_evidence | Layout migration: +applications. Rows kept | 10 | 10 |
| screen_notes | The 17 demand-tab notes (T1, T4, T6, T7, T8) written by the demand load. The 17 other rows are unchanged | 17 | 34 |

## Screen 1 deal and ranking loads (22 Nov 2026, commit 6fe5484)

The three Overview M&A notes were rewritten with the Signal label (they were Fact): screen_notes is
keyed on tab, label and text, so the count is unchanged.

| Table | Change | Rows before | Rows after |
| --- | --- | --- | --- |
| deal | Layout: +value_text, +completed_date. Company-reported rows (source_type document, Fact) replaced by the sheet's M&A rows: 11 to 6. Total rows 64 to 59 | 64 | 59 |
| ranking | Curated rows now come from the sheet's T1 Rankings tab. The tab has no values | 0 | 0 |

## Screen 1 sheet tables and removed paths (22 Nov 2026, this commit)

| Table | Change | Rows before | Rows after |
| --- | --- | --- | --- |
| ov_financial | New table: peer financials from the sheet (T1). Loaded through the store (source checked) | not present | 6 |
| ov_price | New table: share-price list from the sheet (T3). Values empty; state "awaiting feed" | not present | 6 |
| ov_news | New table: competitor news seed from the sheet (T4) | not present | 7 |
| ov_implication | New table: implications from the sheet (T5), Hypothesis | not present | 3 |
| ov_attention | New table: attention items from the sheet (AT-01 to AT-05) | not present | 5 |
| financial_metric | The old path is removed: EDGAR, annual-report and tenk-text loaders no longer run. Rows cleared; nothing reads the table on screen | 117 | 0 |

Unchanged feeds: `share_price_daily` (price feed, 1562 rows) and `news_item` (news feed, 357 rows)
are not displayed on screen 1 now. The feeds keep running. Wiring them to the screen is open.

## Notes

- Deletions and layout migrations were applied directly to `data/app.db` (not through a refresh
  run). They are not in `change_log`. This record is the log for them.
- `financial_metric` stays in the schema, because the store tests use it as a generic example
  table. It has no loader now.
- Open: the technology README notes (20 rows in the sheet export, commit 1ca0ce5) are not in
  `app.db`. The technology loader has not been run against the database since that export change.
- Commit `4fae85a` migrated the rows in place (country and technology tables). The schema
  migration log for that load was not written at the time.

## Full refresh through the normal command (22 Nov 2026, commit of this record)

Command: `uv run python -m src.ingest.refresh --trigger manual`. It is the first full run since the
Phase 0 work started. The direct loads above are the only record before it.

Run records in `refresh_run`:

| Run | Start (UTC) | Status | Rows written | Note |
| --- | --- | --- | --- | --- |
| 26 | 14:45:01 | failed | 1560 | News feed for "Avantor" returned HTTP 429 (rate limit). The loaders before news had already written. Upserts are repeatable |
| 27 | 14:45:33 | succeeded | 2502 | Retry, same command. Unverified: 1 |
| 25 | 13:58:25 | running | 0 | Left open by an earlier direct load (not a refresh). Not closed by this record |

A failed news source stops the whole run (the loaders run in sequence and the first error is
raised). Option for the owner: log a per-feed failure and continue (CLAUDE.md asks each run to log
failures). Not changed here.

Row counts per table, before (the copy taken just before run 26) and after run 27. Only tables
whose counts changed are listed; the other 69 tables are unchanged:

| Table | Before | After |
| --- | --- | --- |
| cdmo_site | 34 | 35 |
| change_log | 3762 | 4522 |
| country_demand | 21 | 28 |
| deal | 59 | 68 |
| demand_implication | (table new in the schema) | 2 |
| news_item | 357 | 394 |
| refresh_run | 23 | 25 |
| s2_market_size | 0 | 3 |
| s2_supplier_revenue | 0 | 6 |
| screen_notes | 34 | 105 |
| share_price_daily | 1562 | 1572 |
| tech_app_list | 0 | 136 |
| tech_apps | 0 | 120 |
| tech_estate_evidence | 10 | 11 |
| tech_row_sources | 100 | 101 |
| tech_sources | 39 | 43 |

Why the "before" counts for tech_app_list and tech_apps were 0: the applications list was never
in `app.db`, so screen 5's ranking table showed "No items to show". The refresh loaded it.

Layoffs (`layoff_year`) and the overview sheet tables (`ov_*`) did not change count. The
layoff_year rows were replaced by the sheet loader (same 18 rows).

## Run 34 (23 Nov 2026): badge columns, screen 2 hypotheses

Migrations logged by the run (change_log, run 34). Each keeps every row; no column was removed.

| Table | Change | Rows before | Rows after | Why |
| --- | --- | ---: | ---: | --- |
| deal | added confidence, source_type_text | 69 | 69 | M&A badge derived from sheet T2 Confidence and the first source's type (decision 1) |
| ov_attention | added confidence, source_type_text | 5 | 5 | attention badge derived from sheet Confidence and Source type (decision 2) |
| s2_implication | new table (id, hypothesis, area, based_on, confirm_or_refute) | 0 | 2 | screen 2 hypotheses from the T5 Implications tab, gid 14 (decision 3, B-17) |

Other changes (no DDL):
- EVIDENCE_LABELS gains Derived: the badge is computed at display from confidence and source type. Stored on the M&A deal and attention rows.
- Sheet exports: data/overview/sheet/attention.csv (new columns J and K), data/coverage/sheet/t5_implications.csv (new), seed_sheet_gids.yaml (screen 2 T5 Implications, gid 14).
- The refresh gained a final step, apply_growth_checks (B-06). It changed 0 rows.

Acceptance check 2 (run the refresh twice on a copy of app.db): 85 tables, identical row counts after both runs. The run wrote 2,717 rows each time.


## Run 35 (23 Nov 2026): enforced checks, dropped tables

Dropped (no loader writes them; each was checked for rows and code references before the drop):

| Table | Rows before | Kept as | Why |
| --- | ---: | --- | --- |
| revenue_observation | 8 | data/archive/revenue_observation.csv (all 8 rows, every column) | legacy table: no longer in the schema, no loader. The YoY check it fed is removed (growth above 50% still checked on cn_financial and ov_financial). |
| challenger_coverage | 0 | none | not in the schema; no loader; no code reference. |
| step_family_map | 0 | none | in the schema only, no loader and no code reference. Entry removed from src/ingest/schema.py. |

Duplicates of the naming deferred item (section 13) are not dropped: disease_burden, approval, capacity_pledge, drug_sales, patent_expiry, policy_event, lifecycle_date, clinical_trial, modality_product_map, market_estimate, incident, integration_tier, adoption_signal, vendor_link, estate_item, gmp_site.

Enforced checks (no DDL): a failing row keeps its values and is stored with verification_status unverified, confidence L and check_notes; the change is logged. Growth (apply_growth_checks) and the quote check (apply_quote_checks) run last in each refresh. Run 35: 0 rows failed either check.

Sheet re-export: data/china/sheet/headline.csv (H-10, H-11 evidence now starts "Calculation:"). Loaded in run 35.

## Run 36 (23 Nov 2026): README rows, tab constants, company and coverage lists

- New rows, no DDL: screen_notes gains the overview sheet's README rows under tab "Overview README" (13 rows; the sheet README exported to data/overview/sheet/readme.csv). Loaded in run 36.
- The overview sheet README has no rows yet for "Prices source", "Sartorius basis" and "Rankings status". The screen shows "to collect" for each until the owner adds them.
- Code-only: the tab names (src/domain/tabs.py), the thresholds (src/domain/thresholds.py), the company lists (src/domain/companies.py) and the coverage model (src/domain/coverage_model.py). No table or column changed.

## Run 37 (23 Nov 2026): merge with main, sheet links and labels

- DDL: tech_eos gains `application` (TEXT). Rows kept (7). Source: sheet column P, Application (list Name). EOS-04 is blank by design.
- New rows, no DDL: screen_notes tab "Demand README" (the demand README rows, including the Display labels block). Loaded in run 37.
- Merged origin/main (#117 and #118). The conflicts were screen 5; the branch's later decision (Show on tile = Yes only) is kept.
- The database is refreshed in run 37 (succeeded). Row counts unchanged except tech_eos (application added) and screen_notes.

## Run 38 (23 Nov 2026): header texts and labels

- New rows, no DDL: screen_notes tab 'Overview headers' (the Forbes and rankings column header texts, from the t1_rankings.csv header row); screen_notes 'Demand README' gains the pipeline period and source rows. Run 38 succeeded.
