# Screen 3: legacy source (Tholos index, applied tariff, direction, scope)

Status: LEGACY, to move into the seed sheet. These values are still read from the old CSVs (`data/clusters/country_barrier.csv`, `data/clusters/market_signals.csv`, `data/clusters/clusters.csv`). The loader marks each one as legacy (`country_barrier_index.legacy_fields`). A test (`test_legacy_exception_ends_once_the_sheet_has_the_columns`) fails once the sheet has the columns. Owner (22 Nov 2026): the Tholos score and the applied tariff are kept on screen 3 as SIGNAL at most, until they are added to the Country barriers tab.

## 1. Country figures

Tholos rank is not stored in the old file, so the rank column is empty. Source URLs are exactly as the old file records them. The tariff score is the WTO band rule (1 below 5 percent, 3 for 5 to 10 percent, 5 at 10 percent and above) as stored.

| Country | Tholos 2025 score (lower = more open) | Tholos rank | Applied tariff % | Tariff year | Tariff score (1 / 3 / 5) | Tariff source URL | Tholos source URL |
|---|---|---|---|---|---|---|---|
| China | 5.16 | (not stored) | 7.5 | 2025 | 3 | https://wto.org/english/res_e/booksp_e/tariffprofiles2026.pdf | https://www.tradebarrierindex.org/ |
| Brazil | 3.86 | (not stored) | 12.0 | 2025 | 5 | https://wto.org/english/res_e/booksp_e/tariffprofiles2026.pdf | https://www.tradebarrierindex.org/ |
| India | 5.72 | (not stored) | 16.0 | 2025 | 5 | https://wto.org/english/res_e/booksp_e/tariffprofiles2026.pdf | https://www.tradebarrierindex.org/ |
| United States | 4.19 | (not stored) | 3.3 | 2025 | 1 | https://wto.org/english/res_e/booksp_e/tariffprofiles2026.pdf | https://www.tradebarrierindex.org/ |
| South Korea | 4.61 | (not stored) | 13.5 | 2025 | 5 | https://wto.org/english/res_e/booksp_e/tariffprofiles2026.pdf | https://www.tradebarrierindex.org/ |
| Japan | 3.07 | (not stored) | 3.7 | 2025 | 1 | https://wto.org/english/res_e/booksp_e/tariffprofiles2026.pdf | https://www.tradebarrierindex.org/ |
| Germany | 3.45 | (not stored) | 4.9 | 2025 | 1 | https://wto.org/english/res_e/booksp_e/tariffprofiles2026.pdf | https://www.tradebarrierindex.org/ |
| United Kingdom | 3.33 | (not stored) | 3.7 | 2025 | 1 | https://wto.org/english/res_e/booksp_e/tariffprofiles2026.pdf | https://www.tradebarrierindex.org/ |
| Singapore | 2.78 | (not stored) | 0.0 | 2025 | 1 | https://wto.org/english/res_e/booksp_e/tariffprofiles2026.pdf | https://www.tradebarrierindex.org/ |
| Ireland | 3.52 | (not stored) | 4.9 | 2025 | 1 | https://wto.org/english/res_e/booksp_e/tariffprofiles2026.pdf | https://www.tradebarrierindex.org/ |
| Switzerland | 3.41 | (not stored) | 3.9 | 2025 | 1 | https://wto.org/english/res_e/booksp_e/tariffprofiles2026.pdf | https://www.tradebarrierindex.org/ |

## 2. Market signal direction (legacy)

