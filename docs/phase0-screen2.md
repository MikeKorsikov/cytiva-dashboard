# Phase 0, screen 2 (competitor coverage): loaded from the live seed sheets

Written for: the repo owner, who approves each screen's display changes before Phase 3.

Status: screen 2 done in the data layer and the app. Screens 6, 5, 3, 4 and 1 are not done (see the end).

## Sources of truth now read

| Input | Live tab | Export (read only) | Rows |
|---|---|---|---|
| Coverage sheet 1EKU | Sources | `data/coverage/sheet/sources.csv` | 20 (S01 to S20) |
| Coverage sheet 1EKU | Peer sites | `data/coverage/sheet/peer_sites.csv` | 47 (PS-01 to PS-47) |
| Coverage sheet 1EKU | T1 Coverage grid | `data/coverage/sheet/t1_coverage_grid.csv` | 8 families x 24 cells |
| Coverage sheet 1EKU | T4 Region cards | `data/coverage/sheet/t4_region_cards.csv` | 4 regions |
| Register 1MPcc | Sites | `data/coverage/sheet/register_sites.csv` | 51 (ST01 to ST51) |

Not read: T2 Steps local (computed in the app from the grid, by the approved rule), T3 tabs (not on screen 2 yet), and the research file 1C1vMJ (not read for displayed data; export kept in `data/coverage/research/` for the diff only). The old research export `data/coverage/evidence.csv` is moved to `data/coverage/research/evidence_legacy_export.csv`.

## Row counts, before and after (`data/app.db`)

| Table | Before | After |
|---|---|---|
| `footprint` (research-derived, now orphan) | 207 | 207 (archived to `data/archive/footprint.csv`; drop in the Phase 3 migration) |
| `footprint_evidence` (research, orphan) | 109 | 109 (archived to `data/archive/footprint_evidence.csv`; drop in the Phase 3 migration) |
| `s2_source` | n/a | 20 |
| `s2_peer_site` | n/a | 47 |
| `s2_peer_family` | n/a | 51 |
| `s2_cyt_site` | n/a | 51 |
| `s2_grid` | n/a | 69 (every grid cell that is not ?; all rows pass the source check) |
| `s2_biotech_sales` | n/a | 4 |

The loader's parse report is empty: every cell, site and family parsed, and every row has a sheet source ID and URL.

Idempotency: a second load changes no counts (tested in `tests/test_coverage.py`).

## Checks against the sheet

