"""Shared pytest fixtures for hooks tests."""
import pytest


@pytest.fixture(autouse=True)
def set_internal_env(monkeypatch):
    """Set ATLASSIAN_PM_INTERNAL=true so parse_stdin() processes input in tests."""
    monkeypatch.setenv("ATLASSIAN_PM_INTERNAL", "true")