| Indicator ID | Indicator | Direction | Source URL |
|---|---|---|---|
| M01 | Biologics license applications in CDER Product Catalog | none | https://www.fda.gov/media/188236/download |
| M02 | Novel drugs approved by FDA CDER | none | https://www.fda.gov/drugs/novel-drug-approvals-fda/novel-drug-approvals-2025 |
| M03 | Novel active substances launched | none | https://www.iqvia.com/pl-pl/insights/the-iqvia-institute/reports-and-publications/reports/global-trends-in-r-and-d |
| M04 | Novel active substances launched | none | https://www.iqvia.com/pl-pl/insights/the-iqvia-institute/reports-and-publications/reports/global-trends-in-r-and-d |
| M05 | Novel active substances launched only in China | none | https://www.iqvia.com/pl-pl/insights/the-iqvia-institute/reports-and-publications/reports/global-trends-in-r-and-d |
| M06 | Share of global clinical trial country uses | down | https://www.iqvia.com/pl-pl/insights/the-iqvia-institute/reports-and-publications/reports/global-trends-in-r-and-d |
| M07 | Drug pipeline growth Jul 2025 to Jul 2026 | up | https://www.wbur.org/news/2026/08/25/massbio-industry-2026-snapshot-jobs-funding |
| M08 | Companies with an R&D pipeline | up | https://soci.org/chemistry-and-industry/cni-data/2026/5/pharma-r-and-d-what-is-in-the-pipeline |
| M09 | Drugs in R&D pipeline | down | https://soci.org/chemistry-and-industry/cni-data/2026/5/pharma-r-and-d-what-is-in-the-pipeline |
| M10 | Pharma US manufacturing investment pledged 2025 (next five years) | up | https://www.fiercepharma.com/manufacturing/pharmas-have-poured-370b-us-manufacturing-amid-2025s-onshoring-boom-dpr |
| M11 | Mammalian cell culture capacity installed | none | https://www.bioprocessintl.com/facilities-capacity/rise-of-the-recombinants-global-mammalian-capacity-to-reach-8-400kl-by-2027 |
| M12 | Share of Danaher sales from China | none | https://www.sec.gov/Archives/edgar/data/313616/000031361626000062/dhr-20251231.htm |
| M13 | R&D spending (GERD): China passed the US | up | https://oecd.org/en/data/insights/statistical-releases/2026/03/oecd-overall-rd-growth-stable-government-rd-budgets-decline-and-reorient-towards-defence.html |

## 3. Cluster fact scope (legacy)

Scope tells the density count whether it is a cluster base, city-wide or capacity.

| Fact ID | Cluster | Metric | Scope |
|---|---|---|---|
| F001 | KR-SONGDO | Biologics production capacity in cluster | capacity |
| F002 | KR-SONGDO | Samsung Biologics capacity (5 plants) | capacity |
| F003 | KR-SONGDO | Celltrion capacity (3 plants) | capacity |
| F004 | KR-SONGDO | Lotte Biologics Plant 1 capacity under construction | capacity |
| F030 | KR-SONGDO | Lotte Biologics Bio Campus plan | capacity |
| F005 | US-BOSTON | Share of US drug development pipeline | n/a |
| F006 | US-BOSTON | Venture capital raised H1 2026 | n/a |
| F007 | US-BOSTON | Biopharma roles cut in 2025 | n/a |
| F008 | US-RTP | Life sciences investment announced 2025 | n/a |
| F009 | US-RTP | Life sciences projects announced 2025 | n/a |
| F010 | SG | Biopharma manufacturing sites | cluster |
| F011 | SG | Biopharma manufacturing output | n/a |
| F012 | SG | Biopharma employment | n/a |
| F013 | IE | Biopharma plants | cluster |
| F014 | IE | Biopharma investment under construction | n/a |
| F015 | IE | FDA-catalogued drug manufacturing sites | cluster |
| F016 | CH-BASEL | Companies that settled in region in 2024 (life sciences) | n/a |
| F017 | CN-SUZHOU | Biopharma companies in Suzhou | cluster |
| F018 | IN-HYD | Biotech and pharma companies in Genome Valley | cluster |
| F019 | IN-HYD | Telangana share of India pharma production | n/a |
| F020 | CN-SHANGHAI | Biomedical enterprises mapped (city-wide) | city-wide |
| F021 | CN-BEIJING | Biomedicine enterprises in Daxing Biomedical Industry Base | cluster |
| F022 | CN-BEIJING | Biomedical enterprises mapped (city-wide) | city-wide |
| F023 | CN-SHANGHAI | Biomedical industry professionals in Pudong | n/a |
| F024 | DK-SE-MEDICON | Companies with active pipeline products (HQ in cluster) | cluster |
| F025 | UK-GOLDEN | Companies with active pipeline products (HQ in cluster) | cluster |
| F026 | CH-BASEL | Companies with active pipeline products (HQ in cluster) | cluster |
| F027 | DE-MUNICH | Companies with active pipeline products (HQ in cluster) | cluster |
| F028 | BE-FLANDERS | Companies with active pipeline products (HQ in cluster) | cluster |
| F029 | JP-SHONAN | Companies and organisations in the park | cluster |

## 4. To do (owner)

1. Check the country figures above and add Tholos score, Tholos rank, applied tariff, tariff year, and their source IDs to the Country barriers tab (headers as in the tests, `Tholos index 2025`, `Tariff applied (%)`, `Tariff year`, `Tariff score (1-5)`).
2. Add `Direction` to Market signals and `Scope` to Clusters, with the values above.
3. Switch the loader to the sheet columns, delete the three legacy CSVs, and remove the exception.
