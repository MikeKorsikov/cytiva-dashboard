# Refactor audit (Phase 1, read only)

Date: 20 Nov 2026. Branch: `CD-61-visibility`. Status: **Phase 1 complete. No code has been changed.** The only change is this file. Phase 2 and Phase 3 wait for the owner's approval of the decisions in section 10.

All line references are to the working tree at the start of this audit.

## 0. Summary

- The app is healthy today: 195 tests pass, ruff lint and format are clean, and all six screens render with no exceptions.
- The brief's architecture is only partly true. The repo has no `EvidenceDrawer`, `ConfidenceBadge`, `UnconfirmedToggle`, `StatusChip`, `TileShell` or `EmptyState`. The "Show unconfirmed (L)" toggle was removed in commit `8afe2a4`. The Google Sheets are represented by CSV exports in `data/`, which is compatible with the brief's "use exported files for tests" rule.
- **Highest-risk rule breaches:**
  1. Hard-coded revenue figures in a component, shown on screen 2 (`src/app/shells.py:177-182`, `:218-221`).
  2. Unverified financial values feed the Overview growth figures, which contradicts CLAUDE.md principle 5 (`src/metrics/overview.py:127-155`).
  3. One loader attaches the wrong source URL to every row of two tables (`src/ingest/clusters.py:162`, `:187`).
  4. Quote check and YoY range check are not wired into any loader (`src/ingest/store.py:194-195`, `src/ingest/checks.py:72-82`).
  5. 138 displayed marks have only the private research-sheet link as their source, which is then removed from the page (`src/app/shells.py:108-109`).
- **Dead code:** about 20 functions, 4 CSS classes, about 6 constants, one dependency (`gspread`), and 24 database tables that no code reads: 17 empty schema tables and 7 orphans (sections 5 and 6).
- **Test gap:** no test renders any screen. `src/app/shells.py` has 18% coverage and `src/app/streamlit_app.py` is not imported by any test.

---

## 1. Baseline (before any change)

| Check | Result |
|---|---|
| `uv run pytest` | **195 passed**, 141.6 s, exit 0. 43 warnings: `ResourceWarning` for unclosed SQLite connections in `src/ingest/store.py:40`, `:77` and `src/metrics/technology.py:35`. |
| `uv run pytest --cov=src` | **69% total** (2,387 statements, 737 missed). `shells.py` 18%, `design.py` 47%, `market_tile.py` 57%, `streamlit_app.py` not in the report (no test imports it). |
| `uv run ruff check .` | All checks passed. |
| `uv run ruff format --check .` | 59 files already formatted. |
| Type check | **Not configured** (no mypy or pyright in `pyproject.toml`). Not run. `python -m compileall -q src tests` passes. |
| Build | **No build step** (Streamlit app). Instead, each of the six screen functions was rendered headless with `streamlit.testing.v1.AppTest`: 0 exceptions on every screen. Each screen has 0 buttons, which confirms the evidence drawer is unreachable (section 4, B-08). |
| Lines of Python | `src/` 7,244 lines in 32 files (`app` 2,164, `ingest` 3,851, `metrics` 1,229). `tests/` 2,325 lines in 22 files. |
| Database | `data/app.db` (tracked, last refreshed 19 Nov 2026) has 70 tables. The schema defines 61. See section 5. |

Render harness used for the check: `$TEMP/audit/render_all.py` in the session scratchpad, not in the repo.

---

## 2. Structure map

```
streamlit_app.py  (349)   routing (st.navigation, 6 pages), overview screen 1, five page loaders
  └─ app/shells.py (1541) screens 2-6 renderers and their helpers
       ├─ app/market_tile.py (25)   tile 3 of screen 2, a placeholder shell
       ├─ app/design.py (249)       CSS, html_table, screen_header, kpi_card, section, note, placeholder
       ├─ metrics/coverage.py       step rule (STEP_FAMILIES), step_cells
       ├─ metrics/china.py          imports ingest.china (FAMILY_NAMES, CNY_USD_RATE)
       └─ metrics/{overview,clusters,demand,technology}.py  read-only SQL on data/app.db
metrics/overview.py   imports ingest.prices (imports yfinance at module load), metrics.deals, metrics.fundamentals
metrics/clusters.py   imports ingest.coverage (REGION constants)
metrics/coverage.py   imports ingest.coverage (RESEARCH_FILE)

ingest/refresh.py     runs LOADERS (13) in one recorded run
  ├─ ingest/store.py  connect, create_schema (migrations), upsert (source check, quote check, change log)
  ├─ ingest/schema.py TABLES (61 definitions), COMMON_COLUMNS
  ├─ ingest/checks.py check_source, check_quote, check_range, check_segment_within_group, check_yoy_change
  └─ loaders: china, coverage, clusters, demand, technology   (read CSV exports in data/)
              prices, news, deals, company_deals, edgar, financials, annual_reports, tenk_text,
              rankings, layoffs                                 (network or inline seed values)
```

Runtime path: `overview.connect_readonly` (`src/metrics/overview.py:93-97`) opens `data/app.db` with `mode=ro`. A grep of `src/app` and `src/metrics` finds **no runtime network calls** (acceptance check 6 passes today). Two runtime imports pull in ingest modules for constants, and `prices.py:17` imports `yfinance` when the app starts.

---

## 3. Duplication

Heuristic scan: 14 repeated 6-line windows across `src/`. The list below is the manual review, which is more complete.

