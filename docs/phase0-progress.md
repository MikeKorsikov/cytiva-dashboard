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

## Screen 4: demand drivers (done, commit 4fae85a)
- [x] Exports: data/demand/sheet/ (8 tabs + Sources). T4 was truncated to column A by the exporter; fixed in 1ca0ce5 (normalise() used row 0's width).
- [x] Loader: src/ingest/demand.py through section maps (sheet_headers.read_tab, SECTION_TABS). T2 checked by position (check_t2_header). Clears and reloads the demand tables.
- [x] Metrics: src/metrics/demand.py (2024 ranking; approvals filtered on period 2025; comparable vs other pipeline counts)
- [x] Screen: src/app/shells.py demand_screen; product matrix removed (tile 8 hidden, Hypothesis, awaiting confirmation)
- [x] Tests: tests/test_demand.py (17 tests, incl. changed-header and missing-section failures, legacy implications)
- [x] Legacy: docs/phase0-screen4-legacy.md (implications text; failing-when-fixed test)
- [x] Old CSVs removed (git rm): data/demand/approvals, burden_country, capacity, expiries, pipeline_type, policy, product_use, top_drugs
- Row counts (app.db, before -> after): demand_burden 19 -> 20; demand_pipeline 8 -> 14; demand_approval 8 -> 10; demand_expiry 4 -> 4 (Ocrevus rejected); demand_policy 6 -> 6; demand_top_drug 15 -> 15; demand_capacity 16 -> 16; demand_product_use 5 -> 5. Notes on screen_notes for the demand tabs: 17.
- Row counts by ID pattern: n/a (no ID column on demand tabs; counts are by tab section)
- Display changes: 2024 ranking (Indonesia in, France out, Brazil and Russia swap); DALYs and NA diabetes show to collect; approvals show period and 2026 YTD rows; "other pipeline counts" table added; product matrix hidden (awaiting confirmation).
- Badge changes: product use HYPOTHESIS (was a matrix with no badge rule); other tables unchanged (Fact or Signal by confidence L).
- Full test count at last run: 258 passed. ruff check and format clean.
- Note: the demand loader's schema migration also migrated country_demand, country_barrier_index and tech_* tables in app.db; rows kept, no migration log written for that step.

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

## Tile 2 link rule (commit 2042474)
- Link columns from the sheet (applications-list Names, ";"-separated): T2 Watchlist "Applications (list Name)", T2 Incidents "Application (list Name)", Estate evidence "Applications (list Name)". Re-exported.
- Every link value matches a Name in the applications list. Blanks: W11 Teradata and W14 Figurate (by decision; Teradata to be added to the list if still used).
- Match type: the sheet's Product match flag, as given (INC-03 is Exact under Microsoft 365 (Teams)).
- Lower-of rule: INC-03 and INC-05 are scope L (list M, watchlist W12 L). Hidden by default; shown as UNCONFIRMED with "Show unconfirmed (L)" on.
- Default tile: empty state plus "4 more awaiting confirmation" (INC-01, INC-02, INC-04, INC-06). Display change, listed in the commit.
- Full suite: 241 passed.

## Screen 3 (stopped here: low context)
- Exports: data/clusters/sheet/ (8 tabs), re-exported by the script.
- Loader still reads the old top-level data/clusters/*.csv (clusters, cdmo_sites, market_signals, country_barrier, country_profile) with snake_case names. Not switched.
- Gap 1 (decision needed): the new Country barriers tab has no Tholos Trade Barrier Index column and no applied-tariff percentage or tariff year. The current screen shows Tholos beside the barrier index and the tariff figure. Switching would remove those values from screen 3. Owner to decide: keep the old source for those two, or drop them.
- Gap 2: Country barriers has "Display on tile" (the audit's item 9); the loader does not read it yet.
- Gap 3: Demand by country and Demand by region have 24 and 13 columns; the old loader's country_demand came from country_profile.csv, which the sheet no longer has as a tab. Mapping needed per column.
- Gap 4: the barrier index the sheet computes (Entry barrier index, Scores available) must be compared with the app's own average before switching; a difference is a display change.
- Header maps per tab: not written. Plan: one HEADER_MAPS entry per export (as for screens 2 and 6), fail loudly on unmapped or missing headers.

## Screens 4 and 1, audit section 8, baseline: not started.

## Screen 3 (switched to the sheet, 22 Nov 2026)
- Loader reads all eight tabs through header maps (src/ingest/sheet_headers.py). Unmapped or missing headers fail the load.
- Counts loaded: cluster_fact 30 (F001 to F030); cdmo_site 35 (CD01 to CD35; note row excluded); market_signal 13; country_demand 28 countries; country_barrier_index 11.
- Every stored row has a source URL. Barrier rows take the URL of their first Source ID (Data Sources tab); before, every barrier row carried the tariff URL (B-03 for barrier rows fixed). Demand rows still carry the Nature Index URL for all columns (B-03 open for demand: the tab has no per-column source).
- Not stored (read and validated only): Demand by region, Research institutions, Data Sources (used for URLs only).
- Legacy exception (owner decision): Tholos 2025 score and URL, applied tariff %, tariff year, tariff score (1/3/5), direction of each market signal, and cluster fact scope. Read from data/clusters/country_barrier.csv, market_signals.csv and clusters.csv. Marked LEGACY in code; badged SIGNAL on the barrier table headers. Test test_legacy_exception_ends_once_the_sheet_has_the_columns fails when the sheet has the columns. Details: docs/phase0-screen3-legacy.md.
- Deleted (superseded by the sheet): data/clusters/cdmo_sites.csv, data/clusters/country_profile.csv.
- Barrier index: the app keeps its average of customs, tariff (legacy) and local preference over the scores present. The sheet's own index (kept as sheet_barrier_index) uses different dimensions and differs for 11 of 11 countries; the largest gaps: China 3.93 vs 4.5, South Korea 2.63 vs 1.5, US 1.75 vs 2.5 (list in the commit message).
- Display on tile: the sheet's text is shown under each partial index ("Partial index: n of 5 scores"; China shows Index). New on screen.
- Percent values: "17%" and "33%" (F005, F019) and "27%", "36%", "11%" (M06, M07, M12) are read as numbers. A first version dropped them; fixed before the commit; test added.

### Display changes on screen 3 (from the sheet updates)
- Cluster facts: F005 and F019 are numbers now (17 and 33, share); metric wording changed in 6 facts (no value change).
- Market signals: M13 value 0.86 becomes 1 (R&D spending, China vs US); M06, M07, M12 now read as %; wording in M01, M10, M13.
- CDMO sites: capacity CD06 330,000 becomes 332,000; CD12 becomes 6,000 (was blank); CD22 becomes 23,000 (was blank); CD25 becomes blank (was 16,000). Confidence L becomes M for CD12, CD14, CD17, CD20, CD22, CD25. CD35 is new. Status text changed in 12 rows.
- Barrier table: partial-index notice (10 countries); legacy SIGNAL badges on the Tariffs and Tholos columns.

## Still open
- Screens 4 and 1 (Clario check), audit section 8, full baseline: not started.
- Decisions needed from the owner: (1) the barrier index: keep the app's three-dimension average or switch to the sheet's index (values differ for all 11 countries); (2) Demand by country: the Nature Index column is 2025 now, the table column was 2024; the table is not displayed, so no visible change.

## Numeric columns and displayed-value check (22 Nov 2026)
- M13 re-exported: the cell reads 0.86 now (the sheet format was changed to 0.00 by the owner).
- Check: `uv run python -m scripts.check_sheet_numbers` lists the numeric columns of every exported tab and flags a numeric cell that equals a number its own row quotes only after rounding (the M13 case). Read only.
- Tabs with numeric columns (for the owner's number-format check):
- data\china\sheet\coverage_grid.csv: — numeric columns: Families evidenced
- data\china\sheet\financials.csv: — numeric columns: Revenue (RMB m), Revenue (USD bn)
- data\clusters\sheet\cdmo_sites.csv: — numeric columns: Capacity (L)
- data\clusters\sheet\clusters.csv: — numeric columns: Value
- data\clusters\sheet\country_barriers.csv: — numeric columns: LPI score 2023, LPI rank 2023, LPI customs score 2023, LPI customs rank 2023, Customs friction (1 low to 5 high), Trade measures (1-5), Local preference (1-5), Regulatory friction (1-5), Geopolitical risk (1-5), Entry barrier index (average of available scores), Scores available (of 5)
- data\clusters\sheet\demand_by_country.csv: — numeric columns: Academia and government research: Nature Index Share 2025 (biological sciences, 2026 edition), Top-100 research institutions: academia (2026 edition), Top-100 research institutions: government labs (2026 edition), R&D spending, all sectors (GERD, PPP $bn, 2021), Big pharma and generics: FDA-catalogued drug sites FY2024, Biotech and pharma: share of R&D companies by HQ (2026), Biotech therapeutics companies (Biotechgate), Biotech R&D services companies, incl. CROs (Biotechgate), CRO and clinical demand: trial registrations since 2019 (WHO), Interventional trials starting 2025 (ClinicalTrials.gov, not yet verified), CDMOs: biologics sites listed, CDMOs: listed capacity (L), Segments with evidence (of 6), Norm. research, Norm. pharma sites, Norm. biotech, Norm. R&D services, Norm. CDMO sites, Demand score (0-1, average of available norms), R&D spending, all sectors (GERD, PPP $bn, 2024, OECD MSTI Mar 2026)
- data\clusters\sheet\demand_by_region.csv: — numeric columns: Countries tracked, Academia and government research (Nature Index Share 2025), Share of tracked research, Top-100 institutions: academia, Top-100 institutions: government labs, FDA-catalogued drug sites (big pharma, generics), Share of tracked drug sites, Biotech therapeutics companies (Biotechgate), Biotech R&D services companies (Biotechgate), CDMO biologics sites listed, CDMO listed capacity (L)
- data\clusters\sheet\market_signals.csv: — numeric columns: Value
- data\coverage\sheet\register_sites.csv: — numeric columns: Linked entities
- data\coverage\sheet\t3_market_size.csv: — numeric columns: Value (USD bn), Year
- data\coverage\sheet\t3_supplier_revenue.csv: — numeric columns: FY2025 revenue (reported currency, m), FY2025 revenue (USD m), Share of disclosed peer pool
- data\coverage\sheet\t4_region_cards.csv: — numeric columns: Cytiva steps local (of 8), Biotech sales Q1 2026 ($m), Share of Biotech sales
- data\demand\sheet\t1_disease_burden.csv: — numeric columns: New cancer cases 2022, New cancer cases 2024 (GLOBOCAN 2024)
- data\demand\sheet\t3_pipeline_by_type.csv: — numeric columns: Previous value, Change
- data\demand\sheet\t6_biggest_drugs.csv: — numeric columns: Sales FY2025, USD bn
- data\overview\sheet\t1_peer_financials.csv: — numeric columns: Revenue (m), Revenue growth, reported %, Gross profit (m), Net income (m), Operating cash flow (m), Free cash flow (m), Revenue (USD m), Gross margin %, Net margin %, FCF margin %
- data\technology\sheet\competitors.csv: — numeric columns: Ad mentions, Ads scanned
- data\technology\sheet\incidents.csv: — numeric columns: Tier A sources (n), Tier B sources (n), Relevance (0-7), Days old
- data\technology\sheet\ranking.csv: — numeric columns: Rank, Size (1-5), Complexity (1-5), Score (size + complexity)
- Flags on this run (cell shows a rounded value of a quoted number; fix the sheet format, then re-export):
- data\china\sheet\financials.csv | F-09 | Gross margin %: cell '42.4' rounds the quoted 42.42
- data\coverage\sheet\t3_market_size.csv | MS-02 | Value (USD bn): cell '11.1' rounds the quoted 11.13
- data\demand\sheet\t6_biggest_drugs.csv | 5 | Sales FY2025, USD bn: cell '17.56' rounds the quoted 17.562
- data\demand\sheet\t6_biggest_drugs.csv | 9 | Sales FY2025, USD bn: cell '13.54' rounds the quoted 13.542
- Screen 2 and 6 numeric flags: none. Screen 4: t6 "Sales FY2025" two cells (rows 5 and 9). Screen 3: F-09 gross margin is on screen 6 (China financials).

## Re-export after the number-format fix (22 Nov 2026)
- All eight sheets re-exported (59 tabs). check_sheet_numbers: 2 flags, not 0. The two flags are T6 "Sales FY2025, USD bn", rows 5 (Skyrizi, 17.56; quote 17.562) and 9 (Zepbound, 13.54; quote 13.542). The owner's note says these cells were fixed; the export still shows them rounded. Only the Tirzepatide total (36.51 -> 36.507) changed in T6. Needs a check of those two cells' format.
- Trailing bare dot: several cells now read "5,763." or "735." (F-04 revenue, F-05, F-06, F-07, F-08, F-08b, net profit cells). The value parses as a number, but the sheet shows a dot with no decimals. Owner to fix the format.
- Tabs with changed cells: china financials (30 cells), clusters demand_by_country (141) and demand_by_region (14), coverage t3 market size (2), t3 supplier revenue (10), t4 region cards (4), demand t3 pipeline (1), demand t6 (1), overview t1 peer financials (23).
- Screen 2 value changes (displayed): none in the displayed figures. Tile 3 inputs change at the decimal level (MS-02 11.1 -> 11.13; MS-03 17.7 -> 17.6985; SR-02 USD m 3,237 -> 3,237.45; supplier shares to 4 decimals; SR total 17,699 -> 17,698.5). Tile 3 is "to collect" on screen, so nothing on screen changes. T4 shares to 4 decimals (not displayed); biotech sales (value m) unchanged.
- Screen 3 value changes (displayed): none. Demand by country values change to 4 decimals (Nature Index 0.89 -> 0.8877; GERD and counts), but country_demand is not displayed. Barrier, CDMO, cluster and market tabs are unchanged in this export.
- Screen 5 value changes: none (technology tabs unchanged).
- Screen 6 value changes (displayed, all at the decimal level): F-01 revenue 924.7 -> 924.69, YoY 18.2 -> 18.18, gross margin 71.3 -> 71.31, net profit 136.0 -> 136.01; F-02 gross 50.9 -> 50.85, R&D 13.6 -> 13.63; F-03 revenue 5,232.9 -> 5,232.92, YoY 4.5 -> 4.45, gross 29.4 -> 29.35, R&D 6.5 -> 6.45, net 200.4 -> 200.38; F-03b YoY 29.8 -> 29.84; F-04 YoY -1.1 -> -1.14, gross 32.2 -> 32.23, net 255.0 -> 255; F-05 net 59.7 -> 59.65; F-06 YoY 27.7 -> 27.73, R&D 13.7 -> 13.67, net 126.5 -> 126.54; F-07 YoY 40.5 -> 40.52; F-08 net 14.3 -> 14.26; F-09 gross 42.4 -> 42.42. Largest move: F-03 net profit 200.4 -> 200.38 and F-08 net profit 14.3 -> 14.26 (0.04). Full suite: 246 passed.

## Sheet fixes confirmed (22 Nov 2026, second re-export)
- check_sheet_numbers: 0 flags. T6 Skyrizi 17.562 and Zepbound 13.542 (were stored rounded).
- No cell in any exported tab ends in a bare dot.
- Number parsers: china _num, clusters _num and the coverage market-size reader accept values with and without thousands separators, and percent signs (test_sheet_numbers_parse_with_and_without_separators_and_percent).

## Exporter fix (commit 1ca0ce5)
- normalise() now keeps every used column (width = last value in any row). Before: tabs whose row 0 was a one-cell title lost their other columns. Re-export changed: demand T4 (full), demand T2 (second ranking), technology readme.csv (now loaded: 20 README notes on screen_notes, was 0), register_value_chain.csv (export only).
- Screens 2, 3, 5 and 6 loaded tabs: unchanged. Confirmed by name.
- Full test count: 247 passed (before screen 4).

## Screen 1: overview (done in part, commit 6fe5484)
- [x] Exports: data/overview/sheet/ (8 tabs + Sources) (existing exports, unchanged)
- [x] Header maps: OVERVIEW_TABS in src/ingest/sheet_headers.py for all eight tabs (read through read_tab, tests/test_overview_sheet.py)
- [x] Loader: company deals from the T2 M&A tab (sheet_deals); rankings from the T1 Rankings tab. Literals removed: COMPANY_DEALS, DEAL_VALUE_USD_M, CURATED_RANKINGS.
- [x] Clario check: MA-04 completed 2026-03-24, cited to S18
- [x] Legacy: docs/phase0-screen1-legacy.md (layoffs, annual_reports REPORTS config, Danaher 10-K notes; all Signal at most)
- [x] Switched (22 Nov 2026, review round): attention display (AT-01 to AT-05), T1 Peer financials (Basis badge per row), T3 Share prices (awaiting feed), T4 Competitor news (seed items), T5 Implications (Hypothesis). Loader: src/ingest/overview_sheet.py (ov_* tables). Old paths removed: financials.py, annual_reports.py, tenk_text.py, metrics/fundamentals.py and their tests; financial_metric cleared (117 rows). The price and news feeds (prices.py, news.py) keep running; their tables are not displayed yet.
- Row counts (app.db, before -> after): deal (company-reported, source_type document, Fact) 11 -> 6; deal total 64 -> 59; ranking (curated) 0 -> 0; screen_notes Overview M&A 3 (labels now Signal).
- Display changes: M&A counts unchanged (they match the sheet's count rows). Deals removed from the database: Danaher StatLab, Genedata, Abcam, Aldevron; Merck KGaA Silence, JSR, SpringWorks. Four re-worded deals kept.
- Full test count at last run: 265 passed.
- The deletion of company-reported deal rows is not written to change_log (direct DB load, as for screen 4).

## Audit section 8 (done, 22 Nov 2026)
- docs/refactor-audit.md section 8-status: rows 13, 14, 16, 16b, 21 updated; B-07 closed.

## Baseline after Phase 0 screens 1 to 6 (22 Nov 2026)
- Full suite: 265 passed (ruff check and ruff format --check clean).
- AppTest render of the six screens against data/app.db: 0 exceptions on each (overview 30 markdown blocks; coverage 16; clusters 16; demand 38; technology 17; china 29).
- Phase 0 is complete except the items marked open above. Stopped for review before Phase 2.

## Review round (22 Nov 2026)
- Removed deals confirmed. Attention shown. Four remaining screen 1 tabs switched. Migration record: docs/phase0-migrations.md. Legacy values: docs/phase0-legacy-values.md.
- Badges for peer financials per row (Fact where confidence H and the first source is primary): Danaher, Thermo Fisher, Repligen, Avantor, Merck KGaA (group) are Fact. Sartorius is Signal (confidence M; gross profit, net income and cash flow are secondary). The downgrade does not disappear for Sartorius, because the sheet rates the row M.
- News badges: company-issued high-confidence items are Fact (Sartorius, Repligen, Avantor); trade press is Signal (Danaher, Cytiva, Thermo Fisher, Merck KGaA).
- Full test count: 237 passed. ruff check and format clean.
- Renders: six screens, 0 exceptions (overview 44 markdown blocks).
- Open: the price and news feeds are not wired to the screen; the technology README notes are not yet in app.db.

## Phase 0 review round 2 (22 Nov 2026)
- Legacy literals moved to the sheets: layoffs (T6 Layoffs, LO-01 to LO-18), Danaher 10-K notes (T2 M&A, 3 rows, source S19), screen 4 implications (T9, I-01 and I-02). The literals are deleted. The legacy test flipped and was replaced by a sheet-based test. Layoffs and 10-K tests read the sheet.
- Feeds regression: share_price_daily and news_item were displayed before Phase 0 (the screen at 2a463d2 read them through overview.share_prices and overview.latest_news). Restored. Prices show awaiting feed where no close is stored. News shows the feed item; the sheet's seed item is used only where the feed has none, marked (seed).
- Badges: 4 layoff rows are Fact (the review expected 5; the sheet has 4 rows that are H and Primary). Sartorius stays Signal.
- Full refresh through the normal command: run 26 failed (HTTP 429 from Google News for Avantor); run 27 succeeded (2502 rows). Per-table counts in docs/phase0-migrations.md.
- Full test count: 241 passed. ruff check and format clean. Six screens render with 0 exceptions.
- Displayed changes from the refresh and sheet edits, beyond the feed items (prices and news):
  (a) Overview M&A counts: the feed's deals are now counted (Thermo 5y 10 to 9; Merck 12m 2 to 3, 5y 5 to 10; Danaher 12m 1 to 2, 5y 6 to 8).
  (b) Overview 10-K note wording (from the sheet).
  (c) Screen 5 applications ranking table now shows (it was "No items to show"), with "2 more awaiting confirmation".
  (d) Screen 4 implication text includes its area.
  (e) Wording changes from sheet edits on screens 3 and 6. No values changed on screens 2, 3 or 6.
- Phase 2 NOT started. The condition (no displayed value changes beyond items 1 and 2) is not met. Waiting for the owner's decision on (a) to (e).

## Phase 0 decisions round 3 and Phase 2 (22 Nov 2026)
- (a) M&A: counts come from the sheet's verified deals only (12 months). 5-year and licensing and collaboration columns show To collect. Feed deals are listed under "Unverified deal signals (feed)", badged Signal, and are not counted. docs/feed-deals.md lists the 62 feed deals that had changed a count.
- (b) 10-K note layout (text in column B, source in column C) accepted and documented in the t2_ma header map.
- (c) Screen 5 applications ranking: its own section, badged Hypothesis, with a "Scoring confidence" column from the sheet.
- (d), (e): accepted.
- Refresh robustness (commit 66eb161): each loader step fails on its own; the error (step, time, message) is logged in refresh_run.error; the run is "completed with errors" if any step failed. Tests in tests/test_refresh_isolation.py. Run 25 closed as aborted. Runs 23 and 24 are still "running" from earlier direct loads and are not closed.
- Bug found and fixed (commit 5e81d04): the M&A splice in 788f2fd left a doubled name (PEER_METRICSPEER_METRICS), so the overview screen raised on render. The unit tests did not render the screen. The earlier "full suite green" for 788f2fd was true for the tests but not for the screen. tests/test_render.py now renders every screen.
- Phase 2: render tests (tests/test_render.py, 6 screens) pass. Screenshots: docs/visual-baseline/ (desktop 1440x900 and phone-390 390x844, 12 PNG files, manifest.json with the last refresh, run 27). Taken with scripts/visual_baseline.py (Playwright, Chromium).
- Visual finding to review: on the 390 px layout a stray "double_arrow_right" text appears at the top left of every screen. It is an icon name shown as text (the icon font did not load). Wide tables also overflow the 390 px width and scroll sideways; not changed.
- Full test count: 255 passed. ruff check and format clean.

## Phase 2 review fixes and Phase 3 start (22 Nov 2026)
Each fix is a commit; the full suite ran before each.
1. Screen 5 tile 1 is end of support only (EOS rows with Show on tile = Yes, two columns). The ranking is off the screen; it orders tile 2. Commit 7b296a2.
2. Screen 4 tables are contained in their cards. Shared fix: every table from html_table sits in a box as wide as its card and scrolls inside it (also fixes screen 5 Integration readiness overlapping the adoption card). Commits 62e95bc, 0af0608.
3. Years show without a separator: _cell takes a year flag; render guard fails if any screen shows "2,0xx"-style years. Commit 0ba7722.
4. Screen 2 legend: "No evidence found yet (not the same as not made)". Commit 025d2d7.
5. Share prices: the awaiting-feed note only when a ticker has no stored price. Commit 58c0bdf.
6. Screen 5 adoption: Example column wraps. Commit 789980f.
7. Phones: the stray "keyboard_double_arrow_right" text came from the sidebar expand button (no sidebar in this app). Hidden in the shared stylesheet. Commits 8a94704, 8df44e4 (lint fix; the first commit's message wrongly said lint was clean).
8. Runs 23 and 24 closed as aborted, as run 25. Commit 54ff7d5.
- Withdrawn: acceptance of the screen 5 ranking on tile 1 (item 1).
- Open for review: at 1440 px the Integration readiness table now scrolls in its box, so its Interfaces column is cut at the edge. Item 6 covered only the adoption table.
- Open for review: on screen 4, the Approvals and Biosimilar tables scroll inside their cards, so their right-hand columns (Confidence, Source) are off screen until scrolled.

### Phase 3: EvidenceDrawer (started)
- src/app/ui/evidence.py: the EvidenceDrawer. An "Evidence" button on a tile opens a dialog listing every row the tile shows: the row, the value as displayed, its basis badge, its confidence and its source. A row with no public source says so.
- Wired to three Overview tiles: peer financials, layoffs, deal activity. Verified in Chromium (dialog lists all six peers).
- The unreachable technology drawer (B-08) is removed.
- Still open for acceptance check 5: the other tiles on each screen, and a drawer per row (the drawer is per tile for now).
- Full suite: 261 passed. ruff check and format clean.

## Phase 2 review round 2 and Phase 3, continued (23 Nov 2026)
Decisions applied:
- Drawer per tile, not per row. Acceptance check 5 now reads: "every displayed row appears in its tile's evidence dialog with at least one source URL, or is marked 'no public source'". Test: tests/test_evidence_tiles.py (button count per screen; every row of every tile).
- Evidence columns out of the tables (Source, Confidence). The Basis badge stays. Long text wraps. Target met: no table scrolls at 1440 px (measured in Chromium, 0 containers on six screens). Phones still scroll (agreed).
- The S/4HANA footnote is removed from the end-of-support tile; EOS-08 is a screen note only (commit cc992f4).

Done:
- Screen 5 footnote removed (cc992f4).
- Evidence button on every tile of all six screens (929bcc2, d59bc8a, 3672ed3): overview 8, coverage 5, clusters 8, demand 13, technology 5, china 8.
- Old technology drawer removed; ui/evidence.py is the only drawer.
- Tables measured at 1440 px: 0 scrolling containers on all six screens.

Not started (Phase 3, step 5 of the list): the shared components (ConfidenceBadge, UnconfirmedToggle, StatusChip, TileShell, EmptyState) as one set, consistent table names, remaining dead code, and the remaining rule breaches (section 4). Stopping here for review.

Enhancement list (owner, 23 Nov 2026):
- Screen 5 header "Data as of 2026-11-16" comes from the sheet README and is stale. Set it from the last successful refresh.
- Screen 2 market share tile (waiting on the owner's decision 9).
- News quality filter.
- Integration readiness "Interfaces" is wider than the card at 1440 px only after wrapping; re-check when the components are unified.

## Phase 2 review round 3 and Phase 3 finish (23 Nov 2026)
- Badge rule (one rule, src/domain/confidence.py): FACT only when confidence H and the source is Primary; otherwise SIGNAL; L is UNCONFIRMED. Source types come from every Sources tab (sheet_source_type, loaded first in the refresh). Screen 5 Sources now has Type; the register has Source type (column P) and Service source type (column U); both are loaded.
- Badge changes after the sheet types were loaded: screen 2 Signal to Fact (8 Cytiva rows, including the register sites); screen 5 Signal to Fact (Oracle EBS end of support, Oracle is Primary); screen 6: the Cytiva Beijing row ST43 is Fact (H, primary register source). Screen 4 and clusters changed in the earlier commit (61 Fact to Signal).
- Layoffs: the sheet's Confidence is stored (layoff_year.confidence); the cells and their drawer follow the rule and the L toggle; the walk test covers them.
- Tile badges: Integration readiness and Adoption signals (tile_box), in addition to screens 4 and 5.
- Dead code: 14 functions with no references removed. The repair of a bad first pass is in the commit.
- Full test count: 292 passed.
- Not done: consistent table names; tile boxes on overview and screens 2, 3, 6; the open rule breaches (see audit section 4).

## Phase 3 finish, round 4 (23 Nov 2026): stopped for review

Commits on CD-61-visibility:
- 8a98143: B-24. No module in src/app, src/metrics or src/domain imports src.ingest. 293 tests passed.
- 4957f25: tile badges on every overview, screen 2, screen 3 and screen 6 tile; shared chip and badge helpers; report-only quote and YoY checks. 293 tests passed.

Dead-code change (verified before this round): 14 functions removed, with no other change to the module-level code (AST comparison against ee92a29 and the removal commit 8913537; git diff --stat 129 deletions, 15 insertions across the five files). A content-based repair put back the signatures that the first removal pass had left at column zero. A pixel diff of the screenshots against 2c76697 found only: the Danaher 10-K note link text ("Danaher FY2025 10-K" to "source", B-19); the overview layoff cells hidden as "?" for L rows (the L rule); news rows changed by the feed refresh; technology tile and row badges and reflow.

B-24: moved CNY_USD_RATE and FAMILY_NAMES to src/domain/china.py, the region codes to src/domain/regions.py, LISTED_PEERS and ListedPeer to src/domain/peers.py, summarise to src/metrics/prices.py and the source-type query to src/metrics/source_types.py. Loaders import from domain. tests/test_layers.py fails if a screen, metric or domain module imports ingest. Test imports updated (test_coverage, test_prices, test_china, test_badges).

Tile badges: tile_box on the overview tiles (peer financials, rankings, deal activity, attention, news, implications; layoffs was done earlier), screen 2 (product families, steps, market size, implications), screen 3 (hubs map, end-market demand, top hubs, barrier index) and screen 6 (basis, financials, vendors, coverage, opportunities, implications, China data). Rows record their label: the rule for news, coverage, signals and barrier rows; record_label and stored_label_badge for hypotheses and attention items (no confidence to apply the rule to). Walk test: stored labels must be a known label; every other row follows the rule.

Copies replaced or deleted: _heat (status_chip), the overview _badge (badge_html), _badge and _CHIP (shells, no callers), _fact_and_signal and _cn_mixed_title (hard-coded section badges), the hard-coded section badges on screens 2, 3 and 6. Not replaced: the KPI card heading markup, _region_tag and the region cards, and the Fact and Signal title text on the overview deals note.

Report-only checks (B-05, B-06): scripts/report_checks.py reads data/app.db read only and writes docs/check-report.md. Quote check: 75 rows whose number is not in its evidence text (s2 biotech, market size, supplier revenue, China headline, demand pipeline and capacity, market signal, cluster fact, CDMO sites). Some are column mismatches: the evidence cell is a note, not a verbatim quote. YoY and growth: 0 rows over 50%. Not checked: cn_financial, ov_financial and revenue_observation have numbers but no quote column. Nothing is enforced.

Acceptance (audit section 12): check 1 passes (293). Check 3: screenshots re-taken; demand and technology pixel-identical to the previous baseline; overview, screen 2, screen 3 and screen 6 differ only in tile badges and the removed SIGNAL badge on the market size tile. Check 4 still fails (B-12, B-14, B-15, B-16, B-18, B-20 open; B-17 partly). Check 5 passes by test with B-04 as the rule decision. Check 7: lint and format pass; no type check configured. Check 2 not run.

Not done:
- Consistent table names across screens (one prefix per screen, sources, row_sources, screen_notes, a confidence enum). Roughly 90 tables and every SQL string in ingest and metrics. No migration was written this round, because no table or column changed in this round. docs/phase0-migrations.md is unchanged. Needs the owner to approve the mapping first.
- Check 2 (import twice, same row counts).
- The B-10 stored-label loaders (clusters, China, technology set the stored label without the source type).

Decisions needed from the owner:
1. M&A deal counts (screen 1). The sheet gives T2 deals no confidence, and the loader stores them as Fact. Under the rule they are Signal unless the sheet gives H. Keep as Fact (the sheet is the source) or move them to Signal?
2. Attention items (screen 1) have no confidence column; they keep the sheet's evidence label. Same question.
3. Coverage hypotheses are still typed in screen 2 (B-17). Move to the sheet?
4. B-05 and B-06: approve enforcement (decision 11) after reading docs/check-report.md. The 75 quote rows include column mismatches to fix first.
5. The table rename mapping (see the not-done list).
6. B-01: confirm closed (no literal of the four biotech figures remains).

Stopping here for review.

## Owner decisions applied (23 Nov 2026), stopped for review

Commits: e6dc46b (299 tests passed); this round's docs and screenshots follow in the next commit.

1. M&A counts: derived, not stored as Fact. Each sheet deal (T2 M&A) stores its Confidence (column K) and the type of its first source; the badge is the rule. A company's count badge is the weakest badge of its 12-month deals, shown in a Basis column. Result: Danaher 1 deal, Fact; Merck KGaA 1, Signal; Repligen 1, Signal; Thermo Fisher 0 in 12 months (2 deals in the sheet, both outside the window); Sartorius 0. The drawer link stays the completion source for completed deals, as before.
2. Attention: the rule on the sheet's Confidence (J) and Source type (K). AT-01, AT-02, AT-03 Signal; AT-04, AT-05 Fact. AT-01 and AT-03 change from Fact to Signal.
3. B-17: screen 2 hypotheses are the sheet's T5 Implications (gid 14), loaded into s2_implication, always Hypothesis. Typed text deleted. The exporter config and seed_sheet_gids.yaml include the tab.
4. B-06 enforced in the refresh (apply_growth_checks): growth above 50% is stored unverified and logged. 0 hits. B-05 quote check rewritten to rules (a) to (d); report: 2 would fail (cn_headline rows 10 and 11, real mismatches), 11 data gaps (top drugs and pledges), 7 derived, 91 not verbatim (no quote marks, not checked). Not enforced.
5. Table renames: not done. Convention and proposed mapping written in audit section 13 (deferred). New table s2_implication follows the convention. No rename migration.
6. B-01: confirmed closed.

Acceptance check 2: refresh run twice on a copy of data/app.db; 85 tables, identical counts; 2,717 rows each run. Passes.

Migrations (docs/phase0-migrations.md, run 34): deal +confidence, +source_type_text (69 rows kept); ov_attention +confidence, +source_type_text (5 kept); s2_implication new (2 rows). Refresh run 34 succeeded.

Screenshots re-taken. Demand and technology identical; overview changed (Basis column, attention and deal badges); coverage, clusters and China changed by 0.04% to 7.6% (China phone layout: heading badges).

Open breaches (one line each, proposed fix):
- B-12: years, sources and names typed into labels (screen 4 captions, GLOBOCAN note, card years). Fix: read the year and source name from the sheet row, not the code.
- B-14: thresholds typed in components (barrier red at 2.5, score scale at 2 and 3.5, low barrier 2.0 in text and metrics). Fix: one thresholds module in src/domain, used by the screen and the text.
- B-15: company, vendor and ID literals in components (APP_EOS, COVERAGE_COMPANIES, COVERAGE_REGIONS, COVERAGE_FAMILIES, COVERAGE_STEPS). Fix: read the company, region and family lists from the sheet tables (companies, s2_ tables).
- B-16: company tuples in metrics (overview buyers, ranking names). Fix: read them from the companies table.
- B-18: provenance text typed on screen 1 (EDGAR and annual-report wording, Forbes note). Fix: store the provenance text with the sheet README or the sources row and display that.
- B-20: tab names typed in queries ("Overview M&A", "As of"). Fix: a constant for each tab name in one module, or a column in the table that says which tab it is.

Not done, needing your call: table renames (section 13), the B-05 enforcement decision (decision 11), empty duplicate tables (section 13), legacy table revenue_observation (8 rows, no loader; the growth check skips it when it is missing).

## Owner decisions round 6 (23 Nov 2026)

Commits (CD-61-visibility): db51e5d (B-05 enforced, unverified as L, three tables dropped), 50a6529 (B-14), 889f99d (B-20), 6f16faa (B-16), a0a42a6 (B-18), e11aaca (B-15 and partly B-12, one commit for both: they share shells.py), and the documents and screenshots commit that follows this entry.

- B-05 quote check: H-10 and H-11 are Derived after the sheet's Calculation wording (headline.csv re-exported). Run 35: 0 failures. Enforced in the refresh; a failing row is unverified with confidence L.
- Unverified rows are treated as L: hidden by default, UNCONFIRMED under the toggle. Test: tests/test_enforced_checks.py.
- revenue_observation (8 rows) archived to data/archive/revenue_observation.csv, then dropped with challenger_coverage and step_family_map (both 0 rows, no loader, no code reference). Duplicates of section 13 stay.
- B-14: thresholds in src/domain/thresholds.py, each commented.
- B-15: companies, families and steps in src/domain/coverage_model.py, tested against the grid. APP_EOS removed (no callers). Still open: the app-to-end-of-support link needs a sheet column.
- B-16: company lists in src/domain/companies.py, tested against the company table.
- B-18: the overview README loads into screen_notes ("Overview README"). The three provenance notes are read by label. The sheet has no rows for them yet: "Prices source", "Sartorius basis", "Rankings status". Until the owner adds them, the screen shows "To collect: add the … row to the overview sheet README". Open for the owner: add the three rows (the current wording is the text to use).
- B-20: tab names and the As of label in src/domain/tabs.py.
- B-12: partly. Periods, sources and the map year now come from the data. Open: GLOBOCAN and IDF names, years in headers and tile titles, the Ocrevus note.
- Note: the B-18 change shows placeholder text on screen 1 until the three rows are added.

Acceptance (audit section 12), final run:
1. Tests: 312 pass.
2. Import twice: sheet-backed tables identical (82 tables); news_item +1 from the external feed between the two runs.
3. Screenshots re-taken; differences explained in the audit (demand captions, coverage card line wrap, overview badges and placeholders).
4. Still fails: B-12 (partly), B-15 (end-of-support link), B-18 (three rows), B-03, B-10 open.
5. Passes by test.
6. Passes (Google Fonts noted, B-23).
7. Lint and format pass; no type check configured.

Not in this round: the "Data architecture" section for CLAUDE.md (the text did not come through with the message; add it when pasted). Table renames stay deferred (audit section 13).

## Round 7 (23 Nov 2026): merge, sheet links, CLAUDE.md, acceptance

- Merged origin/main into CD-61-visibility (merge commit 324e630). The conflicts were screen 5; the branch's later decision (Show on tile = Yes) is kept, and the applications ranking stays withdrawn.
- Sheet columns re-exported: overview README rows (Prices source, Sartorius basis, Rankings status), technology end of support column P (application), demand README display labels.
- B-15: end-of-support rows link to applications through column P. B-12: demand headers, top-10 title and note, and the Ocrevus note come from the README block. B-18: closed.
- CLAUDE.md: data architecture section added; the draft file docs/claude-data-architecture.md is deleted. The parse-report rule is marked as a target: not built yet.
- Tests: 315 pass.
- Acceptance: check 2 passes for sheet-backed tables; check 4 still fails on a strict reading (typed years listed in audit section 12); screenshots re-taken.
