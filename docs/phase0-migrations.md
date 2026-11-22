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
