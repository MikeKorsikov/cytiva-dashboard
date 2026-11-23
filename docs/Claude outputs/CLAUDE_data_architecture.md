## Data architecture

### Layers
Data moves one way only: **Google Sheets → CSV snapshots → SQLite → screens**.

1. **Seed sheets (Google Sheets)**
   - This is where people maintain the data. It is not runtime storage.
   - Read-only from code. **Never write to Google from code**: no API writes, no edits through a connector.
2. **CSV snapshots (`data/<area>/sheet/*.csv`)**
   - One file per tab, committed to git, so every data change shows up as a reviewable diff.
   - Produced **only** by `scripts/export_seed_sheets.py`. Never type a CSV by hand, and never paste one from tool output.
   - Sheet IDs and tab IDs (gids) live in `seed_sheet_gids.yaml`.
   - The script uses the plain export URL `https://docs.google.com/spreadsheets/d/<id>/export?format=csv&gid=<gid>`. **Never** use `/gviz/tq`: it guesses one type per column and blanks the minority values.
   - Each export logs the sheet ID, tab, row count and timestamp to `data/sheet_exports.log`.
3. **SQLite (`data/app.db`)**
   - Built from the CSVs by the loaders (`src/ingest/*.py`) during a refresh.
   - The **only** source the screens read.
4. **Screens (Streamlit)**
   - Read from `app.db` through `src/metrics` and `src/domain`.
   - Screens, metrics and domain modules must never import `src/ingest`; `tests/test_layers.py` enforces this.
   - No network calls at runtime: never call Google, Miro, Lucid or a feed.

Live feeds (share prices, news, security incidents) are the one exception to "sheet first":
- A scheduled collector writes them **directly into `app.db`**.
- Their sheets hold configuration and seed rows only: tickers, feed URLs, matching rules.
- Feed data is not in the CSVs, so it needs its own backup or export.

### Seed sheets
| Area | Sheet | ID |
|---|---|---|
| Screen 1 Overview | Screen 1 – Overview data | `1k5MfRSdsziSTZgtIplwASKkCSlY3nLkfg8jpwqiA8Fg` |
| Screen 2 Competitor coverage | Screen 2 – Market share data | `1EKU_0DEEWXGkAaFEWyrhT9WpdmlBRcgiPpTK6dcoqss` |
| Screen 3 Customer clusters | Screen 3 sheet | `1asd0YHjtFgSCAmAeFbq_QIbYLXCc-AzjWgcZsTEteOk` |
| Screen 4 Demand drivers | Screen 4 sheet | `12YV6UNxTET8WWUmzNG46KjQHeeFBBMaPS-zn-FM5-_o` |
| Screen 5 Technology | Screen 5 – Technology data | `1Io-AbomyfDeRX-LOcxLNJ_YpaqiJbWVh8rSHsy_dgz4` |
| Screen 6 China | Screen 6 – China data | `1wEndgjfRVTKSpNWlNFHdgZp_PWvnLnrca6UCHxzvvXI` |
| Cytiva sites (screens 2, 6) | Danaher & Cytiva — Legal entities and sites | `1MPccYB-6lvaNS5HbDMP0kMzfpmMvQbL5fdorRQi27KM` |
| Applications (screen 5) | Danaher & Cytiva — Applications and technology list | `16MYgBYe3_bxaSimXkR0UjoFcAHUe1gT-IkP8xhu1qKU` |

The research file (`RESEARCH_FILE`, `1C1vMJ…`) is **not** a seed sheet. Don't read it for displayed data.

The plain export returns **displayed** (formatted) values. A number format that rounds a value exports the rounded value.
- Run `scripts/check_sheet_numbers.py` after every export, and fix any flag in the sheet's number format.
- This risk goes away when the export moves to the Sheets API with a read-only service account. That move is also the planned fix for the sheets being link-shared; both are deferred.

