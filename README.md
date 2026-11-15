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

