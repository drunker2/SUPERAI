"""Pytest configuration and fixtures."""

import pytest


@pytest.fixture
def app():
    """Create test application."""
    from app.main import app
    return app