### Loader rules
- Map columns **by header name** through each tab's header map, never by position. An unmapped or missing header fails the load.
- Tabs with stacked tables are parsed by their section header rows; a missing section header fails the load.
- Strip leading apostrophes. Parse numbers with or without thousands separators and percent signs. "n/d" and blank mean no number. Keep year fields as text or integers without separators.
- A data row is one whose column A matches that tab's ID pattern (e.g. `^ST\d+$`, `^EOS-\d+$`). Rows labelled Note, Rule, Gap, Key, Candidates, Change log, 10-K note and similar go to `screen_notes`, never into data tables.
- Upsert by the sheet's row ID, so the load is idempotent: running it twice gives the same row counts.
- Values a sheet computes with formulas (counts, steps, shares, index averages) are **reference only**. Recompute them in `src/metrics`.
- Link screen 5 rows to applications **only** through the explicit link columns, which use applications-list Names. Never match names by alias or by fuzzy matching.
- Every load writes a parse report listing each cell it could not parse (row ID and cell). A non-empty report is a failure to look at, not to ignore.

### Refresh
- Each refresh writes one `refresh_run` row and records changes in `change_log`.
- Each loader and feed step fails on its own. The failure is logged in `refresh_run.error`, the run continues, and a run with any failed step ends "completed with errors".
- Checks enforced on load:
  - **B-06 growth/YoY:** growth above 50% stores the row as unverified.
  - **B-05 quote:** the check runs only where the evidence cell is a verbatim quote, with separators, units, currency and rounding normalised. Rows whose evidence starts with "Calculation", "Sum", "Derived" or "Same as" are basis Derived and skip the check. Rows with no evidence text are data gaps, not failures.
- Unverified rows follow the L rule (see below).

Steps:
1. **Export:** `python scripts/export_seed_sheets.py`, then `python scripts/check_sheet_numbers.py`. Review the CSV diff in git.
2. **Load:** run the refresh command. Check the parse report and `refresh_run` status.
3. **Commit** the CSVs (and `app.db`, while it is still committed) together, with the refresh run ID in the message.

Never load the database outside the refresh command. If a one-off migration is unavoidable, record it in `docs/phase0-migrations.md` (date, commit, row counts before and after).

### Evidence and display rules
- Every displayed row links to at least one `sources` row (title, publisher, date, URL, **type**). Source type comes from each sheet's Sources tab "Type" column. Register sites use the "Source type" columns V and W.
- `confidence` is an enum: H, M or L.
- One badge rule lives in `src/domain/confidence.py`:
  - **FACT** = confidence H **and** a source of type Primary.
  - **SIGNAL** = M, or H with a secondary source (trade press, aggregators, third-party job boards, mirrors).
  - **UNCONFIRMED** = L or unverified. Hidden by default; one screen-level "Show unconfirmed (L)" toggle reveals them.
  - **HYPOTHESIS** = implications and analyst scores, whatever their confidence.
- Tile badge = the weakest row badge on the tile ("FACT AND SIGNAL" when mixed). Counts take the weakest badge of the rows they count.
- Every tile has an Evidence dialog listing each displayed row with its value, badge, confidence and source, or the mark "no public source".
- Estimates are never shown as data. A row with "Show on tile" = No in the sheet is never displayed.
- No hard-coded numbers, dates, names, thresholds, tab names or URLs from the sheets in components or metrics. Build text from loaded rows. Thresholds live in one module in `src/domain`, with a comment per value.

### Tests
- Tests use a temporary database (`tests/conftest.py`). Never touch `data/app.db`.
- Tests read the committed CSVs. Never call Google in the test suite.
- Render tests (`tests/test_render.py`) and the badge walk test (`tests/test_badges.py`) cover every screen.
- Run the **full** suite before every commit, and put the test count in the commit message. The suite takes several minutes, so use a long timeout.
- Visual baseline: `scripts/visual_baseline.py` writes screenshots to `docs/visual-baseline/` at desktop width (1440) and phone width (390). Compare layout, not values, because the feeds change daily.

### Database file
- `data/app.db` is committed for now.
- Planned: stop committing it and rebuild it from the CSVs with one refresh command, once feed data has its own backup.
- Table naming convention and the deferred rename mapping are in `docs/refactor-audit.md` section 13. Name new tables by that convention.
