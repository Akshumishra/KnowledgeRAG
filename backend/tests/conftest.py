"""
Pytest configuration and shared fixtures.

IMPORTANT: DATABASE_URL must be set in the environment *before* importing
anything from src, because settings is read at first import.  We set it
here at module level so that even `from src.api.main import app` (below)
sees the SQLite URL.
"""
import os

# Point the app at an in-memory SQLite database for every test run.
# This must happen before any src.* import so that pydantic-settings
# picks up the value when the Settings object is first constructed.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("APP_ENV", "testing")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("ENCRYPTION_KEY", "")

import pytest  # noqa: E402  (imports after env setup are intentional)
from fastapi.testclient import TestClient  # noqa: E402

from src.api.main import app  # noqa: E402  (engine not yet created here)
from src.core.config import settings  # noqa: E402
from src.database.session import _get_engine  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def configure_test_db():
    """
    Ensure the lazy engine cache is cleared and rebuilt with the SQLite URL.
    Runs once per test session before any test.
    """
    # Clear the cached engine so it re-reads from the (already overridden) env.
    _get_engine.cache_clear()
    yield
    _get_engine.cache_clear()


@pytest.fixture(scope="session")
def test_client():
    """Provides a TestClient for FastAPI."""
    with TestClient(app) as client:
        yield client