| ID | Pattern | Where |
|---|---|---|
| D-01 | Source link. A Google-Sheet check is repeated in 4 places, and each place has a different link markup. | `design.py:216-220` (`source_link`), `shells.py:101-110` (`_mark`), `shells.py:1332-1336` (`_cn_link`), `shells.py:1031-1036` (`_first_source`), `metrics/coverage.py:72`, `ingest/coverage.py:109-111` (`is_research_sheet`). Inline `<a href>` markup appears at `shells.py:403, 426, 910, 922, 1116, 1200`, and `streamlit_app.py:159, 184, 210`. |
| D-02 | Evidence drawer. One drawer exists, but nothing calls it. | `shells.py:971-1005`, reached only via `_row_button` (`:1003-1005`), which has no caller. |
| D-03 | Confidence to badge mapping, implemented 5 times with different outputs. | `shells.py:935-939` (`_CHIP`, H→FACT, M→SIGNAL, L→UNCONFIRMED; used only by the dead `_badge`), `shells.py:1009-1016` (`_HEAT`, shows raw H/M/L), `ingest/china.py:80-81` (H→Fact, else Signal), `ingest/demand.py:46` (L→Signal, else **Fact**, so M becomes Fact), and hard-coded `"Fact"` labels at `ingest/clusters.py:73, 99, 126, 165` and `ingest/coverage.py:123, 149`. |
| D-04 | "Show unconfirmed (L)" toggle and L-row hiding. The toggle is gone (`8afe2a4`). The module docstring still describes it. | `metrics/technology.py:5-6`. L rows are shown on screens 4 and 5 (for example the expiries table, `shells.py:789-797`; screen 5 shows every row). Screen 2 hides L leads by ingest rule (`ingest/coverage.py:94-95`). |
| D-05 | Lower of two confidences. Implemented once, used twice. | `metrics/technology.py:91-95` (`min_conf`), used at `:133` (EOS) and `:232` (integrations). Incidents use a third path, `_estate_confidence` with default `"L"` (`:157-159`). |
| D-06 | Status chips and colours. Five colour maps and about 7 inline copies of the same hex pair. | `shells.py:98` (`_MARK_CLASS`), `:226-237` (`_legend`), `:940-951` (`_EOS_COLOUR`, `_LEVEL_COLOUR`), `:1009-1016` (`_HEAT`), `:1019-1023` (`_chip`), `:600-610` (`_flag_chip`, dead), `design.py:129-137` (`.mk` CSS). `#E6F4EC` / `#1E6B45` appears 7 times in `shells.py`. |
| D-07 | Step rule, recomputed in three places. | Rule and data: `metrics/coverage.py:15-24` and `step_cells` `:41-77`. Region count of "steps local": `shells.py:185-213` (`_region_cards`). Local colour thresholds (≥5 green, ≥1 amber): `metrics/clusters.py:119-129`, used with `_local_steps` `:82-96`. The rule text shown on screen is `shells.py:240-253`. |
| D-08 | Date parsing, two parsers. | `ingest/technology.py:47-67` (`parse_date`: ISO, `31 Dec 2027`, `2026-03`, `at least 2037`, free text → None) and `metrics/technology.py:98-101` (`parse_iso`, ISO only). `gartner_release` `:145-151` formats dates a third way. |
| D-09 | Number parsing, at least 6 copies. | `ingest/china.py:50-54`, `ingest/clusters.py:35-39`, `metrics/demand.py:19-22`, `app/shells.py:652-668` (`_cell`), `:892-895` (`_num_val`), `:898-900` (`_num_fmt`), and the regex `design.py:204`. |
| D-10 | Source-ID and entity-ID parsing. | `S\d+` in `ingest/china.py:46-47` and `ingest/technology.py:70-71`. `EST-\d+` in `ingest/technology.py:94`, `app/shells.py:994`. `ADO-\d+` in `metrics/technology.py:255`. All-ID pattern in `metrics/technology.py:301`. |
| D-11 | Apostrophe stripping. | Not present. No code strips a leading apostrophe and no CSV contains one. The brief's rule does not apply to this repo today. |
| D-12 | Sheet-to-table column mapping. Each loader maps columns by hand. `china.py` maps by header (good), while `clusters.py:50-170` indexes `r["…"]` for every field. Eight near-identical "rows as dicts" helpers. | `ingest/china.py:41-43`, `ingest/clusters.py:30-32`, `ingest/demand.py:33-35`, `ingest/technology.py:74-76`, `ingest/coverage.py:65-77`, `metrics/technology.py:32-35`, `metrics/clusters.py:76-79`, `metrics/demand.py:13-16`, `metrics/china.py:35-38`. |
| D-13 | Note rows. Notes are written with raw SQL and bypass `store.upsert` (no source check, no change log). A note is also stored as a data row. | Raw SQL: `ingest/company_deals.py:144`, `ingest/technology.py:159-165`. Note stored as data: `EOS-08` in `tech_eos`, filtered at `metrics/technology.py:131` and read at `:140-142`. |
| D-14 | FX. Two sources, and the table meant for rates is never written. | `ingest/china.py:26` (`CNY_USD_RATE = 7.2`, an assumption), used at `:166-167`, `metrics/china.py:31`, and shown as text at `shells.py:1414`. Share prices convert with the daily rate (`ingest/prices.py:85-98`). Annual reports use `fx_by_year` (`ingest/annual_reports.py:197-220`). The `fx_rate` table (`ingest/schema.py:57`) has 0 rows and no writer. |
| D-15 | Tile and screen shell. The `_box` helper exists but is unused. The pattern `with st.container(border=True): section(...)` is repeated 30 times in `shells.py` and 7 in `streamlit_app.py`. | `shells.py:39-43` (`_box`, unused). `design.py:167-170` (`screen_header`, used on all six screens, good). |
| D-16 | Empty state. Five variants. | `"Not loaded yet: run the refresh. To collect."` at `shells.py:281, 500, 678, 1218`, and the china variant at `:1390`. Overview uses a different message at `streamlit_app.py:257-260`. |
| D-17 | Page loaders. Five near-identical open, load and close blocks. | `streamlit_app.py:269-330`. |
| D-18 | Map layout. Identical geo and layout settings in two figure builders. | `shells.py:374-390` and `:632-648`. |
| D-19 | Hand-written tables. `html_table` exists, but five tables are built by hand with about 59 inline `style=` attributes. | `shells.py:422-448` (`_top_hubs_table`), `:451-489` (`_barrier_table`), `:868-889` (`_product_matrix`), `:903-913` (`_register_table`, dead), `:916-926` (`_incidents_table`, dead). |
| D-20 | Matrix grids. Two builders for the same layout. | `shells.py:113-142` (`_grid`) and `shells.py:1296-1324` (`_china_matrix`). |
| D-21 | Hard-coded CSS in a component, duplicating `.note`. | `shells.py:1285-1288` (`_CN_CSS`), duplicates `design.py:54`. |

