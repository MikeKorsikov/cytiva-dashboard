# Phase 0 progress (resumable)

Each screen: exports (live tabs, read-only, in data/<screen>/sheet/), loader, metrics, screen (shells.py), tests, commit. Row counts before and after are for data/app.db. Update this file after each commit.

## Screen 2: competitor coverage (done)
- [x] Exports: data/coverage/sheet/ (sources, peer_sites, t1_coverage_grid, t4_region_cards, register_sites)
- [x] Loader: src/ingest/coverage.py (s2_* tables)
- [x] Metrics: src/metrics/coverage.py (grid_cells, step_cells, biotech_sales)
- [x] Screen: src/app/shells.py coverage_screen, region cards use evidence_badge
- [x] Tests: tests/test_coverage.py, tests/test_design.py
- Commits: 5f2c659 (exports and loader), 5007296 (Cytiva from register), 78e01f5 and 621897d (T1 re-export), eaf6bfd and 946d987 (register batch 2, test fixes), 9e295fc (FACT badge)
- Row counts before (footprint 207; footprint_evidence 109) and after (s2_source 20; s2_peer_site 47; s2_peer_family 51; s2_cyt_site 51; s2_grid 73; s2_biotech_sales 4)
- Display changes: see docs/phase0-screen2.md and docs/phase0-screen2-changes.txt
- Full test count at last run: 214 passed

## Screen 6: China (done)
- [x] Exports: data/china/sheet/ (9 tabs). Commit 95cd0a9.
- [x] Loader: src/ingest/china.py (by header name; register rule for Cytiva China; CE-35 step 8)
- [x] Metrics: src/metrics/china.py (tiles gated by Show on tile; Service row; badge helpers with primary-source rule)
- [x] Screen: src/app/shells.py (badges via cm.badge; vendor-to splits on commas and semicolons)
- [x] Tests: tests/test_china.py (16 tests + secondary-source badge test)
- Commits: 95cd0a9 (exports), 06321f1 (loader, metrics, screen, tests), next commit (primary-source badge fix)
- Row counts before -> after: cn_source 46 -> 46; cn_company 19 -> 19; cn_coverage 34 -> 41; cn_coverage_evidence 35 -> 35; cn_financial 12 -> 12; cn_vendor 5 -> 5; cn_opportunity 6 -> 6; cn_implication 5 -> 5; cn_headline 9 -> 12 (H-02, H-10, H-11, H-12 stored, not shown)
- Display changes: Cytiva China matrix: Media, Resins, Filtration, Filling, Genomic, Analytical now Not made (were ?); Systems Partial -> Not made; step 3 ? -> Partial; step 8 ? -> Made (CE-35). Opportunity and implication wording now follows the sheet (for example "$135.7bn", "%", "FP&A"). No values changed in the financials or the headline cards.
- Badge changes: H-04 card SIGNAL (unchanged meaning); vendors V01-V05 all SIGNAL (their sources are secondary or broker reports; before: FACT for Haitai, SIGNAL for others); opportunities O-01, O-03, O-05, O-06 SIGNAL; O-04 FACT (gov.cn primary); O-02 Hypothesis kept; H-01 card FACT.
- Checks: H-12 not shown (tested); F-00 growth n/d (tested); H-04 SIGNAL (tested); Cytiva China: SU Made from ST43 (H, primary URL, FACT in cell badge), Systems Not made, step 3 Partial, step 8 Made from CE-35 (S43) (tested)
- Full test count: 224 passed

## Owner decisions (21 Nov 2026)
- [x] Decision 3: refresh_run rows 21 and 22 deleted from data/app.db (refresh_run 22 -> 20 rows). change_log rows with run_id 21 (136) deleted in the next commit (owner instruction 21 Nov). tests/conftest.py now points refresh.DEFAULT_DB and APP_DB_PATH at a temp file for every test. Full suite: 224 passed, ruff clean.
- [x] Decision 1: China basis card built from H-01 and H-02 (metrics/china.py basis_sentence; typed "11% of $24.6bn" removed). Display change only. Tests: 2 added. Full suite: 226 passed.
- [x] Decision 2 (superseded 21 Nov): the applications sheet now exists. Ranking tab exported to data/technology/sheet/ranking.csv (120 rows) and loaded by load_apps as Hypothesis with the sheet's scoring confidence. apps.csv deleted. Diff before the switch: the 13 old rows match the sheet on every field; the sheet adds 107 rows. Audit row 22 and seed-sheet table updated.
- [x] change_log: 136 rows of run 21 deleted (3786 -> 3650).
- [ ] Applications tab export: BLOCKED. The tab has an active filter on column G ("Ad mentions 22 Oct 2026") that hides 34 rows from the CSV endpoint (values "0", "Seen (22 Oct scan)", "Not counted ..."). The script skips it (SKIPPED in the log) and the committed applications.csv is unchanged. The committed file was copied from tool output (136 rows, old 16-column layout), which the owner's rule no longer allows. The live tab now has 27 columns. Needed from the owner: clear the filter on the Applications tab (view setting, not changed by me), or approve a read-only API key for the script. Tile 2 scope rule (B) waits on this file.
- [x] Notes tab (applications sheet, 37 rows) exported by the script to data/technology/sheet/notes.csv and loaded into screen_notes (tab "Applications list notes", source_url empty like the other curated notes). Test: tests/test_apps.py.
- Export script: scripts/export_seed_sheets.py (config of 8 sheets and tab-to-file map; GET only; normalised CSV so an unchanged sheet gives identical bytes; logs to data/sheet_exports.log). Re-export of ranking.csv: parsed values and bytes identical to the committed file (0 differences). The earlier "on-disk change" was a tool-output copy with different quoting, now gone.
- gviz quirks found: forced headers=1 (without it the first data row merges into the header); Drive export=csv needs sign-in (307), so gviz is the only anonymous route.

