# KPI dictionary

Every number the app shows, what it means, where it comes from and how it is labelled. Each
metric is calculated from values stored in the app database (`data/app.db`). The app reads
the database and never writes to it. A missing value shows as **n/d** (not disclosed or not
yet loaded), never as an estimate.

Conventions that apply everywhere:
- **Currency:** USD on every screen. Local-currency values are converted at the average rate
  for the year (P&L) and stored with the rate and its date.
- **Evidence labels:** **Fact** = taken from a filing, release, exchange or regulator list.
  **Signal** = news or other reporting, not confirmed by the company. **Hypothesis** = text to
  test internally, never a finding.
- **No forecasts:** guidance, analyst estimates and modelled projections are not used.
- **Scope:** financials are group level. Segment figures are not shown as peer financials.

## Screen 1: Overview

### Share prices

| Metric | Definition | Source | Label |
|---|---|---|---|
| Last close (USD) | Latest daily close, converted to USD at that day's FX rate | Yahoo Finance via yfinance | Fact |
| 12-month change | Change from the close about 12 months earlier to the latest close | Yahoo Finance via yfinance | Fact |
| As of | Date of the latest close | Yahoo Finance via yfinance | Fact |

Companies: Danaher (DHR), Thermo Fisher (TMO), Sartorius (SRT3.DE), Repligen (RGEN),
Avantor (AVTR), Merck KGaA group (MRK.DE, the group price).

### Peer financials (latest fiscal year, USD)

| Metric | Definition | Source | Label |
|---|---|---|---|
| Revenue ($m) | Revenue for the latest fiscal year, converted to USD at the year's average rate | SEC EDGAR (DHR, TMO, RGEN, AVTR); annual reports (Sartorius, Merck KGaA) | Fact |
| Growth | Revenue this year ÷ revenue last year − 1, in **reporting currency** | As above | Fact |
| Gross margin | Gross profit ÷ revenue | As above | Fact |
| Net margin | Net income attributable to shareholders ÷ revenue | As above | Fact |
| FCF ($m) | Operating cash flow − capital expenditure (purchases of property, plant and equipment, and intangible assets where the filing reports them as one line) | As above | Fact |
| FCF margin | FCF ÷ revenue | As above | Fact |
| Peer median | Median of the five peers (Danaher is excluded). Shown for each margin and growth | Calculated | Fact |
| Best / weakest | Highest and lowest value in each column, among the companies with a value. Green = best, red = weakest | Calculated | Fact |

Notes:
- Growth and margins for Sartorius and Merck KGaA are in EUR. Their USD revenue and FCF use
  the year's average rate.
- Merck KGaA is the group (IFRS, consolidated statements). Its FY2024 USD values are not
  shown, because the FX series in the database covers only the latest two years.

### Forbes Global 2000 rank (curated)

| Metric | Definition | Source | Label |
|---|---|---|---|
| Rank 2026, rank 2025 | Position in the Forbes Global 2000 list for each year | Entered by hand from the Forbes Global 2000 figures supplied on 8 Nov 2026 | Fact (curated) |

Not re-checked online: the public list page does not show company ranks. n/d = not ranked.

### Deal activity (announced)

| Metric | Definition | Source | Label |
|---|---|---|---|
| M&A, Licensing, Collaboration: last 12 months | Number of announced deals where the buyer is the subject, dated within the last 365 days | Company releases and filings (Fact); Google News and GDELT headlines (Signal) | Fact and Signal |
| Same, last 5 years | Number of announced deals in the last five years (1,825 days) | As above | Fact and Signal |

Rules:
- A **buyer** is a company or one of its operating companies (for example, Danaher counts
  Cytiva, Leica Biosystems, Abcam, Aldevron and Beckman Coulter; Merck KGaA counts MilliporeSigma).
- A headline counts only when it reports a deal: a deal verb (acquires, buys, to acquire,
  completes acquisition, licenses, collaboration, partnership) with the buyer as subject.
  Commentary, analysis, history and stock-price news are excluded.
