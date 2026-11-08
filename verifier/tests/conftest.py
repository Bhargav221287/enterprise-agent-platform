"""Pytest configuration and fixtures for Verifier tests."""

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

VERIFIER_ROOT = Path(__file__).resolve().parent.parent
if str(VERIFIER_ROOT) not in sys.path:
    sys.path.insert(0, str(VERIFIER_ROOT))

os.environ["ENVIRONMENT"] = "test"


@pytest.fixture
def test_client():
    from app.main import app

    with TestClient(app) as client:
        yield client