---

## 4. Rule breaches

Severity: **H** (values or traceability wrong, or a rule in CLAUDE.md broken), **M** (hard-coded text or constants on screen), **L** (minor).

### Values and sources
| ID | Sev | Breach | Where |
|---|---|---|---|
| B-01 | H | **Hard-coded revenue in a component.** Four regional biotech sales figures ($524m, $726m, $490m, $57m, with percentages) are typed into the code, with a comment that cites a "Legal entities sheet" that is not a database row. They are shown on screen 2 as Fact. The source link is an EDGAR company browse page, not the filing, so no quote exists. | `src/app/shells.py:171-182`, render `:218-221`, source `:174-176` |
| B-02 | H | **Unverified values shown as facts.** Twelve `financial_metric` rows fail the check (`verification_status = 'unverified'`, `value_usd` NULL, Sartorius and Merck KGaA 2024). `_metric` never filters on verification status, and the growth figures use these rows for the prior year. So the Sartorius and Merck KGaA growth on the Overview is computed from unverified data. | `src/metrics/overview.py:127-136`, `:153-155`; `src/ingest/store.py` check notes |
| B-03 | H | **Wrong source attached to rows.** Every `country_demand` row (FDA sites, trial counts, CDMO sites, demand score) gets the Nature Index URL, and every `country_barrier_index` row (LPI, tariff and Tholos scores) gets the tariff URL. Traceability is broken for those cells. | `src/ingest/clusters.py:162` (`tariff_source_url` for all barrier columns), `:187` (`NATURE_INDEX_URL` for all demand columns) |
| B-04 | H | **Source link removed from displayed marks.** 138 displayed `footprint` marks have only the research-sheet URL as source. (The 20 `footprint_evidence` rows with the same issue are stored but not shown.) The page drops any Google-Sheet URL and shows an unlinked mark. Acceptance check 5 cannot pass for these. | `src/app/shells.py:108-109` (`_mark`), `:1334-1335` (`_cn_link`), `src/app/design.py:218`, `src/metrics/coverage.py:71-75`, `src/ingest/coverage.py:120` |
| B-05 | H | **Quote check not run.** `store.upsert` supports a quote check, but no production loader passes `quote_columns`. Only tests pass it. CLAUDE.md check 2 is not enforced for any loader. | `src/ingest/store.py:194-195`; no production caller |
| B-06 | H | **YoY and consistency checks not enforced.** `check_yoy_change` (CLAUDE.md check 3c, flag above 50%) has no production caller. `check_range` runs only in `financials.py:186` and `prices.py:137`. `check_segment_within_group` runs only in `financials.py:188` and `annual_reports.py:225`. No demand, China, clusters or technology loader runs any range check. | `src/ingest/checks.py:50-82` |
| B-07 | H | **Estimate shown as data.** The product-use matrix (High, Some, None) is analyst judgement with no source (`product_use.csv`, confidence column = "Hypothesis"). The loader's docstring says it "is not loaded … the screen shows it as to collect", which is false. The screen renders the matrix. | `src/ingest/demand.py:5-7` (docstring), `:29` (loaded), `src/app/shells.py:855-861` (rendered) |
| B-08 | H | **Evidence drawer unreachable.** Acceptance check 5 ("every displayed row opens the evidence drawer") fails: the drawer exists, but no button or chip opens it. Zero buttons on every screen. | `src/app/shells.py:971-1005`, `:1003-1005` |
| B-09 | M | **Coordinates and reference constants not from a source row.** Map positions are described as "approximate … reference, not from the sheet", and country centres likewise. They are rendered on the map. | `src/metrics/clusters.py:20-37` (`HUB_POSITION`), `src/metrics/demand.py:57-78` (`COUNTRY_CENTRE`), `src/metrics/clusters.py:40-55` (`COUNTRY_REGION`) |
| B-10 | M | **Hard-coded label confidence / evidence labels.** `country_demand` is always `confidence "H"`, label Fact (`clusters.py:186-190`). Coverage cells and `clusters` rows always say Fact, whatever their confidence (D-03). | See D-03 |