- Each deal counts once. Announcements and completions of the same deal, and reports from
  different outlets, are merged when they name the same target, or share two distinctive words,
  within 180 days.
- Company-reported deals (Fact) are kept over news reports of the same deal (Signal).
- Dates are the date of the company release, or the publication date of the first matching
  article for news. These can differ from the announcement date by a day.
- Counts are lower bounds. Deals that the feeds do not return, and deals announced only in
  filings, are not counted until they are added to the company list or the feed returns them.

### Competitor news

Headlines and links only, one row per company, latest first. Automated stock-price pages
(for example "stock price, news, quote and history") are excluded. Signal.

### Implications for Finance & IT

Two hypotheses from the BRD, labelled Hypothesis. They are questions to test, not findings.

## Screen 2: Competitor coverage

Status: planned. The app shows placeholders for this screen until the research tickets are
done (CD-20, CD-21, CD-32 to CD-34). The definitions below apply when the data is loaded.

Companies: Cytiva (Danaher), Thermo Fisher, Sartorius, Repligen, Avantor, Merck KGaA.

| Metric | Definition | Source | Label |
|---|---|---|---|
| Families made in region | Count of the 8 product families made in each region | Danaher 10-K site list and Cytiva site pages (Cytiva); peer site and product pages (to collect) | Fact (Cytiva); to collect (peers) |
| Steps local | Count of the 7 bioprocess steps supplied from the region. A step is local only when the region makes every family that step needs | Derived from the product grid | Fact (Cytiva); to collect (peers) |
| Biotech sales by region | Biotechnology segment sales for the quarter, by Danaher reporting region, with the share of the total | Danaher 10-Q | Fact |
| Market size and share | Danaher bioprocessing revenue ÷ sourced market size, shown as an indicative range. Not yet sourced: shown as to collect | Danaher primary filing (to collect); market size source to be chosen (scope stored with the value) | To collect |

Peer cells and peer shares are **to collect** until researched. They are not estimated.

## Screen 3: Customer clusters

- **Biotech hub:** a high-density area of biotech companies, plants, sites, labs and universities. Not a legal entity.
- **Density count:** the hub's headline count of companies, enterprises, sites, plants or organisations, from the sheet "Screen 3 - Customer clusters data". Counts of people, jobs, capacity or money are not density counts. A cluster-scope count is used where one exists; a city-wide count is used only where none exists and is labelled city-wide. Counts of different types are not comparable and are shown with their type.
- **Map bubble colour:** the MVP legend, from Cytiva's manufacturing steps made in the hub's region on screen 2 (steps 1 to 7, service excluded): green mostly local (5 to 7), yellow partly local (1 to 4), red imported (0). Region-level, not hub-level.
- **End-market tags:** only signals that state a change. Green up arrow = rising demand or interest; red down arrow = falling. Each tag links to its source.
- **Barrier index:** average of the three 1-to-5 scores present, from customs friction (World Bank LPI customs score, rescaled), tariffs and local content. Registration and geopolitical scores are stored but not averaged, because almost all are blank.
- **Tariff score (1 to 5):** from the WTO applied MFN simple average, all products, 2025: below 5 percent = 1; 5 to 10 percent = 3; 10 percent and above = 5. EU members use the EU rate.
- **TBI 2025:** Tholos International Trade Barrier Index, lower is better, on its own scale. Shown beside the index, not averaged into it. Methodology not yet read.
- **Sources:** each row carries its URL. Some values come from secondary sources (news, summaries) and carry medium or low confidence.
- **Known limits:** city-centre map positions are approximate and not from the sheet. Hubs with no density count are shown as to collect.

## Screen 4: Demand drivers

