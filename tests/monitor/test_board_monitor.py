"""Tests for monitor/board_monitor.py — PID lockfile, velocity loader, SIGTERM, threading."""
import os
import signal
import sys
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "monitor"))
import board_monitor  # type: ignore[import-untyped]


# --- _write_pid ---

def test_write_pid_no_existing_lock(tmp_path, monkeypatch):
    monkeypatch.setattr(board_monitor, "_PID_FILE", tmp_path / "monitor.pid")
    board_monitor._write_pid()
    assert (tmp_path / "monitor.pid").read_text().strip() == str(os.getpid())


def test_write_pid_stale_lock_cleared(tmp_path, monkeypatch):
    pid_file = tmp_path / "monitor.pid"
    pid_file.write_text("99999999")  # non-existent PID
    monkeypatch.setattr(board_monitor, "_PID_FILE", pid_file)
    board_monitor._write_pid()
    assert pid_file.read_text().strip() == str(os.getpid())


def test_write_pid_live_process_exits(tmp_path, monkeypatch):
    pid_file = tmp_path / "monitor.pid"
    pid_file.write_text(str(os.getpid()))  # current process IS alive
    monkeypatch.setattr(board_monitor, "_PID_FILE", pid_file)
    with pytest.raises(SystemExit) as exc:
        board_monitor._write_pid()
    assert exc.value.code == 1


def test_write_pid_permission_error_exits(tmp_path, monkeypatch):
    """PermissionError on kill means process is alive (cross-user) — must exit 1."""
    pid_file = tmp_path / "monitor.pid"
    pid_file.write_text("12345")
    monkeypatch.setattr(board_monitor, "_PID_FILE", pid_file)
    with patch("os.kill", side_effect=PermissionError):
        with pytest.raises(SystemExit) as exc:
            board_monitor._write_pid()
    assert exc.value.code == 1




# --- SIGTERM handler ---

def test_sigterm_handler_sets_stop_event(monkeypatch):
    stop_event = threading.Event()
    monkeypatch.setattr(board_monitor, "_stop_event", stop_event)
    monkeypatch.setattr(board_monitor, "_last_analyzer_thread", None)
    with patch.object(board_monitor, "_cleanup_pid"), \
         patch("sys.exit"):
        board_monitor._sigterm_handler(signal.SIGTERM, None)
    assert stop_event.is_set()


# --- analyzer thread dispatch ---

def test_dispatch_analyzer_starts_daemon_thread(monkeypatch):
    """_dispatch_analyzer should start exactly one daemon thread."""
    dispatched = []

    fake_module = MagicMock()
    fake_module.analyze = MagicMock()

    original_thread = threading.Thread

    def capturing_thread(*args, **kwargs):
        t = original_thread(*args, **kwargs)
        dispatched.append(t)
        return t

    monkeypatch.setattr(threading, "Thread", capturing_thread)

    with patch.dict("sys.modules", {"monitor.handlers.intelligence_analyzer": fake_module}), \
         patch.object(board_monitor, "_load_calibration", return_value={}), \
         patch.object(board_monitor, "_stop_event", threading.Event()):
        board_monitor._dispatch_analyzer([], {}, {}, board_config={}, dry_run=False)

    assert len(dispatched) == 1
    assert dispatched[0].daemon is True


def test_dispatch_analyzer_dry_run_does_not_start_thread(monkeypatch):
    """dry_run=True must return immediately without starting any thread."""
    dispatched = []
    original_thread = threading.Thread

    def capturing_thread(*args, **kwargs):
        dispatched.append(True)
        return original_thread(*args, **kwargs)

    monkeypatch.setattr(threading, "Thread", capturing_thread)
    board_monitor._dispatch_analyzer([], {}, {}, board_config={}, dry_run=True)
    assert dispatched == []