### Numbers and text in components
| ID | Sev | Breach | Where |
|---|---|---|---|
| B-11 | M | Axis cap constant tied to a data value. | `src/app/shells.py:748` (`maximum = 2217`) |
| B-12 | M | Years, sources and names typed into labels and notes: "FY2025, Pharma 50 (secondary source)", "FY2025" in cards, "2022" in hover text, "GLOBOCAN 2022", "IDF 2024", "Ocrevus 2029 … 2024 articles", "Pharma 50 (FY2025)". | `shells.py:627, 688, 694, 742, 798, 831, 1402-1407` |
| B-13 | M | Derived China share written as text: "11% of $24.6bn". The value is in the database as a derived row (H-01 × H-02, `ingest/china.py:162-163`), but the text is typed in. | `src/app/shells.py:1414-1417`; `data/china/financials.csv` F-00 |
| B-14 | M | Thresholds in components. Barrier index ≥2.5 is red, and a score colour scale at 2 and 3.5. The screen text states "below 2.0" for low barrier (the same value as `LOW_BARRIER` in metrics). | `shells.py:318-325`, `:476`, `:541`; `metrics/clusters.py:203` |
| B-15 | M | Company, vendor and IDs typed into components. `APP_EOS` maps "Oracle E-Business Suite" and "SAP ERP (ECC)" to row IDs. `_fin_name` checks `F-03b`. "Cytiva" is a literal. Company and region lists are typed in. | `shells.py:1154` (`APP_EOS`), `:1371`, `:1131`, `:62-95` (`COVERAGE_COMPANIES`, `COVERAGE_REGIONS`, `COVERAGE_FAMILIES`, `COVERAGE_STEPS`) |
| B-16 | M | Company tuples in the metrics layer. Companies, buyers and ranking names are hard-coded, not derived from the `company` table. | `src/metrics/overview.py:21-50`, `:201-208`, `:55-63` |
| B-17 | M | Hypothesis text typed in code instead of stored rows. Overview and coverage hypotheses are literals, while technology and China hypotheses come from the database. | `src/metrics/overview.py:39-42` (`IMPLICATIONS`), `shells.py:300-301`, `:864-865` |
| B-18 | M | Provenance text typed in. "SEC EDGAR (DHR, TMO, RGEN, AVTR); Sartorius annual report; Merck KGaA group" and the Forbes note. | `src/app/streamlit_app.py:117-120`, `:131-132` |
| B-19 | M | Note link text fixed to one document. Any `screen_notes` row on the Overview M&A tab gets the label "Danaher FY2025 10-K", whatever its source. | `src/app/streamlit_app.py:153-159` |
| B-20 | M | Hard-coded tab names in queries. | `streamlit_app.py:153` (`'Overview M&A'`), `shells.py:1220` (`'As of'` label) |
| B-21 | M | Brief says tile 5 implications are always HYPOTHESIS. The table shows H/M/L chips, and the HYPOTHESIS badge helper `_hyp_badge` is dead. | `shells.py:1141-1150` (`_implications_table`), `:963-968` |

### Runtime and config
| ID | Sev | Breach | Where |
|---|---|---|---|
| B-22 | L | Runtime network calls from app or metrics. None found (check 6 passes). | `src/app`, `src/metrics`: no `requests`, `yfinance`, `gspread` or `urllib` imports |
| B-23 | L | Google Fonts loaded in CSS. This is a browser request, not an API call. Confirm it is acceptable. | `src/app/design.py:25` |
| B-24 | L | Runtime import of ingest modules, which pulls `yfinance` into the app process. | `src/metrics/overview.py:16`, `src/app/shells.py:30`, `src/metrics/china.py:12`, `src/metrics/coverage.py:12` |

---

## 5. Data layer

**Counts.** The schema defines 61 tables. The committed database has 70 tables: 61 schema tables minus `tech_apps` (missing), plus 7 orphan data tables not in the schema (`challenger_coverage`, `estate_item`, `incident`, `market_size`, `opportunity`, `revenue_observation`, `vendor_link`) plus `change_log`, `refresh_run` and `sqlite_sequence`.

- **Stale committed database.** `data/app.db` was refreshed on 19 Nov 2026, before the `tech_apps` loader existed (`3c2b252`). So screen 5 shows the old end-of-support table until the next refresh. Tests do not catch this, because they build their own databases.
- **Empty schema tables with no reader** (17): `region`, `fx_rate`, `step_family_map`, `market_estimate`, `gmp_site`, `country_barrier`, `disease_burden`, `clinical_trial`, `approval`, `patent_expiry`, `drug_sales`, `capacity_pledge`, `policy_event`, `modality_product_map`, `lifecycle_date`, `integration_tier`, `adoption_signal`. (`ranking` is also empty, by design, and is read by the Overview.) Several are duplicates of a live table:
  - `approval` vs `demand_approval`
  - `patent_expiry` vs `demand_expiry`
  - `drug_sales` vs `demand_top_drug`
  - `capacity_pledge` vs `demand_capacity`
  - `policy_event` vs `demand_policy`
  - `disease_burden` vs `demand_burden`
  - `integration_tier` vs `tech_integrations`
  - `adoption_signal` vs `tech_adoption`
  - `country_barrier` vs `country_barrier_index`
  - `opportunity` vs `cn_opportunity`
  - `market_estimate` vs `market_size`
- **Orphan tables with data.** `market_size` has 2 sourced rows (Repligen narrow definition, $20bn, and GMI equipment market, $48.1bn). Screen 2 tile 3 still shows "to collect". `estate_item` (4 rows) and `revenue_observation` (8 rows) have no writer in the current schema. Dropping them means losing rows, so each needs a decision (section 10).
- **Missing natural keys from sheet row IDs.** The demand tables are keyed by names (`demand_expiry` by `drug`, `demand_policy` by `item`, `demand_top_drug` by `drug`), not by the sheet's row ID. `demand_product_use` is keyed by `medicine_type`. `footprint` is keyed by company, region and family, with no evidence ID. `screen_notes` is keyed by `(tab, label, text)`, so a changed note text creates a second row. `country_demand` and `country_barrier_index` are keyed by country only, so a second factor for the same country cannot be stored.
- **Confidence is free text.** No `CHECK` constraint exists (`grep CHECK src/ingest/schema.py` → 0). Stored values include `customer M; product L` (`cn_vendor`) and `Hypothesis` (`demand_product_use`). The CSV `country_profile.csv` has 10 blank `barrier_confidence` cells; that column is not loaded.
- **Naming is inconsistent.** Prefixes `cn_`, `tech_`, `demand_`, `footprint`, `cluster_`, `layoff_`, plus unprefixed `deal`, `news_item`, `company`, `ranking`, `screen_notes`, `cdmo_site`, `market_signal`. Source tables are `tech_sources`, `cn_source`, and `tech_row_sources`, while the other tables store `source_url` per row.
- **Unverified rows are readable.** 12 rows are unverified and no read path filters them (B-02).
- **Status columns are free text.** `cdmo_site.status` has 13 distinct values in the CSV.
- **Sample flag.** `is_sample` is 0 on every row (good, consistent with CLAUDE.md "no sample values").
- **Migration.** `_migrate_table` (`src/ingest/store.py:67-118`) copies rows and drops rows that violate the new key (`INSERT OR IGNORE`). The counts are recorded only in the change log. This is safe for additive changes. It is not safe for renames: a renamed column is treated as a new column and its values are lost.

