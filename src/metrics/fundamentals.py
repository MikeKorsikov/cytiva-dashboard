"""KPI calculations for the Peer financials tile (CD-3, screen 1).

Pure functions: they take stored values and return a number or None. None means the input
is missing, so the tile shows "n/d" rather than a guess.
"""

from __future__ import annotations


def yoy_growth_pct(current: float | None, previous: float | None) -> float | None:
    """Year-on-year growth in percent."""
    if current is None or previous is None or previous == 0:
        return None
    return (current / previous - 1) * 100


def margin_pct(numerator: float | None, revenue: float | None) -> float | None:
    """Numerator as a percentage of revenue (gross margin, net margin, FCF margin, SG&A ratio)."""
    if numerator is None or revenue is None or revenue == 0:
        return None
    return numerator / revenue * 100


def free_cash_flow(operating_cash_flow: float | None, capex: float | None) -> float | None:
    """Free cash flow = operating cash flow minus capital expenditure.

    `capex` is the amount spent, as reported by PaymentsToAcquirePropertyPlantAndEquipment.
    """
    if operating_cash_flow is None or capex is None:
        return None
    return operating_cash_flow - abs(capex)
