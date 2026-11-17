# cytiva-dashboard

Outside-in dashboard for Cytiva's competitive position against Danaher and peers: growth and margin, cost and cash, market and valuation, and a news feed.

Hosting: a Streamlit app plus a scheduled Python job (GitHub Actions). Runs locally for now and is built to move to Streamlit Community Cloud or similar later.

## Public-data-only rule

This project uses public data only (filings, earnings materials, market data, news, and public regulatory sources). No internal Cytiva data is used or stored in this repository. Do not commit credentials, `.env` files, or private datasets.

## Layout

| Path | Purpose |
| --- | --- |
| `docs/` | Project documentation and decision notes |
| `src/ingest/` | Data collection from public sources |
| `src/metrics/` | Metric calculations (growth, margin, cash, valuation) |
| `src/app/` | Streamlit application |
| `tests/` | Automated tests |
| `.github/workflows/` | CI and scheduled data-refresh jobs |

## Status

Setup phase. See the Jira project CD (epic CD-1, "01 Decisions & setup") for decisions and remaining tasks.

## Screen 3: Customer clusters

One page: biotech density hubs on a map, end-market demand tags, the top hubs by density, and the market entry barrier index.

- **Data:** the research sheet "Screen 3 - Customer clusters data", saved as CSV in `data/clusters/` and loaded by the refresh job (`src/ingest/clusters.py`). Each row keeps its source URL.
- **Tariffs:** WTO World Tariff Profiles 2026 (applied MFN simple average, 2025). The World Bank tariff series ends in 2022 and is not used for scoring.
- **Trade Barrier Index:** Tholos International Trade Barrier Index 2025, shown beside the index, not averaged into it.
- **Definitions:** see `docs/KPI_DICTIONARY.md`, section "Screen 3: Customer clusters".
- **Refresh:** edit the CSV files, then run `uv run python -m src.ingest.refresh --trigger manual`.

## Screen 4: Demand drivers

Disease burden, pipeline, approvals, policy and funding, biggest drugs, capacity pledges, and the Cytiva product matrix (to collect until evidenced).

- **Data:** the research sheet "Screen 4 - Demand drivers data", saved as CSV in `data/demand/` and loaded by the refresh job (`src/ingest/demand.py`). Each row keeps its source URL.
- **Definitions:** see `docs/KPI_DICTIONARY.md`, section "Screen 4: Demand drivers".
- **Refresh:** edit the CSV files, then run `uv run python -m src.ingest.refresh --trigger manual`.

## Screen 5: Technology

End of support, exposure at vendors we use (last 30 days), integration readiness, adoption signals, and implications.

- **Data:** the research sheet "Screen 5 - Technology data", saved as CSV in `data/technology/` and loaded by the refresh job (`src/ingest/technology.py`). The old live CISA download was removed; the app reads only from its database.
- **Definitions:** see `docs/KPI_DICTIONARY.md`, section "Screen 5: Technology".
- **Refresh:** edit the CSV files, then run `uv run python -m src.ingest.refresh --trigger manual`. The collector for vendor feeds (CISA, Oracle, SAP, Microsoft) must run outside this workspace; see `data/technology/feeds.csv`.

## Screen 6: China

Selling into China and relying on Chinese vendors: China share of Danaher sales, local competitor coverage, challenger financials (USD), Chinese vendors, commercial opportunities, and implications.

- **Data:** the research sheet "China data", saved as CSV in `data/china/` and loaded by the refresh job (`src/ingest/china.py`). Sources are in `data/china/sources.csv`.
- **Currency:** RMB is converted at 7.2 RMB per USD, an assumption flagged on the screen until the PBoC 2025 annual average is loaded (`CNY_USD_RATE` in `src/ingest/china.py`).
- **Definitions:** see `docs/KPI_DICTIONARY.md`, section "Screen 6: China".
- **Refresh:** edit the CSV files, then run `uv run python -m src.ingest.refresh --trigger manual`.