---

## 6. Dead code

Verified by grep across `src/` and `tests/`.

**Functions and constants with no production caller**
- `src/app/shells.py`: `STATUS_LEGEND` (34-36), `_box` (39-43), `_text` (46-51), `_hyp` (54-59), `_flag_chip` (600-610), `_register_table` (903-913), `_incidents_table` (916-926), `_format_check` (929-932), `_CHIP` (935-939, used only by `_badge`), `_badge` (954-960), `_hyp_badge` (963-968), `_evidence_drawer` (971-1000), `_row_button` (1003-1005), `_cn_kind` (1339-1340).
- `src/app/design.py`: `BLUE` (16), `inject_css` (152-153). `streamlit_app.py:48` (`_table` alias) and `:41` (`CSS` alias) are trivial.
- `src/metrics/china.py`: `coverage_summary` (112-116). `tiles` (83-90) is used only by a test.
- `src/metrics/clusters.py`: `kpis` (235-244).
- `src/metrics/technology.py`: `gartner_release` (145-151), `gartner_rows` (251-262, test only). Gartner data is loaded but never displayed.
- `src/metrics/technology.py:211`: a sort that is overwritten on the next line (`:212`).
- `src/metrics/technology.py:274-280`: `evidence_quote` appears twice in `_QUOTE_FIELDS`.
- `src/metrics/demand.py:110-115`: `by_type` is built and never read.
- `src/metrics/overview.py:246`: `LOWER_IS_BETTER` is an empty set, so it has no effect.
- `src/metrics/overview.py:195`: `publisher` is set from the `summary` column and never displayed.
- `src/ingest/checks.py:72-82`: `check_yoy_change`, used by tests only (B-06).
- `src/ingest/clusters.py:27`: `WORLD_BANK_LPI_URL`, unused.
- `src/ingest/schema.py:24`: `VERIFICATION_STATUSES`, unused.
- `src/ingest/technology.py:24`: `CONFIDENCE`, unused.
- `src/ingest/technology.py:39`: the adoption ID pattern also allows `G26-` IDs. The current `adoption.csv` has only `ADO-` rows, so the allowance is unused. Remove it when the Gartner rows are placed (section 10, decision 10 or a later step).

**CSS classes defined in `design.py` and never used:** `.t-row` (`:124`), `.navlabel` (`:110`), `.mkt` (`:71`), `.card` (`:100`; `kpi_card` and `_cn_card` are functions, not this class).

**Dependencies**
- `gspread` (`pyproject.toml`, `requirements.txt`): no import in `src/`. Only `tests/test_environment.py` imports it. Its transitive packages `google-auth` and `google-auth-oauthlib` go with it.
- `requirements.txt` is a generated export of `uv.lock`. CI uses `uv sync --locked`, so the file is not needed by any workflow. Confirm before removing.

**Files**
- `.gitkeep` placeholders in `docs/`, `src/app/`, `src/ingest/`, `src/metrics/`, `tests/` and `.github/workflows/`. Harmless, but they can be removed once folders have files.

**Database tables** (section 5): 17 empty schema tables with no reader, 7 orphan tables, and 1 table missing from the committed file.

---

## 7. Test gaps

| Area | Coverage today | Gap |
|---|---|---|
| Screens (rendering) | `shells.py` 18%, `design.py` 47%, `market_tile.py` 57%, `streamlit_app.py` not imported by any test | No test renders a screen. Pinning "what each tile shows" needs a rendering test. `AppTest` works (section 1). |
| Source-scanning test | `tests/test_technology.py:211-218` reads `shells.py` as text and checks for vendor names | Brittle. Replace with a rendering test. |
| Private import | `tests/test_coverage.py:129` imports `_footprint_matrix` | Test through the public screen function instead. |
| Importer idempotency | `test_technology.py:28` (runs twice), `test_prices.py:110`, `test_store.py:52` (schema twice) | No test runs every importer twice and compares row counts. |
| Importer row counts and known values | Present for China, clusters, demand, technology, coverage, overview | Not per screen, per tab, for all tabs. Known values are sparse. |
| Refresh end to end | `test_store.py:118` runs refresh with zero loaders | No test runs all loaders into a temp database and checks counts. |
| `tech_apps` loader | `test_apps.py` | Covered. But the committed DB lacks the table (section 5). |
| `screen_notes` writes | `test_danaher_10k.py` only | Raw-SQL writers (B-13) are not checked against the change log. |
| Low coverage loaders | `edgar.py` 35%, `tenk_text.py` 64%, `deals.py` 77%, `annual_reports.py` 77%, `news.py` 83%, `prices.py` 82%, `refresh.py` 82% | Network paths are untested by design. Parsing paths should be covered. |
| Unused and broken paths | Evidence drawer (B-08), Gartner tile (section 6), Partial-index message (section 8) | Not tested because not reachable. |
| Test hygiene | 43 warnings, unclosed SQLite connections (`store.py:40`, `:77`, `metrics/technology.py:35`) | Fix as part of Phase 2. |

