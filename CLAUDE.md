# CLAUDE.md

Project brief for Claude Code. Read this at the start of every session.

## Purpose

Personal, outside-in dashboard that monitors Danaher and Cytiva against competitors (Thermo Fisher, Sartorius, Merck Life Science, Repligen, Avantor, Eppendorf, Getinge) for an IT Business Enablement Director - Finance.

**Public data only.** Never use, store, or reference internal Cytiva or Danaher data. If a request needs internal data, stop and ask. "Internal app DB" means the app's own database; it holds public data only.

The full requirements are in the BRD (Google Doc `1lB6E_Zm-cUpVqSvY9KY5qnXHs2pTtvkIXYpSxZjxCIU`) and the screen mockup on the Miro board. Decisions are recorded in Jira project CD: epic CD-1 holds the decisions table; CD-14 holds the hosting design rules; CD-13 holds the market-data decision.

## Scope

- **MVP:** six screens, as in BRD v0.2, with 36 tiles in total:
  1. Overview (share prices, peer financials, M&A, competitor news)
  2. Competitor coverage (footprint by region, process-step coverage, market size and share)
  3. Customer clusters (GMP sites, cluster map, demand, entry barrier index)
  4. Demand drivers (disease burden, pipeline, approvals and expiries, policy, drug sales, capacity, product mapping)
  5. Technology (end of support, incidents in the last 30 days, integration readiness, adoption signals)
  6. China (local competitors' coverage, challengers' financials, confirmed Chinese vendors, opportunities to sell in China)
- **Excluded from scope:** valuation metrics (EV/EBITDA, P/E, relative return vs peers).
- **Deferred:** peer rank and trend per metric.
- **Closed (not in MVP):** CD-4 to CD-9 are marked Done in Jira as parked.
- **Included peer:** Merck Life Science (Process Solutions / MilliporeSigma) at segment level, entered from public disclosures (IFRS, EUR, converted to USD). Decided in CD-19.
- **Excluded peer scope:** the Merck group as a whole, because it is not comparable to Danaher.
- **Peer set (exhaustive list of closest competitors, 8 Nov 2026):** Thermo Fisher, Sartorius, Merck Life Science (segment only), Repligen, Avantor, Eppendorf SE and Getinge AB. Eppendorf and Getinge add benchtop and pilot-scale bioreactors and fermentors, and bioprocess control software. Their financials are included in full. Where a figure is not public, it is shown as "to collect" or n/d, never estimated. Eppendorf is private and has no listed share price.
- **China screen (6):** covers Cytiva and Chinese challengers only. Eppendorf and Getinge are not in the China grid. All China amounts are shown in USD.
- **Footprint grid (screen 2):** 8 product families × 4 regions × 7 companies (Cytiva plus six peers). New peer cells start as "to collect" until researched.

## Stack and hosting

- Python, Streamlit app, run locally on the owner's PC for now.
- Built to move to Streamlit Community Cloud later (or Render or Heroku). The move should be a config change.
- **App database:** a versioned database file in the repo (SQLite is the default choice; confirm in CD-2). It is populated by the refresh job. The app reads only from this database at view time.
- Refresh runs in GitHub Actions, on the BRD cadences (daily for prices, news and incidents; monthly, quarterly or semi-annual for the rest) and on a manual trigger. Each run logs successes, failures and row counts.
- **Publishing refreshed data:** when `data/app.db` changes, the refresh job opens a pull request from a `refresh/<timestamp>` branch. The job runs ruff and pytest first. Pull requests opened with the Actions token do not start CI, so the owner reviews the change and merges it as admin.
- App entry point: `src/app/streamlit_app.py`.
- **Portability rules:**
  - No Windows-specific paths in code or config. Use `pathlib` relative to the repo root.
  - All settings and secrets come from environment variables or `.streamlit/secrets.toml`. Nothing is hard-coded.
  - Dependencies are pinned in `pyproject.toml` (and `requirements.txt` if needed).
- **Secrets:** local values go in `.env` (gitignored). `.env.example` lists secret names with no values. The same secrets go into GitHub Actions secrets. The SEC EDGAR User-Agent is a setting, not a secret. No Google service-account key is needed.

## Data sources

| Source | Used for | Notes |
| --- | --- | --- |
| SEC EDGAR XBRL company facts | Fundamentals for US filers | Requires the User-Agent setting. |
| Company filings, annual reports, press releases (extracted) | Fundamentals for European filers, segment data, M&A, capacity, drug sales, policy events | Extracted by the refresh job; see "AI-populated data" below. |
| Yahoo Finance via yfinance | Share prices for listed companies (last close, 12-month change, 52-week range), USD | Unofficial API and can break. Wrap it in one loader module with caching and a clear failure message. Eppendorf has no listed price. |
| Company newsrooms (RSS), Google News, GDELT | News feed | Free sources only. Store the headline and link; for paywalled articles, store the headline and link only. De-duplicate across sources. |
| Regulator and public data: FDA, EMA, ClinicalTrials.gov, WHO, IHME, GLOBOCAN, IDF, WTO, World Bank, CISA KEV, vendor status pages | Screens 3 to 5 | Free public APIs or downloads, as listed in the BRD. |
| Market research estimate: GMI (Global Market Insights) | Market size for the share calculation | Scope must be stored with the value. |
| Chinese-language sources: CNINFO (巨潮资讯网), HKEXnews, Chinese company sites and financial press | Screen 6: challenger financials, vendor relationships, opportunities | Keep the original text and an English translation. See "Chinese-language sources" below. |
| Benchmark Google Sheet "Danaher vs Peers - Financial Benchmark FY2023-FY2025" (id `12xBj8gkZRS8xBUOSysZ_t3o27iX2Zp0GyEfKqEQ8chw`) | One-time seed for the app database | Not read after the initial load. |

