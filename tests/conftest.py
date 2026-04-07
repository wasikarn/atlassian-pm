import pytest
import os
import shutil
import tempfile
from pathlib import Path

@pytest.fixture
def temp_state_dir(monkeypatch):
    """Creates a temporary directory for state storage and patches STATE_DIR."""
    temp_dir = tempfile.mkdtemp()
    monkeypatch.setattr("hooks.hooks_state.STATE_DIR", Path(temp_dir))
    monkeypatch.setattr("hooks.hooks_state._STATE_DIR_STR", str(temp_dir))
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)

@pytest.fixture
def session_id():
    return "test-session-123"