- **Cytiva families made** (T4): NA 7, WE 7, HG 3, OD 0. Match.
- **Cytiva steps local, steps 1 to 7** (T2 counts steps 1 to 8, so the sheet's figure is one higher where step 8 is Made): NA 5, WE 6, HG 1, OD 0. Match after excluding step 8.
- **Cytiva column of T1** against the register stage counts: 0 differences on all 32 cells.
- **Peer grid** against Peer sites: 1 difference, Sartorius Resins in High-growth markets. T1 says Partial and the only site is an L row (PS-33). The sheet's key says L-only cells are Partial, so the grid is right.
- **Biotech sales**: 524 / 726 / 490 / 57, total 1,797. Shares computed: 29.2 / 40.4 / 27.3 / 3.2 per cent. Match.
- **Steps 2, 3 and 5** are now the approved definitions. Spot-checked against the T2 values: TMO NA step 3 Made, AVT NA step 3 Partial, MRK NA step 3 ?, CYT WE step 5 Not made, CYT HG step 2 Partial. All match.

## Displayed values that change on screen 2

Full cell and step lists: `docs/phase0-screen2-changes.txt` (159 cell changes, 140 step changes, generated from the before and after data).

**Summary of cell changes (159):**
- 178 peer cells: Not made to ?. The research file marked a peer family Not made when no evidence was found; the sheet's key says ? means no evidence found.
- 61 Made to ?, of which 4 are Cytiva Service cells (Service has no evidence row yet) and the rest are peer cells that came only from the research file (see the 22 rows below).
- 26 Partial to ?, peer cells from the research file.
- 9 Made to Partial, 7 Partial to Made, 7 Not made to Made, 3 To collect to Made, and a few more: mostly peer cells where the sheet grid differs from the research file.
- Cytiva cells: Western Europe Analytical ? to Made; High-growth Systems ? to Made; High-growth Filtration Partial to Made; North America Resins Partial to Made; Service Made to ? in four regions.

**Step changes:** the new rule (step 2 needs Single-use; step 3 no longer needs Filtration; step 5 needs only Filling; step 8 is ? with no Service row) and the ? rule (any unknown family makes the step ?). 140 step cells change, mostly peer cells that were Not made and are now ?.

**Region labels:** "Japan, Australia and New Zealand" becomes "Other developed markets" (card title, matrix group header, colour tint). The short label is "Other developed".

**Biotech sales cards:** the four figures are unchanged ($524m, $726m, $490m, $57m). The share is now computed (29.2% etc.). The link now goes to the 10-Q (S20), not to the EDGAR browse page. The card text no longer names a "Biotech sales" link to the EDGAR browse page.

**Region card counts:** North America 6 to 7 families, 4 to 5 steps local; Western Europe 6 to 7 families, 4 to 6 steps; High-growth 1 to 3 families, 0 to 1 step; Other developed 0 families, 0 steps (unchanged).

## Decisions I need from you (found while loading)

1. **Hypothesis rows counted as Made.** The sheet's T1 counts two register sites whose stage evidence is a hypothesis:
   - ST16 (Cardiff, Discovery and analytics, "to confirm", Hypothesis, confidence M) makes Cytiva Western Europe Analytical Made.
   - ST47 (Incheon, Filtration, "to confirm", Hypothesis, confidence L) makes Cytiva High-growth Filtration Made. The research file had it Partial.
   The brief says a hypothesis is not a fact. Should these two cells be Partial, ?, or Made with the L label?
2. **Muskegon (ST08) makes Cytiva North America Resins Made.** The site's stage says "from 2028", and the research file had it Partial. The grid's own key says "Partial = a site opening later". Partial or Made?
3. **Cytiva marks lose their links.** The register is a Google Sheet, and the app hides Google Sheet links, so Cytiva marks show no link. That was already true before this change. The owner's approval says S19 (the register) backs site counts at M, so either the register link is shown, or Cytiva marks stay unlinked. Which?
4. **Step 8 for Cytiva drops from Made to ?** in four regions, because no Service evidence row exists in the seed sheets. Service rows were only in the research file. Should service evidence be added to the coverage sheet (as a Service row per region), or stay ??

## 22 rows that exist only in the research file (1C1vMJ)

These are Made or Partial rows in the research file with no matching Peer sites row. They are not displayed now. Each needs a primary source before it can come back (approval 4: treat as L, no link, UNCONFIRMED when shown).

| Company | Region | Family | Research ID | Site | Source |
|---|---|---|---|---|---|
| Thermo Fisher | North America | Genomic | E022 | Carlsbad, CA, USA | Thermo Fisher press release |
| Thermo Fisher | North America | Systems | E023 | Santa Clara, CA; Logan, UT, USA | Thermo Fisher press release, $600m bioprocessing investment |
| Thermo Fisher | North America | Analytical | E024 | San Jose, CA, USA | SelectScience |
| Thermo Fisher | Western Europe | Analytical | E028 | Bremen, Germany | Analytica-World |
| Thermo Fisher | High-growth markets | Media | E032 | Singapore | FiercePharma |
| Sartorius | North America | Analytical | E039 | Ann Arbor, MI, USA | Sartorius capacity expansions page |
| Sartorius | Western Europe | Media | E041 | Schloss Holte-Stukenbrock, Germany | Sartorius capacity expansions page |
| Sartorius | High-growth markets | Single-use | E048 | Beijing, China; M'Hamdia, Tunisia | Sartorius Beijing and M'Hamdia pages |
| Sartorius | High-growth markets | Filtration | E049 | Bangalore, India | Sartorius blog, 1 Oct 2024 |
| Sartorius | High-growth markets | Systems | E050 | Bangalore, India | Sartorius blog, 1 Oct 2024 |
| Repligen | North America | Systems | E056 | Anaheim, CA, USA | Repligen locations page |
| Repligen | North America | Genomic | E058 | BioLife Solutions sites, USA | Repligen 10-Q Q3 2026 |
| Repligen | Western Europe | Media | E059 | Lund, Sweden | Repligen locations page |
| Repligen | Western Europe | Single-use | E062 | Waterford, Ireland | Repligen locations page; 10-K FY2024 |
| Repligen | High-growth markets | Single-use | E063 | Bengaluru, India | Repligen locations page |
| Repligen | High-growth markets | Systems | E064 | Jüri, Estonia | Repligen locations page; 10-K FY2024 |
| Merck KGaA | North America | Single-use | E072 | Danvers, MA, USA | Merck KGaA life science operations brochure |
| Merck KGaA | North America | Resins | E074 | Burlington, Ontario, Canada | Merck KGaA life science operations brochure |
| Merck KGaA | North America | Genomic | E075 | Carlsbad, CA, USA | Merck KGaA brochure; OncoDaily on CDMO sale |
| Merck KGaA | Western Europe | Resins | E077 | Gernsheim, Germany; Buchs and Altdorf, Switzerland; Cork, Ireland | Merck KGaA life science operations brochure |
| Merck KGaA | Western Europe | Systems | E080 | Molsheim, France | Merck KGaA life science operations brochure |
| Merck KGaA | High-growth markets | Systems | E083 | Beijing, China; Bangalore, India | Merck KGaA life science operations brochure |

## Not done, and what the owner said about it

- **Screen 1 (Overview):** the Python literals in `layoffs.py`, `company_deals.py`, `rankings.py` and `annual_reports.py` are still in use. They need the Screen 1 sheet's tabs as their source, and I have not yet read that sheet's tabs.
- **Screen 6 (China):** the step helper now applies the new rule, so screen 6's steps have already changed (Cytiva China step 3 Partial to ?; Duoning unchanged). Its data loader has not been moved to the live tabs.
- **Screens 5, 3, 4:** not started.
- **Clario and H-12:** to check against screen 1's and screen 6's live tabs.
- **L-row hiding and the UNCONFIRMED label (approvals 4, 6):** not built yet. They belong to Phase 3 display changes, so screen 2 currently shows L-confidence peer cells as normal marks.