---

## 8. Brief compared with the repo

The brief describes some things that are not in this repo. Each needs a decision or a correction to the brief before Phase 3.

| # | Brief says | Repo says | Where |
|---|---|---|---|
| 1 | Step 2 needs Genomic, Media and Single-use | Code: Genomic and Media only | `metrics/coverage.py:17` |
| 2 | Step 3 needs Media and Single-use | Code: Media, Single-use **and Filtration** | `metrics/coverage.py:18` |
| 3 | Step 5 needs Filling | Code: Filling **and Filtration** | `metrics/coverage.py:20` |
| 4 | Step 8 (service) is entered by hand | Code derives it from `Service` evidence rows | `metrics/coverage.py:53-55`, `ingest/coverage.py:98-100` |
| 5 | Step rule matches the research sheet | Code docstring says it matches the sheet's "Step map" tab | `metrics/coverage.py:4`, `ingest/coverage.py:7-14` |
| 6 | Screen 2 has tabs `T1 Coverage grid`, `T2 Steps local`, `Peer sites` (PS-01 to PS-47), `T4 Region cards` | Only `evidence.csv` is loaded. No code reads the other tabs. | `ingest/coverage.py:28` |
| 7 | Sources now run S01 to S19 on screen 2 | Screen 2 rows carry full URLs, and no source table is loaded. | `data/coverage/evidence.csv` |
| 8 | Fourth region is "Other developed markets" | Export and code use "Japan, Aus. & NZ". An unknown label raises `KeyError`. | `ingest/coverage.py:46-51` |
| 9 | Screen 3 `Country barriers` has column T "Display on tile" | Column is not in `data/clusters/country_barrier.csv` and not read | `data/clusters/country_barrier.csv` header |
| 10 | Show "Partial index: n of 5 scores" when fewer than 3 scores | Not implemented. The index is averaged over the scores present, with no notice. | `ingest/clusters.py:142-159`, `shells.py:589-600` |
| 11 | Screen 6 H-12 (FY2025 China growth estimate) is reference only | Not in `data/china/headline.csv` (only H-01 to H-09). Nothing displays it. | `data/china/headline.csv` |
| 12 | Screen 6 T2 F-00 growth is `n/d` | Correct in `data/china/financials.csv` (F-00 growth n/d). | `data/china/financials.csv` |
| 13 | Screen 1 Clario (MA-04) completed 2026-03-24 | Code has "Thermo Fisher to acquire Clario Holdings", 29 Oct 2025, announced only. No completion record. | `ingest/company_deals.py:84-89` |
| 14 | Screen 1 rankings are empty ("To collect") | Correct. | `ingest/rankings.py:18-22` |
| 15 | Screen 1 share prices come from the daily feed | Correct. | `ingest/prices.py` |
| 16 | Screen 1 attention items carry ACT or MONITOR | No attention items exist on screen 1. | `streamlit_app.py:230-252` |
| 17 | Screen 5 hides L rows, with a "Show unconfirmed (L)" toggle | Toggle removed; every row shown (`1cf20a7`, "confidence is a label, not a filter") | `metrics/technology.py:5-6` (stale docstring) |
| 18 | Labels FACT, SIGNAL, HYPOTHESIS, UNCONFIRMED | Screens use "Fact", "Signal", "Hypothesis" in mixed case. `FACT` / `UNCONFIRMED` appear only in dead code. | `design.py:149`, `shells.py:935-939` |
| 19 | Components: EvidenceDrawer, ConfidenceBadge, UnconfirmedToggle, StatusChip, TileShell, ScreenHeader, EmptyState | None exists under these names. `screen_header` exists. The others are described in D-02 to D-16. | Section 3 |
| 20 | Importers read seed sheets | Importers read CSV exports in `data/`. Compatible with "use exported files for tests". The live sheets were **not** read in this audit. | `data/*/` |
| 21 | Seed data is in Google Sheets | Several loaders hold seed values as Python literals (`layoffs.py`, `company_deals.py`, `annual_reports.py`, `rankings.py`). They are not in the CSV exports. | Section 2 |
| 22 | Screen 5 end-of-support ranking comes from a seed sheet | Resolved 21 Nov 2026. The applications sheet "Danaher & Cytiva — Applications and technology list" (ID 16MYgBYe3_bxaSimXkR0UjoFcAHUe1gT-IkP8xhu1qKU) now holds the ranking. Its "Size and complexity ranking" tab is exported to `data/technology/sheet/ranking.csv`, and `apps.csv` is deleted. Diff before the switch: the 13 rows in `apps.csv` match the sheet on every field; the sheet adds 107 rows. Ranking is loaded as Hypothesis, with the sheet's scoring confidence and no URL (its source IDs point to another workbook). | `data/technology/sheet/ranking.csv`, `ingest/technology.py` (`load_apps`) |

---

**Seed sheets (Google Sheets, read-only exports, as of 21 Nov 2026)**

