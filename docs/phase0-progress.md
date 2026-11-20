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

## Screen 6: China
- [x] Exports: data/china/sheet/ (headline, companies, coverage_grid, coverage_evidence, financials, vendors, opportunities, implications, sources). Commit 95cd0a9.
- [ ] Loader (src/ingest/china.py) reads data/china/sheet with header names
- [ ] Cytiva China row from register ST42–ST45 (country China only); step 8 from CE-35/S43
- [ ] Metrics (src/metrics/china.py)
- [ ] Screen (src/app/shells.py china_screen)
- [ ] Tests (tests/test_china.py)
- [ ] Commit
- Checks: H-12 not shown; F-00 growth n/d; H-04 SIGNAL; Cytiva China row (SU Made FACT; Systems Not made; step 3 Partial; step 8 Made from CE-35/S43)

## Screen 5: technology
- [ ] Exports
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