- **Source:** the research sheet "Screen 4 - Demand drivers data", saved as CSV in `data/demand/` and loaded by the refresh job (`src/ingest/demand.py`). Each row keeps its source URL. Rows without a source are not loaded.
- **Top 10 countries by disease burden:** ranked by new cancer cases (GLOBOCAN 2022), one source. Diabetes (IDF 2024) is shown beside it and does not affect the ranking. DALYs (WHO GHE) are not yet loaded, so the ranking is not by total burden.
- **Pipeline by medicine type:** therapies in development (preclinical to pre-registration), Q2 2026, ASGCT and Citeline. The total is the report's figure; its parts do not reconcile to it.
- **Approvals 2025:** FDA CDER and CBER, EMA and NMPA, each with its source.
- **Biosimilar wave:** patent expiries from company filings. Two rows still come from 2024 articles and must be replaced.
- **Headline totals:** FDA biologics approved 2025 (12 CDER + 6 CBER gene and cell therapies); top-15 drug sales from mAbs (sum of Pharma 50 FY2025 figures); US manufacturing pledges listed (pledges, not spend).
- **Product matrix (tile 8):** Hypothesis (analyst judgement), labelled as such. It has no source URL, by owner decision for this tile only. Validate with Cytiva product evidence before treating it as fact.

## Screen 6: China

Placeholder only. Shows "to collect" and names the research ticket that will fill it.

## Screen 5: Technology

| Metric | Definition | Source | Label |
|---|---|---|---|
| End-of-support register | Products in the estate, where each is used, the vendor's support status, and the source link. A vendor date is shown only where the vendor states one | Public case studies and vendor releases (estate); vendor lifecycle statements (status) | Signal (estate); status as stated by the vendor |
| Incidents in the last 30 days | Vulnerabilities added to the CISA Known Exploited Vulnerabilities catalogue within the last 30 days, where the vendor matches a product in the register. The check date is the last successful refresh | CISA KEV catalogue | Fact |

If the catalogue cannot be downloaded, the refresh run fails and the screen does not show a
zero.

## Data quality rules

Applied to every stored record before it is shown:
1. **Source link:** every record has an https source link. A record without one is rejected.
2. **Quote check:** figures from documents must appear in the source text. Otherwise the
   record is stored as unverified and is not shown as a fact.
3. **Range and consistency:** revenue is not negative; a segment does not exceed its group;
   a change above 50% year on year is flagged.
4. **Change log:** each refresh records what was added, changed or removed, with the source.
5. **Schema changes:** a table whose layout differs from the schema is rebuilt with its rows
   kept. Rows without a source are dropped and counted in the change log.

## Where to find each calculation

| Calculation | Code |
|---|---|
| Growth, margins, FCF | `src/metrics/fundamentals.py` |
| Peer median, best and weakest, share prices, financial table, deal activity | `src/metrics/overview.py` |
| Deal counts by window | `src/metrics/deals.py` |
| Deal rules, duplicates and revalidation | `src/ingest/deals.py` |
| Company-reported deals | `src/ingest/company_deals.py` |
| End-of-support register | `src/ingest/technology.py`, `src/metrics/technology.py` |
| Incidents (CISA KEV) | `src/ingest/incidents.py`, `src/metrics/technology.py` |
| Quality checks | `src/ingest/checks.py` |

## Overview: layoffs tile (2024 to 2026)

| Metric | Definition | Source | Label |
|---|---|---|---|
| Layoffs announced, per year | ✓ announced job cuts or severance for that year; ✗ none found in the sources searched (not proof of none); ? to collect (undated or unclear) | Company filings, releases and reports, each cell linked to its source. Research log: `docs/layoffs_research.md` | Signal |

## Overview: peer order

Every Overview tile lists the peers from largest to smallest by FY2025 revenue in USD: Thermo
Fisher, Merck KGaA, Danaher, Avantor, Sartorius, Repligen. Cytiva is part of Danaher and has no
revenue of its own; it is listed last. Defined in `PEER_ORDER` in `src/metrics/overview.py`.
