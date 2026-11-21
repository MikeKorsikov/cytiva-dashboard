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
- [x] Decision 3: refresh_run rows 21 and 22 deleted from data/app.db (refresh_run 22 -> 20 rows). Note: change_log still holds 136 rows with run_id 21 (not touched; needs an owner call). tests/conftest.py now points refresh.DEFAULT_DB and APP_DB_PATH at a temp file for every test. Full suite: 224 passed, ruff clean.
- [x] Decision 1: China basis card built from H-01 and H-02 (metrics/china.py basis_sentence; typed "11% of $24.6bn" removed). Display change only. Tests: 2 added. Full suite: 226 passed.
- [ ] Decision 2: apps.csv flagged as not in a seed sheet; SIGNAL at most (not started)

## Screen 5: technology
- Live tabs (spreadsheet 1Io-Abom...): T1 End of support; T2 Incidents 30 days; T2 Watchlist; T2 Feeds (not yet read); T2 Rules (not yet read); T3 Integration readiness; T4 Adoption signals (+ Gartner section below it); T5 Implications; Estate evidence; Sources.
- The applications list (apps.csv, used by EOS tile ranking) is not on a live tab: keep the CSV and flag it.
- [ ] Exports (in progress: eight of ten tabs read; Feeds and Rules still to read)
- [ ] Loader
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
