import pytest

from app.config import Settings


def test_from_env_reads_variables(monkeypatch):
    monkeypatch.setenv("METRICS_ENDPOINT", "http://api:8000/metrics")
    monkeypatch.setenv("COLLECTION_INTERVAL", "10")
    monkeypatch.setenv("REQUEST_TIMEOUT", "2")

    settings = Settings.from_env()

    assert settings.metrics_endpoint == "http://api:8000/metrics"
    assert settings.collection_interval == 10
    assert settings.request_timeout == 2


def test_from_env_rejects_non_numeric(monkeypatch):
    monkeypatch.setenv("COLLECTION_INTERVAL", "abc")

    with pytest.raises(ValueError, match="numériques"):
        Settings.from_env()


def test_from_env_rejects_zero(monkeypatch):
    monkeypatch.setenv("COLLECTION_INTERVAL", "5")
    monkeypatch.setenv("REQUEST_TIMEOUT", "0")

    with pytest.raises(ValueError, match="> 0"):
        Settings.from_env()
