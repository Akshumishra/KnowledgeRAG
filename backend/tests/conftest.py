import pytest
from fastapi.testclient import TestClient
from src.api.main import app
from src.core.config import settings

@pytest.fixture(scope="session")
def test_client():
    """Provides a TestClient for FastAPI"""
    with TestClient(app) as client:
        yield client

@pytest.fixture(autouse=True)
def override_settings(monkeypatch):
    """Override configuration settings for testing."""
    monkeypatch.setattr(settings, "app_env", "testing")
    monkeypatch.setattr(settings, "database_url", "sqlite+aiosqlite:///:memory:")
