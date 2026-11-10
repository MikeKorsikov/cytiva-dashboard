# Competitor coverage: research log (screen 2)

Purpose: fill the product-family matrix (8 families × 4 regions × 6 companies) from public
sources. Data lives in `src/ingest/coverage.py`; each row carries its source URL. A cell with no
row shows as "to collect". Nothing is estimated.

Companies: Cytiva (Danaher), Thermo Fisher, Sartorius, Repligen, Avantor, Merck KGaA.

Regions follow the Danaher reporting regions used on the screen: North America; Western
Europe; High-growth markets; Japan, Australia and New Zealand.

## Method

1. Primary documents first: FY2025 annual report or Form 10-K, Item 2 (Properties) and
   the manufacturing description in Item 1.
2. Company releases and company site lists next, for sites the annual report does not name.
3. Trade press only where the company's own release is not available, and labelled as such.
4. A product family is made at a site only when a source names that site and the product.
   A site with no stated product line is left "to collect".

## Findings by company

### Cytiva (Danaher)

- **Source:** BioProcess International, 11 June 2025, on Cytiva's $1.6bn investment programme
  (https://www.bioprocessintl.com/facilities-capacity/cytiva-outlines-1-6bn-facility-investment-plans-through-2028).
- Sites named with their products: Uppsala SE (resins, capacity doubled); Muskegon MI (resins
  site, operational by 2028); Pensacola FL (filtration lines being installed); Logan UT (media,
  dry powder and liquid); Fajardo PR (filtration upgrades and expansion); Ilfracombe UK
  (filtration devices); South Korea (filtration, from 2026, city not stated).
- **Correction:** the earlier mockup banner cited "Danaher 10-K site list". The FY2025 10-K
  Item 2 gives only totals (about 194 significant facilities, 77 in the US and 117 outside).
  It names no sites. Cytiva cells therefore come from the company programme above, not the 10-K.
- Gaps: single-use, systems, filling, genomic and analytical are not named for any Cytiva site.

### Repligen

- **Source:** Form 10-K FY2025, Item 2 (Properties) and Item 1 (Manufacturing)
  (https://www.sec.gov/Archives/edgar/data/730272/000119312526076528/rgen-20251231.htm).
- Item 2 lists sites by principal use: Waltham MA (chromatography manufacturing); Marlborough
  MA (manufacturing; products in Item 1: XCell ATF, FS TFF, Spectrum HF; process analytics);
  Hopkinton MA (assembly center, single-use); Rancho Dominguez CA, Clifton Park NY, Bridgewater
  NJ (manufacturing; products as stated in Item 1); Toulouse FR, Jüri EE, Waterford IE
  (filtration, Item 1); Lund SE (proteins, Item 1); Germany and the Netherlands (chromatography,
  Item 1); Braunschweig DE (process analytics, Item 1).
- Gaps: Rancho Dominguez and Clifton Park product lines are not stated. No Repligen site is
  listed for High-growth markets or Japan, Australia and New Zealand; those cells stay "to collect".

### Sartorius

- **Source:** Annual Report 2025, Combined Group Management Report, Bioprocess Solutions
  (https://www.sartorius.com/download/1796536/fy-2025-download-annual-report-sag-en-data.pdf).
  Page numbers below are PDF pages.
- p. 35 lists production sites by country: USA (Albuquerque, Ann Arbor, Ashland, Fremont,
  Marlborough, New Oxford); Puerto Rico (Yauco); France (Aubagne, Cergy, Loos, Lourdes, Pompey,
  Strasbourg); Germany; China (Beijing, Shanghai); India (Bangalore); Israel (Beit Haemek);
  and others.
- p. 60: largest production sites in Germany, France and Puerto Rico; also UK, Belgium,
  Switzerland, Tunisia, India, the USA, China, Israel and Slovenia. Aubagne (FR) makes sterile
  single-use bags, tubing and connectors.
- p. 61: Illkirch (FR) makes transfection reagents, which are not cell culture media (Partial).
- p. 77: Beit Haemek (IL) makes cell culture media.
- Gaps: the report does not map the German, US, Puerto Rico, Chinese and Indian sites to
  product families, so those cells stay "to collect".

### Merck KGaA (MilliporeSigma Process Solutions)

- **Sources:** company releases, 2020 to 2025. The FY2025 annual report did not show the
  production-site list in the search results, so these are older releases and are labelled so.
- Molsheim FR: single-use assemblies and Mobius capacity
  (https://sigmaaldrich.com/US/en/collections/press/investment-to-strengthen-manufacturing-capabilities-in-molsheim-france).
- Cork IE: membrane manufacturing expansion
  (https://sigmaaldrich.com/collections/press/expansion-membrane-filtration-manufacturing-ireland).
- Darmstadt DE: sterilizing membrane manufacturing; cited as a second source for the Cork cell
  (https://chemengonline.com/milliporesigma-launches-membrane-manufacturing-facility-in-darmstadt).
  The footprint table holds one row per cell, so the Cork row is the stored source.
- Jaffrey NH: filtration devices, 2020 release, marked Partial
  (https://www.emdgroup.com/en/news/ls-expansions-07-12-2020.html).
- Danvers MA and Wuxi CN are named as production sites in the 2020 release, with no product
  stated: "to collect".
- Gaps: Bedford MA was not confirmed as a production site.

### Thermo Fisher

- Form 10-K FY2025 Item 2 gives only a general statement ("office, engineering, laboratory,
  production and warehouse space throughout the world"). No site list.
- **Result:** all cells "to collect". Site-level sources would come from Thermo Fisher's
  release on its US manufacturing investment, which names sites, but not yet checked.

### Avantor

- Form 10-K FY2025 Item 1 says over 40 global manufacturing facilities, 6 cGMP compliant, in
  North America, Europe and AMEA. Item 2 gives totals only.
- **Result:** all cells "to collect".

## Open items

1. Thermo Fisher and Avantor site lists: find company releases or site pages that name sites
   and products.
2. Sartorius: map its German, US, Puerto Rico, Chinese and Indian sites to product families.
3. Repligen: confirm the product lines at Rancho Dominguez and Clifton Park.
4. Merck KGaA: find the FY2025 site list (annual report or investor site) to replace the
   2020 releases.
5. Cytiva: Cytiva site pages for single-use, systems and analytical sites.
6. Steps matrix (bioprocess steps by region): derived from the families matrix using the
   step-to-family rules on the screen. Not yet derived; all step cells are "to collect".

## Update (10 Nov 2026): Thermo Fisher, Avantor, and link to source on every mark

- **Thermo Fisher:** the FY2025 10-K Item 2 gives no site list. Site-level facts come from the
  company's 2020–22 bioprocessing materials programme (more than $600m), as reported by DCAT
  Value Chain Insights: single-use at Logan UT, Millersburg PA, Nashville TN (announced),
  Cramlington UK, Singapore and Suzhou CN; media at Grand Island NY, Miami FL and Inchinnan UK.
  Because these are dated, every cell is **Partial** until the current status is confirmed.
  Source: https://www.dcatvci.org/top-industry-news/thermo-fisher-to-invest-600-m-to-expand-bioprocessing-materials-capacity/
  The April 2026 Plainville, MA design centre is a customer space, not production, so it is not
  counted. Resins and filtration sites were not found.
- **Avantor:** the FY2025 10-K gives totals only. Two dated sources: the Gliwice, Poland buffer,
  media and clean-in-place plant (Q4 2024 call, secondary transcript: https://www.roic.ai/quote/AVTR-PA/transcripts/2024-year/4-quarter)
  and the Changzhou, China single-use plant from the RIM Bio acquisition (2021: https://www.pharmaceuticalprocessingworld.com/avantor-acquires-rim-bio-to-bolster-presence-in-asia/).
  Both are **Partial**.
- **Display:** each mark on screen 2 now links to its source, per the standing preference for
  dashboard tables.

Open items after this update: confirm current status of Thermo Fisher's 2020–22 sites; find
Avantor's US and European single-use and filtration site list; find Thermo Fisher's resin and
filtration sites.

## Classification rules (10 Nov 2026)

- **Resins** means bulk chromatography bead resins only, so the comparison is like for like.
  Ligands, pre-packed columns, monoliths, membranes and affinity products are filed under
  "Other chromatography" (evidence kept, not counted in the grid).
- **Service and support** is shown as a row without a step number. It is not a manufacturing
  step and is not counted in "steps local".
- Contract (customer-order) manufacturing is "Service only" and is not counted.
