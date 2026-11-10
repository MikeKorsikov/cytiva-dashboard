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

## Market size and share (Competitor coverage, Tile 3)

**What it shows:** Danaher's share of the bioprocessing market (Cytiva and Pall, FY2025), under
two market definitions, with the growth of each supplier's bioprocessing business.

- **Numerator:** bioprocessing revenue reported by each supplier (not the Biotechnology segment).
  Danaher is a floor ("over $6B"), so its share is a floor too.
- **Denominator:** the market size, in two definitions. Narrow: Repligen's company framing
  ($20bn+). Broad: GMI's bioprocessing equipment market ($48.1bn, 2025). Others = market minus
  named suppliers, capped at zero with a warning. Thermo Fisher does not disclose bioproduction,
  so it is in Others.
- **Merck KGaA** (Process Solutions) is included by default; the toggle on the tile removes it.
- **FX:** EUR converted at the ECB 2025 annual average (1.1300 USD per EUR).

**Sources:** every number is stored with its source URL, the source's wording, and an H/M/L
confidence mark (`revenue_observation`, `market_size`, `fx_rate`). Seed rows live in
`src/ingest/bioprocess_share.py`; they are checked before they are written.

**Limits:** supply-side shares. Unlisted suppliers are excluded. The broad market is equipment
only, while supplier revenues include consumables, so the broad share overstates an
equipment-only comparison. Danaher's growth is not yet collected, so the growth comparison is
incomplete.

**Refresh:** the seed rows are loaded by the refresh job (`LOADERS` in `src/ingest/refresh.py`).
To change a figure, edit the tuple in `src/ingest/bioprocess_share.py` with its source URL, then
run `uv run python -m src.ingest.refresh --trigger manual`.
