# Layoffs tile: research log (2024 to 2026)

Source file: `src/ingest/layoffs.py`. Tile: Overview, between Deal activity and Competitor news.

## Mark rules

- **✓ (Yes):** a company filing, release or report states job cuts or severance for that year.
- **✗ (No):** none found in the sources searched. This is not proof that no cuts happened.
- **? (Unknown):** the source is undated, or does not say whether cuts were made.

## Findings

| Company | 2026 | 2025 | 2024 | Main sources |
|---|---|---|---|---|
| Thermo Fisher | ✓ Franklin, MA site phased out; WARN lists 103 roles, company says capped at 80 | ✓ about 85 layoffs at Carlsbad, CA; also Massachusetts cuts. FY2025 10-K: severance about 5% of workforce | ✓ FY2025 10-K: severance about 2% of workforce | Fierce Pharma (Franklin, Carlsbad); FY2025 10-K |
| Merck KGaA | ✗ none found | ✗ none found | ✗ none found | Latest cuts found date from 2012–2013 (1,100 German jobs). Merck KGaA's FY2025 reports searched, none found |
| Danaher | ✗ none found | ✗ none found | ✗ none found | FY2025 10-K read only in part. Still to check |
| Avantor | ✓ Avantor Fluid Handling, Morrisville, NC: 54 employees (third-party tracker, WARN-based, not verified) | ? 2024 programme severance reversed by $5.3m; no new charges stated | ✓ FY2025 10-K: 2024 multi-year programme, $82.8m charges, $64.3m severance | Layofftracker; FY2025 10-K |
| Repligen | ✓ Q3 2026 10-Q: restructuring to simplify the manufacturing footprint; severance $3.3m in H1. Headcount not disclosed | ? Q1 2025 charges mainly facility-related (severance $12k) | ? no 2024 headcount detail found | 10-Q Q3 2026; FY2025 10-K |
| Sartorius | ✗ none found | ✗ hiring again (2025 coverage) | ? voluntary programme at HQ (about 200 roles, not confirmed by the company; undated) | Ärzteblatt (2025); MarketScreener (undated) |

## Caveats

- Thermo Fisher and Avantor 2026 and Repligen 2026 rely on the company filings or a third-party
  tracker, as noted per cell.
- Danaher and Merck KGaA crosses are the weakest cells. The FY2025 10-Ks and reports were not read
  in full for headcount actions. Both should be checked before the tile is shown as final.
- Headcount figures are as reported. Where a company does not disclose headcount, the cell
  records the cuts without a number.

## Open items

1. Danaher: read the FY2025 10-K restructuring note and the 2026 10-Qs for workforce actions.
2. Merck KGaA: read the 2025 annual report sections on restructuring and headcount.
3. Sartorius 2024: find the date and outcome of the HQ voluntary programme.
4. Repligen 2024 and 2025 and Avantor 2025: find headcount detail in the filings.

## Update: reconciled table (10 Nov 2026)

Two external reviews were received with different figures. Each cell was checked against a
primary source where one was reachable. Where the reviews still disagree, the mark is "?".

Confirmed or updated:
- Thermo Fisher 2026: Germany confirmed by Eurofound (Bremen up to 100; Langenselbold about 60).
- Avantor 2025: FY2025 10-K restructuring and severance charges of $29.8m (not $35.1m, which is
  the "other" line). Headcount not disclosed.
- Repligen 2026: Q3 2026 10-Q, severance $3.9m in nine months; no headcount given.
- Danaher 2025: the $250m cost actions are described with different timing in different sources
  (2025 realised vs 2026 benefit). Marked Yes for the cuts; timing to check against the transcript.

Still to verify:
- Merck KGaA 2026 (Billerica, 20 jobs vs none found): "?".
- Merck KGaA 2025 Martillac, France (109 jobs) reported in one review only.
- Thermo Fisher Carlsbad 173 (Jan 2026) and Asheville closure (about 420) reported in one review only.
- Repligen 2024 and Sartorius 2024: programmes with undisclosed headcount.
