# CLAUDE.md

Project brief for Claude Code. Read this at the start of every session.

## Purpose

Personal, outside-in dashboard that monitors Danaher and Cytiva against competitors (Sartorius, Thermo Fisher, Merck Life Science, Repligen and others) for an IT Business Enablement Director - Finance.

**Public data only.** Never use, store, or reference internal Cytiva data. If a request needs internal data, stop and ask.

Decisions are recorded in Jira project CD. Epic CD-1 holds the decisions table; CD-14 holds the hosting design rules; CD-13 holds the market-data decision.

## Scope

- **In MVP:** one page (epic CD-3) with growth and margin, cost and cash, market and valuation, and a news feed.
- **Later:** full news page (CD-4), full scorecard (CD-5), quarterly refresh and TTM (CD-6), Cytiva head-to-head (CD-7), finance deep-dives (CD-8), AI summaries and digest (CD-9).
- **Included:** Merck Life Science (Process Solutions / MilliporeSigma) as a direct bioprocess competitor at segment level. Its segment data is entered manually each quarter from the benchmark Sheet (IFRS, EUR, converted to USD). Decided in CD-19.
- **Excluded:** the Merck group as a whole, because it is not comparable to Danaher.

## Stack and hosting

- Python, Streamlit app, run locally on the owner's PC for now.
- Built to move to Streamlit Community Cloud later (or Render or Heroku). The move should be a config change.
- Scheduled data refresh runs in GitHub Actions. Refresh writes a versioned dataset that both the local and the cloud app can read (a repo data folder or the Google Sheet), not only local disk.
- **Portability rules:**
  - No Windows-specific paths in code or config. Use `pathlib` relative to the repo root.
  - All settings and secrets come from environment variables or `.streamlit/secrets.toml`. Nothing is hard-coded.
  - Dependencies are pinned in `pyproject.toml` (and `requirements.txt` if needed).
- App entry point: `src/app/streamlit_app.py`.
- Secrets: a Google service-account key is stored outside the repo. Local values go in `.env` (gitignored). `.env.example` lists secret names with no values. The same secrets go into GitHub Actions secrets. The SEC EDGAR User-Agent is a setting, not a secret.

## Data sources

| Source | Used for | Notes |
| --- | --- | --- |
| SEC EDGAR XBRL company facts | Fundamentals for US filers (9 companies) | Requires the User-Agent setting. |
| Google Sheet "Danaher vs Peers - Financial Benchmark FY2023-FY2025" (id `12xBj8gkZRS8xBUOSysZ_t3o27iX2Zp0GyEfKqEQ8chw`) | Record for manual and segment data (including Merck Life Science), and for caveats | Figures must reconcile to this Sheet. |
| yfinance | Share prices and valuation inputs (EV/EBITDA, P/E, relative return) | Unofficial API and can break. Wrap it in one loader module with caching and a clear failure message. |
| RSS (IR press releases, Google News per company, EDGAR 8-K feed) | News feed | De-duplicate across sources. |

**Currency:** convert non-USD peers to USD. Use the average FX rate for P&L items and the period-end rate for balance-sheet items.

**Comparability:** carry comparability metadata with the data (IFRS or GAAP, fiscal year end, group or segment). Show comparability badges in the UI.

## Folder layout

| Path | Purpose |
| --- | --- |
| `docs/` | KPI dictionary, decision notes |
| `src/ingest/` | Data loaders (EDGAR, Sheet, yfinance, RSS) |
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
3. Figures reconcile to the benchmark Sheet.
4. README and KPI dictionary are updated where relevant.

Agreed in CD-18 on 5 Nov 2026.