**Currency:** convert all non-USD values to USD, including share prices. Use the average FX rate for P&L items and the period-end rate for balance-sheet items. Store the rate and its date with each converted value.

**Comparability:** carry comparability metadata with the data (IFRS or GAAP, fiscal year end, group or segment). The UI shows comparability badges. Badges are part of the MVP only if confirmed in the re-planned CD-3.

## Data principles

- **Traceability:** every stored record keeps its source URL, publication date, load date, and evidence label (Fact, Signal or Hypothesis).
- **No forecasts:** company guidance, analyst estimates and modelled projections are excluded. Reported history and observed counts only.
- **Sample values:** a value taken from a mockup is marked `is_sample` and must be replaced with sourced data before release.
- **Hypotheses:** "Implications for Finance & IT" text is marked as Hypothesis.
- **AI research tools are never a source.** Tools such as DeepSeek or Gemini may suggest where to look. The app stores only the primary document they point to, with its own URL.

## Chinese-language sources

- The original Chinese text is stored with its English translation.
- Translations are produced by AI. Numbers are checked against the Chinese original by the quote check.
- The owner spot-checks a sample of translations each month. Spot-checks do not block publication.
- Access limits of CNINFO and Chinese news feeds are checked before each source is built.

## AI-populated data

The refresh job uses AI to extract values from documents and news. No human reviews each value before publication (decided 8 Nov 2026), so these checks are required in the pipeline:

1. **Source link.** Every value has a source URL. A record without one is rejected.
2. **Quote check.** The extracted figure must appear in the source text. If it does not, the record is rejected.
3. **Range and consistency checks.** Examples: revenue is not negative; a segment does not exceed group revenue; a year-on-year change above 50% is flagged.
4. **Change log.** Each refresh records what changed and from which source, so a bad update can be found and reversed.
5. **Unverified values are flagged.** A value that fails a check is stored as unverified and is not shown as a fact.

## Folder layout

| Path | Purpose |
| --- | --- |
| `docs/` | KPI dictionary, decision notes |
| `src/ingest/` | Data loaders (EDGAR, filings, yfinance, news, regulator APIs) |
| `src/metrics/` | KPI calculations |
| `src/app/` | Streamlit app (`streamlit_app.py`) |
| `tests/` | pytest tests |
| `.github/workflows/` | CI and scheduled refresh |

## Commands

Environment is managed with `uv`. Python is pinned to 3.13 in `.python-version`; dependencies are pinned in `uv.lock`.

- Install (runtime and dev dependencies): `uv sync`
- Install git hooks (once per clone): `uv run pre-commit install`
- Run app: `uv run streamlit run src/app/streamlit_app.py` (the entry point is created in CD-3)
- Run tests: `uv run pytest`
- Lint: `uv run ruff check .`
- Format: `uv run ruff format .`
- All hooks on all files: `uv run pre-commit run --all-files`
- Local settings: copy `.env.example` to `.env` and fill in values. Never commit `.env`.
- Check EDGAR access (needs `EDGAR_USER_AGENT`): `uv run python -m src.ingest.edgar --ticker DHR`
- Refresh the app database (creates `data/app.db`): `uv run python -m src.ingest.refresh --trigger manual`

Add a dependency with `uv add <package>` (or `uv add --dev <package>` for tools) and commit the updated `uv.lock`.

## Workflow

- **One Jira issue per branch.** Branch name: `CD-<n>-short-name`, for example `CD-15-claude-md`.
- **Commits start with the issue key**, for example `CD-15: add project brief`.
- **Pull requests target `main`.** Do not push directly to `main`.
- **Ask before changing Jira status.** Do not transition issues without the owner's go-ahead.
- **Tests:** every KPI calculation has a test.
- **Docs:** update the README and the KPI dictionary (`docs/`) when a metric or source changes.

## Definition of done

A story is done when:

1. Code is merged to `main` through a pull request.
2. CI passes (ruff and pytest).
3. Every value on screen carries a source link, a date and an evidence label, and passes the AI-populated data checks.
4. README and KPI dictionary are updated where relevant.

Criterion 3 was changed from "figures reconcile to the benchmark Sheet" after the 7 Nov 2026 decisions. The owner has not yet confirmed this change to CD-18.
