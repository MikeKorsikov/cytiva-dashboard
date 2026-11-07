"""Tests for settings loading. No network access."""

import pytest

from src.ingest import config


def test_missing_required_setting_raises_clear_error(monkeypatch):
    monkeypatch.delenv("EDGAR_USER_AGENT", raising=False)
    monkeypatch.setattr(config, "load_env_file", lambda: None)
    with pytest.raises(config.ConfigError, match="EDGAR_USER_AGENT"):
        config.get_setting("EDGAR_USER_AGENT")


def test_optional_setting_returns_none_when_missing(monkeypatch):
    monkeypatch.delenv("SOME_OPTIONAL_KEY", raising=False)
    monkeypatch.setattr(config, "load_env_file", lambda: None)
    assert config.get_setting("SOME_OPTIONAL_KEY", required=False) is None


def test_setting_is_read_and_stripped(monkeypatch):
    monkeypatch.setenv("EDGAR_USER_AGENT", "  Example Name test@example.com  ")
    monkeypatch.setattr(config, "load_env_file", lambda: None)
    assert config.edgar_user_agent() == "Example Name test@example.com"


def test_blank_setting_counts_as_missing(monkeypatch):
    monkeypatch.setenv("EDGAR_USER_AGENT", "   ")
    monkeypatch.setattr(config, "load_env_file", lambda: None)
    with pytest.raises(config.ConfigError):
        config.edgar_user_agent()