| Screen | Sheet | ID | Export folder |
| --- | --- | --- | --- |
| 1 Overview | Screen 1 – Overview data | 1k5MfRSdsziSTZgtIplwASKkCSlY3nLkfg8jpwqiA8Fg | not exported yet |
| 2 Coverage | Screen 2 – Market share data | 1EKU_0DEEWXGkAaFEWyrhT9WpdmlBRcgiPpTK6dcoqss | `data/coverage/sheet/` |
| 3 Clusters | Screen 3 – Customer clusters data | 1asd0YHjtFgSCAmAeFbq_QIbYLXCc-AzjWgcZsTEteOk | not exported yet |
| 4 Demand | Screen 4 – Demand drivers data | 12YV6UNxTET8WWUmzNG46KjQHeeFBBMaPS-zn-FM5-_o | not exported yet |
| 5 Technology | Screen 5 – Technology data | 1Io-AbomyfDeRX-LOcxLNJ_YpaqiJbWVh8rSHsy_dgz4 | `data/technology/sheet/` (in progress) |
| 6 China | Screen 6 – China data | 1wEndgjfRVTKSpNWlNFHdgZp_PWvnLnrca6UCHxzvvXI | `data/china/sheet/` |
| 5 (EOS ranking) | Danaher & Cytiva — Applications and technology list | 16MYgBYe3_bxaSimXkR0UjoFcAHUe1gT-IkP8xhu1qKU | `data/technology/sheet/` (ranking.csv, notes.csv exported; applications.csv blocked by a filter on the tab, see progress file) |
| 2 (register) | Register (sites, legal entities, value chain, entity-site links, sources) | 1MPccYB-6lvaNS5HbDMP0kMzfpmMvQbL5fdorRQi27KM | `data/coverage/sheet/` (`register_sites.csv` is an earlier committed copy, not yet re-exported: the sheet has 55 rows, the file 51) |

Eight sheets in total: the six screens, the applications list and the screen 2 register. The export script (`scripts/export_seed_sheets.py`) holds the tab list for all of them. Sheet exports are read only, and no CSV is written by hand.

## 9. Bugs logged (not fixed; ask before fixing)

| ID | Bug | Where |
|---|---|---|
| BUG-01 | Overview growth uses unverified prior-year rows (B-02). | `metrics/overview.py:153-155` |
| BUG-02 | Country demand and barrier rows carry the wrong source URL (B-03). | `ingest/clusters.py:162`, `:187` |
| BUG-03 | `demand.py` docstring says the product-use matrix is not loaded. It is loaded and shown (B-07). | `ingest/demand.py:5-7` |
| BUG-04 | `technology.py` docstring describes the removed L toggle. | `metrics/technology.py:5-6` |
| BUG-05 | Dead sort overwritten immediately. | `metrics/technology.py:211-212` |
| BUG-06 | `publisher` is mapped from `summary`. Not displayed, so no visible effect. | `metrics/overview.py:195` |
| BUG-07 | `refresh.py` counts unverified rows with a `LIKE '%unverified%'` search over the JSON in `new_values`. It matches the word anywhere in the record, not only in `verification_status`. | `ingest/refresh.py:68-71` |
| BUG-08 | `china.py` (loader) reads `headline["H-03"]` without a guard. A missing row fails the whole refresh. | `ingest/china.py:163` |
| BUG-09 | `read_evidence` raises `KeyError` on a region or company name it does not know, so a renamed sheet fails the import. | `ingest/coverage.py:70-75` |
| BUG-10 | Committed database is older than the code (no `tech_apps`). | `data/app.db` (section 5) |
| BUG-11 | Evidence labels are hard-coded to Fact in several loaders regardless of confidence (B-10, D-03). | `ingest/clusters.py:73, 99, 126, 165`, `ingest/coverage.py:123, 149` |
| BUG-12 | Demand loader gives M-confidence rows the label Fact (`Signal` only for L). This differs from China, which gives Signal to anything not H. | `ingest/demand.py:46` vs `ingest/china.py:80-81` |
| BUG-13 | Tile 3 says "to collect" although two sourced market-size rows exist in the database. | `market_tile.py`, `market_size` table |
| BUG-14 | SQLite connections left open in tests and loaders (ResourceWarning, 43 warnings). | `ingest/store.py:40`, `:77`, `metrics/technology.py:35` |
| BUG-15 | `_metric` uses an f-string for the column name. Safe today (two fixed values), but fragile. | `metrics/overview.py:130-132` |

---

## 10. Decisions needed from the owner

Each decision changes what a user sees, or changes data. Nothing below has been changed.

