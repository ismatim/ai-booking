import pytest
from fastapi.testclient import TestClient
from main import app  # Import your FastAPI app
from unittest.mock import MagicMock


@pytest.fixture
def client():
    """Test client for FastAPI endpoints."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def mock_db():
    """Mock for SupabaseService to avoid real DB calls."""
    return MagicMock()


@pytest.fixture
def mock_messenger():
    """Mock for WhatsApp/Twilio services."""
    return MagicMock()
