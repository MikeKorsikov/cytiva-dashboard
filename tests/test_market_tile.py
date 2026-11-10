"""Tile 3 (MVP layout): the sample pie. The values are mockup samples, not sourced data."""

from src.app import market_tile


def test_sample_share_is_the_mockup_ratio():
    assert market_tile.SAMPLE_DANAHER_BN == 7.5
    assert market_tile.SAMPLE_MARKET_BN == 37.5
    assert abs(market_tile.share_pct() - 20.0) < 1e-9


def test_pie_splits_the_market_into_danaher_and_the_rest():
    fig = market_tile._pie()
    values = list(fig.data[0].values)
    assert values == [7.5, 30.0]
