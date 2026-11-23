"""The listed peers whose share prices the app shows (CD-13).

Pure data: the loader in src/ingest/prices.py fetches them, the metrics read the list.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ListedPeer:
    company: str
    ticker: str  # Yahoo Finance symbol
    currency: str  # ISO code of the trading currency


LISTED_PEERS: tuple[ListedPeer, ...] = (
    ListedPeer("Danaher", "DHR", "USD"),
    ListedPeer("Thermo Fisher", "TMO", "USD"),
    ListedPeer("Sartorius", "SRT3.DE", "EUR"),
    ListedPeer("Repligen", "RGEN", "USD"),
    ListedPeer("Avantor", "AVTR", "USD"),
    ListedPeer("Merck KGaA", "MRK.DE", "EUR"),  # group price and group financials
)
