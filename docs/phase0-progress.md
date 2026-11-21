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

## Export defect found 21 Nov 2026 (blocks applications, screens 2 and 6)
- The public CSV endpoint (gviz) returns blank cells for text in columns that also hold numbers. The sheet has the values; the export does not. Checked: H Headline figures H-05 Value "Low single-digit decline" (live) comes back blank; H-06 and H-07 too; financials F-00 Code "DHR" and Revenue YoY "n/d" blank. JSON output (tqx=out:json) blanks the same cells, and a retry after waiting gave the same result. Applications column G ("Ad mentions 22 Oct 2026") has 82 of 136 cells blank, for example Oracle E-Business Suite "2 (plus 25 generic Oracle)" and SolidWorks "20 (CAD total)". Text-only columns (for example Confidence (H/M/L)) match the committed file for all 136 rows.
- The filter is gone; the saved view "Hide apps with no ad mentions" exists. The 136 rows and 27 columns are exported correctly (11 columns have blank headers and no data).
- Decision: nothing with blanks is committed. The screen 2 and 6 exports and applications.csv are restored to the committed versions. The 27-column applications export is kept outside the repo, at C:\Users\nikol\AppData\Local\Temp\applications_export_27col.csv, for review.
- Fix needed: read the sheets through the Sheets API (read only, as in the planned service account), not the CSV endpoint. This is the same access change already recorded in the audit (sharing / access).

## Screen 2 and 6 counts by ID pattern (new export, not committed)
- Peer sites: 47 PS rows + 1 Note row. Register sites: 51 ST rows + 4 note rows.
- China coverage grid: 19 company rows + Key, Key, Finding, Change log. Companies: 19 + 2 Note. Coverage evidence: 35 + Mockup differences, Gap. Financials: 12 + Not available (2), Not collected, Note (2), Parameter. Headline: 12 + Note. Opportunities: 6 + 2 Note. Vendors: 6 + Finding, Note. Implications: 5. Sources: 46 (China), 20 (coverage).
- Header changes: coverage grid "Sys (systems; bioreactors)" becomes "Sys (systems, bioreactors)" (plus an empty column). Peer sites: one extra empty column. Coverage sources: extra Type column. China sources: extra Notes column in the export. Companies, coverage evidence, implications and opportunities: list separators changed from ";" to ",".
- Real data changes that cannot be trusted until the blanks are fixed: H-05, H-06 and H-07 values, F-00 fields, and any cell in the mixed columns above.

## Export switch (21 Nov 2026, owner instruction)
- Export script now reads sheet IDs and gids from seed_sheet_gids.yaml (repo root) and uses the plain export URL (export?format=csv&gid=). The gviz endpoint is no longer used. PyYAML added as a dependency (uv add pyyaml).
- Verified after the switch: applications Oracle E-Business Suite column G = "2 (plus 25 generic Oracle)", SolidWorks = "20 (CAD total)"; screen 6 H-05, H-06, H-07 values and F-00 Code "DHR" and Revenue YoY "n/d" are no longer blank. Trailing columns with no header are dropped, so the applications export is 136 rows and 16 columns.
- Applications list: the saved view is in place and the basic filter is gone. Full export committed.
- Exports not taken: register Legal entities, Entity-site links and Sources. Export only: screen 2 T2 Steps local, register Value-chain coverage.
- Separators: family and source-ID parsing accepts both ";" and ",". Test added.

## Screen 2 and 6 header maps (src/ingest/sheet_headers.py)
- Every export that a loader reads goes through a header map: an unmapped or missing header fails the load. Mapped: china (companies, coverage evidence, coverage grid, financials, headline, implications, opportunities, sources, vendors), coverage (sources, peer sites, register sites, T3 market size, T3 supplier revenue, T4 region cards).
- "Sys (systems, bioreactors)" is mapped to the loader key "Sys (systems; bioreactors)".
- Coverage grid: only the eight product families are read (blank line and the Key, Regions and Cytiva column notes are skipped). The grid rows are identical to the committed load.
- Peer sites: only PS- rows are read (the Note row is skipped).
- T4 region cards: sales source and confidence come from the "(sales)" part of Source IDs and Confidence; rows without a sales figure are skipped.

## Tile 3 inputs now loaded (screen 2)
- s2_market_size: MS-01 to MS-03 (3 of 6 sheet rows; the other rows are recommendation, check and not-used notes).
- s2_supplier_revenue: SR-01 to SR-06 (6 of 9 sheet rows; the other rows are a total, a parameter row and a note). Thermo Fisher has no USD figure in the sheet, so it is stored with NULL.
- Not shown on the screen yet: the tile 3 display decision (BUG-13) is still open.

## Counts by ID pattern (loaded, after the fix)
- s2_grid 73, s2_peer_site 47, s2_cyt_site 51, s2_biotech_sales 4, s2_source 20. cn_coverage 41, cn_company 19, cn_coverage_evidence 35, cn_financial 12, cn_headline 12, cn_vendor 5, cn_opportunity 6, cn_implication 5, cn_source 46. All equal to the committed loads.

## Still open
- Tile 1 (show_on_tile column M), tile 2 (security, scope rule and order), screens 3, 4 and 1 (Clario check), audit section 8, baseline.
- Screen 3, 4 and 1 exports exist in data/ (clusters, demand, overview) but no loader is written for them yet.

## Screen 5 tiles (commits d551a1e / 451ba28, e80384d, f828b71)
- Tile 1: columns "Application" and "End of support". Shows Show on tile = Yes rows only (EOS-01, EOS-02; was 7 rows). Tile note under the date; status chip; confidence badge.
- Tile 2: title "Security issues in apps we use · last 30 days". Applications list loaded to tech_app_list (Name key, header map). Scope: list Confidence H or M; the lower of the list and any Estate evidence or Watchlist row that names the application (core name match, vendor word removed). In scope: 117 of 136 apps (96 M, 23 H, 17 L out). Matching: exact when the core name appears in the incident product text, vendor-level when only the vendor matches; exact ranks first, then relevance, then size plus complexity. Sheet result: INC-03 shown (vendor-level, Microsoft Azure); 5 more awaiting confirmation.
- Known gaps (decision needed): (1) estate and watchlist text uses abbreviations, e.g. EST-04 "Oracle EBS", that the name match does not link to "Oracle E-Business Suite"; (2) the sheet marks INC-03 (Outlook) "Exact", but no application named Outlook exists, so the tile shows the vendor-level app Microsoft Azure; (3) the tile now lists corroborated rows only and counts pending rows in the line "N more awaiting confirmation" (display change, agreed line).
- Full suite: 239 passed.

## Screen 3 (not started as a loader)
- Exports exist: data/clusters/sheet/ (8 tabs: Clusters, Country barriers, Demand by country, Demand by region, Research institutions, CDMO sites, Market signals, Data Sources).
- The loader (src/ingest/clusters.py) still reads the old top-level data/clusters/*.csv (clusters, cdmo_sites, market_signals, country_barrier, country_profile). The sheet's tab names and headers differ (for example Country barriers has 'LPI score 2023' and the entry-barrier columns; there is no country_profile tab). Needed: a header map per tab, a mapping to the table fields, and a display check. Not done.

## Screens 4 and 1, audit section 8, baseline: not started.