1. **Step rule (section 8, rows 1-5).** Which family list is correct for steps 2, 3 and 5? The code includes Filtration in steps 3 and 5. The brief omits it. Step 8: entered by hand, or derived from Service rows? These change the "steps local" counts on screens 2 and 6, and the colours on the matrix.
2. **Biotech sales (B-01).** Keep the four figures on screen 2 and move them into a sourced row (with a quote and the filing URL), or remove them until they are sourced?
3. **Unverified growth (B-02, BUG-01).** Blank the Sartorius and Merck KGaA growth figures until the FX-rate row is loaded? This changes two displayed values.
4. **Research-sheet-only marks (B-04).** 138 displayed marks have no public source. Show them as unlinked (today's behaviour), link to the research sheet, or require a public source before they can show as Made?
5. **Product-use matrix (B-07).** Keep it on screen as a Hypothesis, or show "to collect" until product evidence exists?
6. **Source attribution (B-03, BUG-02).** Approve fixing the per-row source for country demand and barrier data. This needs a per-row source column in the CSV exports, which is a data change.
7. **L rows (D-04, section 8 row 17).** Screen 5 shows every row, by your last commit. The brief says L rows are hidden by default with a toggle. Which rule applies to screens 3 to 6?
8. **Tile 5 implications (B-21).** Show the HYPOTHESIS badge on every implication row, or keep the confidence chips?
9. **Tile 3 market share (BUG-13).** The market-size rows are in the database. Should tile 3 show them now? It is a change to the screen. Danaher's bioprocessing revenue is still missing.
10. **Orphan and empty tables (section 5).** Drop the 18 empty and 7 orphan tables after a migration, or keep them? `estate_item` (4 rows), `revenue_observation` (8 rows) and `market_size` (2 rows) hold data, so dropping them needs your OK.
11. **Quote and range checks (B-05, B-06).** Turning them on for all loaders can mark existing rows as unverified, which changes displayed values. Approve the change, or only run them for new rows?
12. **Dependencies.** Approve removing `gspread`, and confirm `requirements.txt` can go. Approve adding a dev dependency for screenshots (Playwright with Chromium, or Streamlit `AppTest` snapshots without pixels), and optionally a type checker (mypy).
13. **Live sheets.** Items 6, 7 and 9 of section 8 depend on whether the live sheets already hold the new tabs and columns. I can read the sheets (read only) to confirm. Should I?
14. **Google Fonts (B-23).** Keep the font import, or host the font? It is a browser request, not an API call.

---

## 11. Proposed target structure and change list

Target layout, which keeps Streamlit, SQLite, pytest and ruff, and keeps every route and URL:

```
src/
  domain/          NEW  pure rules, each with unit tests
    confidence.py  H/M/L enum, FACT/SIGNAL/UNCONFIRMED mapping, min_conf
    status.py      Made / Partial / Not made / to collect, chip classes
    steps.py       step rule (STEP_FAMILIES), step_cells
    dates.py       parse_date (ISO, "31 Dec 2027", "2026-03", "at least 2037")
    ids.py         S-ID, EST-, ADO-, EOS- parsing; research-sheet detection
    numbers.py     number parsing and formatting
    fx.py          CNY/USD rate and conversion, rate and date kept with each value
  ingest/
    importer.py    NEW  one framework: read tab, map columns by header, upsert by row ID,
                        notes to screen_notes, report unparsed cells (ID + cell)
    specs/         per-screen import config (tab, ID pattern, columns, table)
    ... loaders reduced to specs
  metrics/         read-only queries, one module per screen
  app/
    ui/            NEW  EvidenceDrawer, ConfidenceBadge, StatusChip, TileShell,
                        ScreenHeader (moved from design.py), EmptyState, html_table
    screens/       NEW  one module per screen (replaces shells.py)
    streamlit_app.py   routing unchanged; page loaders replaced by one helper
tests/
  rendering/       NEW  AppTest per screen, default and L-toggle states
  screenshots/     NEW  baseline PNGs at 1280 px and 390 px (after approval)
```

**Ordered steps** (one per commit; tests green after each)

| # | Change | Risk | Verification |
|---|---|---|---|
| 0 | Phase 2 safety net: importer row-count and known-value tests per screen and tab; AppTest rendering tests per screen; screenshot baseline (after decision 12). | Low | Tests pass on current code. Baseline recorded before any refactor. |
| 1 | `src/domain/` helpers, moved as-is from `metrics/`, `ingest/` and `app/`. Unit tests for each. No behaviour change. | Low | 195 existing tests pass. Screenshots identical. |
| 2 | Unify the confidence→label mapping (D-03). Show FACT/SIGNAL/UNCONFIRMED or keep the current text? Decision 8 first. | Med, changes labels | Labels table in tests. Screenshot diff listed. |
| 3 | Import framework (`importer.py`), one loader at a time, starting with `coverage` (smallest). Idempotent upsert by row ID. Report unparsed cells. | Med | Row counts per table identical to baseline. Double run: no duplicates. |
| 4 | Migrate loaders `technology`, `clusters`, `demand`, `china` onto the framework. | Med | As step 3, per loader. |
| 5 | Data model: the same names for shared concepts, one `sources` and `row_sources`, `confidence` as a `CHECK` enum. Migrations keep rows (decision 10 first). | High | Migration test on a copy of `data/app.db`. Row counts equal. Change log has one entry per changed row. |
| 6 | UI components, one screen at a time: `EmptyState`, `TileShell`, `StatusChip`, `ConfidenceBadge`, `EvidenceDrawer` (made reachable, B-08). | Med | Rendering tests and screenshot diff per screen. |
| 7 | Split `shells.py` into `app/screens/`, one module per screen. | Low | Rendering tests unchanged. |
| 8 | Remove dead code (section 6), unused CSS, `gspread` (decision 12). | Low | Tests, ruff and AppTest unchanged. |
| 9 | Rule breaches (section 4), each after its decision. B-01 to B-21 as decided. | Med, changes displayed values | Each change listed with before and after. |
| 10 | Quote and YoY checks wired into the loaders (B-05, B-06) after decision 11. | Med-high | Tests for each check. Count of rows flagged before and after. |

Risk note: steps 2, 5 and 9 change what a user sees. They wait for decisions in section 10.

---

## 12. Acceptance checks, status today

| # | Check | Status today |
|---|---|---|
| 1 | Baseline tests still pass, plus new ones | 195 pass (baseline). New tests not yet written. |
| 2 | Importing every sheet twice gives the same row counts, no duplicates | Not tested for all importers (section 7). Technology and prices are tested. |
| 3 | Screenshots match the baseline at both widths | No screenshot baseline exists yet (decision 12). |
| 4 | No component has a hard-coded company name, date, number or URL from the sheets | **Fails**: B-01, B-11 to B-21. |
| 5 | Every displayed row opens the evidence drawer with at least one source URL | **Fails**: no drawer is reachable (B-08). 138 displayed marks have no public source (B-04). Hypothesis rows with no URL are exempt under CLAUDE.md. |
| 6 | No runtime code calls Google, Miro or Lucid APIs | **Passes**. Google Fonts CSS import noted (B-23). |
| 7 | Lint, type checks and build are clean | Lint and format **pass**. Type check **not configured**. No build step. |

---

*Prepared in Phase 1 as a read-only audit. Commands used are listed in section 1. Line numbers refer to the working tree on branch `CD-61-visibility` at the start of the audit.*
