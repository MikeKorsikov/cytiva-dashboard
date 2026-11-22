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
