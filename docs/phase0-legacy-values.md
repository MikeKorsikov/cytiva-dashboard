# Phase 0 legacy values

Status on 22 Nov 2026: all three groups have moved into the sheets. This file keeps the values as
they stood in the code before the move, for the record.

- Layoffs (18 rows): now sheet tab "T6 Layoffs" (LO-01 to LO-18). Moved, not re-checked: each row's "Checked" column says so.
- Screen 4 implication questions: now sheet tab "T9 Implications" (I-01, I-02).
- Danaher 10-K notes (3): now sheet tab "T2 M&A", rows labelled "10-K note" (source S19).

## Values before the move

## 1. Layoffs (screen 1): `src/ingest/layoffs.py`

Current values, as in the code. Mark: Yes, No or Unknown (to collect). Year is the year the mark refers to.

| Company | Year | Mark | Source | Note (numbers as stated) |
| --- | --- | --- | --- | --- |
| Thermo Fisher | 2026 | Yes | https://apps.eurofound.europa.eu/restructuring-events/detail/300198 | Bremen: up to 100 jobs announced Apr 2026 (Eurofound); 85 relocations to Brno confirmed later. Langenselbold: about 60 (April). Asheville, NC closure notice reported at about 420 roles (single report). |
| Thermo Fisher | 2025 | Yes | https://www.beckershospitalreview.com/supply-chain/thermo-fisher-cuts-300-jobs-in-latest-layoff-round.html | About 300 in Cambridge and Plainville, MA; about 85 in Carlsbad, CA; further WARN notices in Orlando and Cerritos. |
| Thermo Fisher | 2024 | Yes | https://www.sec.gov/Archives/edgar/data/97745/000009774526000018/tmo-20251231.htm | FY2025 10-K: severance about 2% of workforce in 2024 (facility consolidations and cost reductions). Lexington, MA closure about 160 jobs (Boston Business Journal). |
| Merck KGaA | 2026 | Unknown | https://oncodaily.com/technology/merck624237 | Sources disagree: one reports 20 at EMD Serono Billerica, MA; another finds none. CDMO sale to Lonza, staff transfer. To verify. |
| Merck KGaA | 2025 | Yes | https://www.irishtimes.com/business/2025/10/22/merck-to-close-arklow-plant-with-loss-of-100-jobs | Arklow, Ireland plant to close by 2028, about 100 jobs (Oct 2025). Second report: 109 in Martillac, France (not yet verified). |
| Merck KGaA | 2024 | Yes | https://www.marketscreener.com/quote/stock/MERCK-KGAA-436395/news/Merck-cuts-up-to-230-jobs-in-electronics-division-46074265/ | Electronics restructuring: up to 230 jobs, about 100 at Darmstadt (Mar 2024). |
| Danaher | 2026 | No | https://www.sec.gov/Archives/edgar/data/313616/000031361626000062/dhr-20251231.htm | No new company-wide layoffs found in 2026 sources. Management says 2025 actions deliver most savings in 2026. |
| Danaher | 2025 | Yes | https://www.fool.com/earnings/call-transcripts/2026/01/28/danaher-dhr-q4-2025-earnings-call-transcript/ | Cost actions of about $250m including headcount reductions and rooftop consolidation (Q4 2025 call summary; timing of savings to check). Cepheid WARN notices in California (2025). Cytiva Westborough, MA: 85 positions, effective Mar 2025. |
| Danaher | 2024 | Yes | https://www.fiercebiotech.com/medtech/testmaker-cepheid-cut-more-600-jobs-silicon-valley-headquarters | Cepheid: about 626 positions at Sunnyvale, CA (2024 report). Cytiva Westborough, MA: 85 positions (notice Dec 2024). |
| Avantor | 2026 | Yes | https://www.warntracker.com/company/avantor-fluid-handling | Avantor Fluid Handling, Morrisville, NC: 54 (WARN notice, Feb 2026). Q3 2026: about $13m cash restructuring; no headcount disclosed. |
| Avantor | 2025 | Yes | https://www.sec.gov/Archives/edgar/data/1722482/000162828026007118/avtr-20251231.htm | FY2025 10-K: restructuring and severance charges of about $29.8m (includes a $5.3m reversal of 2024 severance). Headcount not disclosed. |
| Avantor | 2024 | Yes | https://www.sec.gov/Archives/edgar/data/1722482/000162828026007118/avtr-20251231.htm | FY2025 10-K: 2024 multi-year cost programme, $82.8m charges, of which $64.3m employee severance. Sanborn, NY site closure (38 jobs). |
| Repligen | 2026 | Yes | https://www.sec.gov/Archives/edgar/data/0000730272/000162828026068562/rgen-20260930.htm | Site optimisation programme from Q1 2026 to end 2027: severance $3.9m in nine months. Headcount not disclosed. |
| Repligen | 2025 | No | https://www.sec.gov/Archives/edgar/data/730272/000119312526076528/rgen-20251231.htm | No new layoffs found. Facility-exit costs only; Q1 2025 severance $12k. |
| Repligen | 2024 | Unknown | https://www.sec.gov/Archives/edgar/data/730272/000095017025038999/rgen-20241231.htm | Restructuring continued in 2024 ($46.9m charges, per one report); employee reductions not quantified. To verify. |
| Sartorius | 2026 | No | https://www.sartorius.com/en/company/newsroom/corporate-news/2026-half-year-results-sartorius-group-1845854 | No layoffs found. Results growing; headcount rising. |
| Sartorius | 2025 | No | https://www.aerzteblatt.de/news/sartorius-stellt-mehr-personal-ein-a49d263f-d8ee-40ca-8ca9-ee6014b36860 | No compulsory programme found. Workforce up 514 to 14,042 in 2025. |
| Sartorius | 2024 | Unknown | https://in.marketscreener.com/quote/stock/SARTORIUS-AG-436559/news/Hiring-freeze-and-voluntary-redundancies-at-laboratory-supplier-Sartorius-43240015 | Fit for Future programme with voluntary severance; 1,590 departures in 2024, mostly voluntary. Headcount 14,614 to 13,528. Not confirmed against the annual report. |

10-K sources used for the layoffs (`FY2025_10K`):

- Thermo Fisher: https://www.sec.gov/Archives/edgar/data/97745/000009774526000018/tmo-20251231.htm
- Avantor: https://www.sec.gov/Archives/edgar/data/1722482/000162828026007118/avtr-20251231.htm
- Repligen: https://www.sec.gov/Archives/edgar/data/730272/000119312526076528/rgen-20251231.htm
- Danaher: https://www.sec.gov/Archives/edgar/data/313616/000031361626000062/dhr-20251231.htm

## 2. Screen 4 implication questions (Finance and IT): `src/app/shells.py`, `demand_screen`

Typed in the screen, badged Hypothesis. No sheet tab holds them.

1. "Can we report revenue by medicine type?"
2. "Customer pipeline as demand signal?"

## 3. Danaher FY2025 10-K notes (Overview M&A): `src/ingest/company_deals.py`

Source: https://www.sec.gov/Archives/edgar/data/313616/000031361626000062/dhr-20251231.htm

1. FY2025 10-K: no acquisitions in 2025.
2. FY2024 10-K: three businesses acquired for $558 million in cash, net of cash acquired, complementing Life Sciences ($305 million goodwill). The 10-K does not name or date them, so they are not counted as individual deals.
3. Abcam (acquired 6 Dec 2023): cash purchase price of approximately $5.6 billion; about $3.9 billion of goodwill; now part of Life Sciences.

