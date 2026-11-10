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
