"""Smoke test: the pinned environment imports the core dependencies."""

import sys


def test_python_version_is_313_or_newer():
    assert sys.version_info >= (3, 13)


def test_core_dependencies_import():
    import gspread
    import pandas
    import requests
    import streamlit
    import yfinance

    for module in (gspread, pandas, requests, streamlit, yfinance):
        assert module.__name__