## Screen 5: technology
- Live tabs (spreadsheet 1Io-Abom...): T1 End of support; T2 Incidents 30 days; T2 Watchlist; T2 Feeds (not yet read); T2 Rules (not yet read); T3 Integration readiness; T4 Adoption signals (+ Gartner section below it); T5 Implications; Estate evidence; Sources.
- The applications list (apps.csv, used by EOS tile ranking) is not on a live tab: keep the CSV and flag it.
- [x] Exports: all 10 tabs exported by the script to data/technology/sheet/ (eos 10 rows, 15 columns with M/N/O; sources 43; estate_evidence 12 rows, not the 11 expected: to check; rules is new, not loaded; incidents, watchlist, feeds, integrations, adoption, implications written too).
- [x] Loader: switched (this commit). Header map per tab in src/ingest/technology.py (HEADER_MAPS, ordered, exact match; any unmapped or changed header fails the load). Reads data/technology/sheet/. Gartner: its own section of the adoption tab, loaded once (10 rows, tests). Estate evidence: ID pattern EST-\d+ with fullmatch, so the Gap row is not a row: it goes to screen_notes (tab "Estate evidence"). EST count 11. Sources 43. Notes from the tabs and the README go to screen_notes (replaces screen_notes.csv). Old top-level technology CSVs removed (git rm).
- [ ] Metrics: tile 1 (show_on_tile column M) and tile 2 (security) not yet built.
- [ ] Metrics
- [ ] Screen
- [ ] Tests
- [ ] Commit

## Screen 3: customer clusters
- [ ] Exports
- [ ] Loader
- [ ] Metrics
- [ ] Screen
- [ ] Tests
- [ ] Commit

## Screen 4: demand drivers
- [ ] Exports
- [ ] Loader
- [ ] Metrics
- [ ] Screen
- [ ] Tests
- [ ] Commit

## Screen 1: overview (includes Clario check)
- [ ] Exports
- [ ] Loader (replaces layoffs.py, company_deals.py, rankings.py, annual_reports.py literals)
- [ ] Metrics
- [ ] Screen
- [ ] Tests
- [ ] Commit
- Clario check: MA-04 completed 2026-03-24 (S18)

## Afterwards
- [ ] Audit section 8 update (docs/refactor-audit.md)
- [ ] Full baseline (tests, AppTest render of all six screens)

## Screen 2 and 6 re-export (21 Nov 2026, not committed)
Re-exported with the script. Value diff against the committed files (parsed, by row):
- China companies 19 -> 21 (C00 Cytiva in China added; C03 Bestchrom and C07 Duoning dropped from the Yes/No list; C05 OPM added); coverage_evidence 35 -> 37; coverage_grid 19 -> 23 rows, header unchanged in the first six columns but the loader header 'Sys (systems; bioreactors)' no longer matches; financials 12 -> 18; headline 12 -> 13; implications 5 -> 5 (I-01 and I-02 text changed; I-04 added, I-05 kept); opportunities 6 -> 8; sources 46 -> 46 (S01, S03, S19, S34 new; S10, S11, S28, S41 gone); vendors 5 -> 7.
- Coverage peer_sites 47 -> 48 (PS-07, PS-22 added; PS-06, PS-12 gone, others changed); register_sites 55 -> 55 (ST25 text changed); sources 20 -> 20 (S19 is now the internal register, S12 added, S02 and S18 gone); t1_coverage_grid 9 -> 12 (Cytiva column and key rows added); t4_region_cards header changed (the loader expects Region, Biotech sales, Source IDs, Confidence, Sales evidence; the sheet now has six columns including cytiva families and steps, and the region rows changed, e.g. Western Europe 726 with 5 families).
- New tabs not loaded: T2 Steps local (11), T3 Supplier revenue (9), T3 Market size (6), register Legal entities (57), Value-chain coverage (6), Entity-site links (39), register Sources (5).
Result: the re-export breaks the loaders (china.py:212 KeyError 'Sys (systems; bioreactors)'; coverage.py:358 KeyError on the T4 source column). Tests: 16 errors and failures in test_china and test_coverage. The committed screen 2 and 6 files were restored, so HEAD is green. To apply: add a header map for each of these tabs (as for screen 5), then update the pinned figures and tests and list each display change. Not done in this step.

## Applications list (still blocked)
- Checked on 21 Nov 2026: the basic filter on the Applications tab is still in place (column G hidden values). No saved filter view exists yet. Re-export after the owner confirms the view is saved and the filter is removed.
