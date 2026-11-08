"""Pytest fixtures and configuration for Orchestrator tests."""

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Ensure orchestrator app is on sys.path
ORCHESTRATOR_ROOT = Path(__file__).resolve().parent.parent
if str(ORCHESTRATOR_ROOT) not in sys.path:
    sys.path.insert(0, str(ORCHESTRATOR_ROOT))

# Set test environment variables
os.environ["ENVIRONMENT"] = "test"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["LLM_MOCK_LATENCY"] = "0.0"
os.environ["DATA_DIR"] = ":memory:"
os.environ["DOMAIN_PACKS_DIR"] = str(ORCHESTRATOR_ROOT.parent / "domain_packs")


@pytest.fixture
def packs_dir():
    """Return path to domain packs directory."""
    return Path(os.environ["DOMAIN_PACKS_DIR"])


@pytest.fixture
def test_client():
    """FastAPI TestClient fixture."""
    from app.main import app

    with TestClient(app) as client:
        yield client
