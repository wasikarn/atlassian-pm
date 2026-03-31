# Intelligence Automation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automate 3 manual steps in the intelligence pipeline: launchd daemon for board_monitor, calibrate.py trigger at sprint close, and calibrate.py trigger on story_outcome_record.py calls.

**Architecture:** 6 independent tasks. Tasks 1–2 are Python with TDD. Tasks 3, 6 are SKILL.md / markdown edits. Tasks 4–5 are bash scripts (shellcheck, no unit tests). All tasks can be committed independently.

**Tech Stack:** Python 3.x stdlib (`threading`, `fcntl`, `subprocess`), bash, macOS launchd, SKILL.md markdown.

---

## File Map

| File | Action |
|------|--------|
| `scripts/ai/calibrate.py` | MODIFY — add `_hard_timeout()` + `_LOCK_FILE` + lock in `run_calibration()` |
| `tests/scripts/test_calibrate.py` | MODIFY — add 3 new tests for B8/B9 |
| `scripts/story_outcome_record.py` | MODIFY — add `import subprocess, sys` + calibrate spawn at end of `main()` |
| `tests/scripts/test_story_outcome_record.py` | CREATE — 3 tests for spawn behavior |
| `skills/sprint/close-sprint/SKILL.md` | MODIFY — Phase 8: detached nohup spawn after story_outcome_record block |
| `scripts/setup_monitor.sh` | CREATE — launchd daemon installer |
| `scripts/teardown_monitor.sh` | CREATE — launchd daemon uninstaller |
| `skills/setup/doctor/SKILL.md` | MODIFY — add check 11 for board_monitor daemon |
| `QUICKSTART.md` | MODIFY — add optional monitor setup step |

---

## Task 1: calibrate.py — B8 hard timeout + B9 fcntl.flock

**Files:**

- Modify: `scripts/ai/calibrate.py`
- Test: `tests/scripts/test_calibrate.py`

- [ ] **Step 1: Write 3 failing tests in `tests/scripts/test_calibrate.py`**

Add at the end of the existing file (after the last existing test):

```python
# ── _hard_timeout ─────────────────────────────────────────────────────────────

class _FakeTimer:
    def __init__(self, interval, fn):
        self.interval = interval
        self.fn = fn
        self.daemon = False
        self._started = False
        self._cancelled = False
    def start(self):
        self._started = True
    def cancel(self):
        self._cancelled = True


def test_hard_timeout_creates_started_daemon_timer(monkeypatch):
    captured = []
    def fake_timer(interval, fn):
        t = _FakeTimer(interval, fn)
        captured.append(t)
        return t
    monkeypatch.setattr(calibrate.threading, "Timer", fake_timer)
    t = calibrate._hard_timeout(30)
    assert len(captured) == 1
    assert captured[0].interval == 30
    assert captured[0].daemon is True
    assert captured[0]._started is True
    t.cancel()
    assert captured[0]._cancelled is True


# ── run_calibration flock ──────────────────────────────────────────────────────

def test_run_calibration_returns_none_when_lock_held(tmp_path, monkeypatch):
    """When another process holds the lock, run_calibration returns None immediately."""
    def locked_flock(fd, op):
        raise BlockingIOError("lock held by another process")
    monkeypatch.setattr(calibrate.fcntl, "flock", locked_flock)
    monkeypatch.setattr(calibrate, "_hard_timeout", lambda secs=60: _FakeTimer(secs, lambda: None))

    outcomes = _write_outcomes(tmp_path, [_make_record("BE", "completed")] * 15)
    cal_path = tmp_path / "calibration.json"
    lock_path = tmp_path / "calibration.lock"

    result = calibrate.run_calibration(
        outcomes_path=outcomes,
        calibration_path=cal_path,
        lock_file=lock_path,
        force=True,
    )
    assert result is None
    assert not cal_path.exists()


def test_run_calibration_cancels_timer_on_success(tmp_path, monkeypatch):
    """Timer is cancelled after successful calibration."""
    timer = _FakeTimer(60, lambda: None)
    monkeypatch.setattr(calibrate, "_hard_timeout", lambda secs=60: timer)
    # Use real flock — lock_path in tmp_path is isolated
    outcomes = _write_outcomes(tmp_path, [_make_record("BE", "completed")] * 6)
    cal_path = tmp_path / "calibration.json"
    lock_path = tmp_path / "calibration.lock"

    calibrate.run_calibration(
        outcomes_path=outcomes,
        calibration_path=cal_path,
        lock_file=lock_path,
        force=True,
    )
    assert timer._cancelled is True
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python3 -m pytest tests/scripts/test_calibrate.py::test_hard_timeout_creates_started_daemon_timer tests/scripts/test_calibrate.py::test_run_calibration_returns_none_when_lock_held tests/scripts/test_calibrate.py::test_run_calibration_cancels_timer_on_success -v
```

Expected: 3 FAILs — `AttributeError: module 'calibrate' has no attribute 'threading'` and `TypeError: run_calibration() got unexpected keyword argument 'lock_file'`

- [ ] **Step 3: Add `import threading` to `scripts/ai/calibrate.py` imports**

In `scripts/ai/calibrate.py`, the import block starts at line 15. Add `threading` to the existing imports:

```python
import argparse
import fcntl
import json
import os
import re
import sys
import threading
from datetime import UTC, datetime
from pathlib import Path
```

- [ ] **Step 4: Add `_LOCK_FILE` constant after `_CALIBRATION_FILE`**

In `scripts/ai/calibrate.py`, after the line:
```python
_CALIBRATION_FILE = _DATA_DIR / "calibration.json"
```
Add:
```python
_LOCK_FILE = _DATA_DIR / "calibration.lock"
```

- [ ] **Step 5: Add `_hard_timeout()` function before `run_calibration()`**

In `scripts/ai/calibrate.py`, insert before the `def run_calibration(` line:

```python
def _hard_timeout(seconds: int = 60) -> threading.Timer:
    """Kill the process if calibration takes too long (fire-and-forget protection)."""
    def _kill() -> None:
        os._exit(1)
    t = threading.Timer(seconds, _kill)
    t.daemon = True
    t.start()
    return t
```

- [ ] **Step 6: Modify `run_calibration()` — add `lock_file` param + timeout + flock**

Replace the entire `run_calibration()` function with:

```python
def run_calibration(
    outcomes_path: Path = _OUTCOMES_FILE,
    calibration_path: Path = _CALIBRATION_FILE,
    lock_file: Path = _LOCK_FILE,
    force: bool = False,
) -> dict | None:
    """Run calibration. Returns result dict or None if skipped/no data."""
    timer = _hard_timeout(60)
    lock_fd = open(lock_file, "w")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        timer.cancel()
        lock_fd.close()
        return None  # another calibration is running — exit cleanly
    try:
        if not outcomes_path.exists():
            return None

        lines = outcomes_path.read_text().splitlines()
        current_count = sum(1 for l in lines if l.strip())

        existing_cal = load_calibration(calibration_path)
        if not force and not _should_run(current_count, existing_cal):
            return None

        records = _parse_records(lines[-_MAX_RECORDS:])
        if not records:
            return None

        allowlist = load_allowlist()

        # Group by service_tag
        groups: dict[str, list[dict]] = {}
        for r in records:
            tag = r["service_tag"]
            if tag:
                groups.setdefault(tag, []).append(r)

        service_tags_out: dict = {}
        excluded_groups: dict = {}

        for tag, grp in groups.items():
            weights = [_weight(r["age_days"]) for r in grp]
            sum_w = sum(weights)
            if sum_w == 0:
                continue

            carry_sum_w = sum(w for r, w in zip(grp, weights) if r["is_carry_over"])
            carry_over_rate = carry_sum_w / sum_w
            decay_weight_mean = sum_w / len(weights)
            eff_n = _effective_n(weights)
            conf = _confidence(eff_n)

            if conf is None:
                excluded_groups[tag] = {"record_count": len(grp), "reason": "below_min_n"}
                continue

            keyword_risk = _compute_keyword_risk(grp, weights, sum_w, carry_sum_w, allowlist)

            service_tags_out[tag] = {
                "carry_over_rate": round(carry_over_rate, 4),
                "n": len(grp),
                "confidence": conf,
                "decay_weight": round(decay_weight_mean, 4),
                "keyword_risk": keyword_risk,
                "keyword_method": "weighted_odds_ratio_laplace_alpha1",
            }

        # Team baseline
        inject_eligible = [
            (v["carry_over_rate"], _effective_n([_weight(r["age_days"]) for r in groups[t]]))
            for t, v in service_tags_out.items()
            if v.get("confidence") in ("high", "medium")
        ]

        if current_count >= _MIN_RECORDS_FOR_DERIVED_BASELINE and inject_eligible:
            total_eff_n = sum(en for _, en in inject_eligible)
            team_baseline = (
                sum(rate * en for rate, en in inject_eligible) / total_eff_n
                if total_eff_n > 0
                else _FALLBACK_BASELINE
            )
        else:
            team_baseline = _FALLBACK_BASELINE
            import logging
            logging.getLogger(__name__).warning(
                "Calibration: using fallback baseline %.2f (records=%d < %d)",
                _FALLBACK_BASELINE, current_count, _MIN_RECORDS_FOR_DERIVED_BASELINE,
            )

        signal_thresholds = existing_cal.get("signal_thresholds", _DEFAULT_THRESHOLDS.copy())

        result: dict = {
            "schema_version": _SCHEMA_VERSION,
            "generated_at": datetime.now(UTC).isoformat(),
            "record_count": current_count,
            "last_calibrated_record_count": current_count,
            "team_carry_over_baseline": round(team_baseline, 4),
            "excluded_groups": excluded_groups,
            "service_tags": service_tags_out,
            "signal_thresholds": signal_thresholds,
            "calibration_model": "haiku",
        }

        # Optional Haiku note synthesis (failures are non-fatal)
        inject_tags = {t: v for t, v in service_tags_out.items()
                       if v.get("confidence") in ("high", "medium")}
        if inject_tags:
            try:
                from claude_runner import run_claude
                from prompts_calibrate import build_calibrate_prompt

                prompt = build_calibrate_prompt(inject_tags)
                response = run_claude(prompt, model="haiku", timeout=30)
                if response:
                    try:
                        notes = json.loads(response)
                        if isinstance(notes, dict):
                            for tag, note in notes.items():
                                if tag in service_tags_out and isinstance(note, str):
                                    service_tags_out[tag]["note"] = note[:200]
                    except json.JSONDecodeError:
                        pass
            except Exception:
                pass  # Notes are optional — never fail calibration for this

        _write_atomic(calibration_path, result)
        return result
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()
        timer.cancel()
```

- [ ] **Step 7: Run tests to verify they pass**

```bash
python3 -m pytest tests/scripts/test_calibrate.py -v
```

Expected: all tests PASS (including the 3 new ones)

- [ ] **Step 8: Commit**

```bash
git add scripts/ai/calibrate.py tests/scripts/test_calibrate.py
git commit -m "feat(calibrate): add B8 hard timeout (60s) + B9 fcntl.flock for TOCTOU prevention

- _hard_timeout(): threading.Timer 60s → os._exit(1) prevents runaway LLM calls
- _LOCK_FILE: calibration.lock in DATA_DIR
- run_calibration(): LOCK_EX|LOCK_NB before self-gate read — second concurrent
  invocation exits immediately instead of racing to overwrite calibration.json
- lock_file param added for testability
- Tests: timeout timer behavior, flock blocks second invocation, timer cancel"
```

---

## Task 2: story_outcome_record.py — detached calibrate spawn

**Files:**

- Modify: `scripts/story_outcome_record.py`
- Create: `tests/scripts/test_story_outcome_record.py`

- [ ] **Step 1: Create `tests/scripts/test_story_outcome_record.py` with 3 failing tests**

```python
"""Tests for scripts/story_outcome_record.py — calibrate spawn behavior."""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import story_outcome_record  # type: ignore[import-untyped]

_ISSUE = {"key": "{{PROJECT_KEY}}-1", "summary": "auth fix", "status": "Done", "sp": 3,
          "assignee": None, "issuetype": "Story", "labels": ["be"]}


def _run_main(tmp_path, monkeypatch, issues=None):
    """Helper: patch env, run main() with given issues list."""
    monkeypatch.setattr(story_outcome_record, "DATA_DIR", tmp_path)
    monkeypatch.setattr(story_outcome_record, "STORY_OUTCOMES", tmp_path / "story-outcomes.jsonl")
    monkeypatch.setattr(
        sys, "argv",
        [
            "story_outcome_record.py",
            "--sprint-id", "1",
            "--sprint-name", "S1",
            "--issues-json", json.dumps(issues or [_ISSUE]),
        ],
    )
    story_outcome_record.main()


def test_spawns_calibrate_when_plugin_root_and_script_exist(tmp_path, monkeypatch):
    """Popen is called with calibrate.py path and start_new_session=True."""
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(tmp_path))
    monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
    calibrate_path = tmp_path / "scripts" / "ai" / "calibrate.py"
    calibrate_path.parent.mkdir(parents=True)
    calibrate_path.touch()

    with patch.object(story_outcome_record.subprocess, "Popen") as mock_popen:
        _run_main(tmp_path, monkeypatch)

    mock_popen.assert_called_once()
    args, kwargs = mock_popen.call_args
    assert str(calibrate_path) in args[0]
    assert kwargs["start_new_session"] is True
    assert kwargs["stdout"] == story_outcome_record.subprocess.DEVNULL


def test_does_not_spawn_when_plugin_root_unset(tmp_path, monkeypatch):
    """No Popen call when CLAUDE_PLUGIN_ROOT env var is not set."""
    monkeypatch.delenv("CLAUDE_PLUGIN_ROOT", raising=False)

    with patch.object(story_outcome_record.subprocess, "Popen") as mock_popen:
        _run_main(tmp_path, monkeypatch)

    mock_popen.assert_not_called()


def test_does_not_spawn_when_calibrate_missing(tmp_path, monkeypatch):
    """No Popen call when calibrate.py does not exist at expected path."""
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(tmp_path))
    # Do NOT create calibrate.py

    with patch.object(story_outcome_record.subprocess, "Popen") as mock_popen:
        _run_main(tmp_path, monkeypatch)

    mock_popen.assert_not_called()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python3 -m pytest tests/scripts/test_story_outcome_record.py -v
```

Expected: 3 FAILs — `AttributeError: module 'story_outcome_record' has no attribute 'subprocess'`

- [ ] **Step 3: Add `import subprocess` and `import sys` to `scripts/story_outcome_record.py`**

Replace the import block in `scripts/story_outcome_record.py` (lines 27–33):

```python
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
```

- [ ] **Step 4: Add calibrate spawn at the end of `main()` in `scripts/story_outcome_record.py`**

In `main()`, after the final `print(...)` call (currently the last statement before `if __name__ == "__main__":`), add:

```python
    # Trigger calibration in background (non-blocking, fire-and-forget)
    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
    if plugin_root:
        calibrate_path = Path(plugin_root) / "scripts" / "ai" / "calibrate.py"
        if calibrate_path.exists():
            log_path = Path(os.environ.get(
                "CLAUDE_PLUGIN_DATA",
                str(Path.home() / ".claude" / "plugins" / "data" / "atlassian-pm-atlassian-pm"),
            )) / "calibrate.log"
            subprocess.Popen(
                [sys.executable, str(calibrate_path)],
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=open(log_path, "a"),  # noqa: SIM115
            )
```

The complete `main()` function after the change (showing only the end to confirm placement):

```python
    prune_if_needed(STORY_OUTCOMES, MAX_RECORDS)

    completed = sum(1 for i in issues if is_completed(str(i.get("status") or "")))
    carry_over = written - completed
    print(
        f"Story outcomes recorded: {written} issues — "
        f"{completed} completed, {carry_over} carry-over → story-outcomes.jsonl"
    )

    # Trigger calibration in background (non-blocking, fire-and-forget)
    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
    if plugin_root:
        calibrate_path = Path(plugin_root) / "scripts" / "ai" / "calibrate.py"
        if calibrate_path.exists():
            log_path = Path(os.environ.get(
                "CLAUDE_PLUGIN_DATA",
                str(Path.home() / ".claude" / "plugins" / "data" / "atlassian-pm-atlassian-pm"),
            )) / "calibrate.log"
            subprocess.Popen(
                [sys.executable, str(calibrate_path)],
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=open(log_path, "a"),  # noqa: SIM115
            )
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
python3 -m pytest tests/scripts/test_story_outcome_record.py -v
```

Expected: 3 PASSes

- [ ] **Step 6: Run full test suite to check no regressions**

```bash
python3 -m pytest tests/ -v --tb=short 2>&1 | tail -20
```

Expected: all previously passing tests still pass

- [ ] **Step 7: Commit**

```bash
git add scripts/story_outcome_record.py tests/scripts/test_story_outcome_record.py
git commit -m "feat(story_outcome_record): spawn calibrate.py detached after writing outcomes

Triggers calibration automatically on every story_outcome_record.py call —
catches manual runs outside the close-sprint flow without a PostToolUse hook.

- subprocess.Popen with start_new_session=True (detached, non-blocking)
- stderr → calibrate.log for debuggability (not DEVNULL)
- Guarded by CLAUDE_PLUGIN_ROOT presence and calibrate.py existence
- Tests: spawn when ready, no-op when env unset, no-op when script missing"
```

---

## Task 3: close-sprint SKILL.md — Phase 8 detached nohup spawn

**Files:**

- Modify: `skills/sprint/close-sprint/SKILL.md`

- [ ] **Step 1: Add nohup calibrate spawn after the story_outcome_record.py block**

In `skills/sprint/close-sprint/SKILL.md`, find this block (around line 140–149):

```
> Then record per-story outcomes:
>
> ```bash
> python scripts/story_outcome_record.py \
>   --sprint-id SPRINT_ID \
>   --sprint-name "SPRINT_NAME" \
>   --issues-json 'JSON_ARRAY'
> ```
>
> Build `JSON_ARRAY` from Phase 1 `issue_list`: `key`, `summary`, `status`, `sp` (customfield\_10016), `assignee` (displayName), `issuetype` (name), `labels`. Include all sprint issues (done and incomplete).
```

Replace it with:

```
> Then record per-story outcomes:
>
> ```bash
> python scripts/story_outcome_record.py \
>   --sprint-id SPRINT_ID \
>   --sprint-name "SPRINT_NAME" \
>   --issues-json 'JSON_ARRAY'
> ```
>
> Build `JSON_ARRAY` from Phase 1 `issue_list`: `key`, `summary`, `status`, `sp` (customfield\_10016), `assignee` (displayName), `issuetype` (name), `labels`. Include all sprint issues (done and incomplete).
>
> Then spawn calibration update in the background (non-blocking):
>
> ```bash
> nohup uv run scripts/ai/calibrate.py > /dev/null 2>> ~/.claude/plugins/data/atlassian-pm-atlassian-pm/calibrate.log &
> ```
>
> Print `[calibration scheduled in background]` and continue immediately — do NOT wait for it to finish.
>
> If calibrate skips (< 10 new records or < 7 days since last run), it exits on its own — not a blocker.
```

- [ ] **Step 2: Verify the change looks correct**

```bash
grep -n "calibrat\|nohup\|background" skills/sprint/close-sprint/SKILL.md
```

Expected output should include lines containing `nohup uv run scripts/ai/calibrate.py` and `calibration scheduled in background`.

- [ ] **Step 3: Commit**

```bash
git add skills/sprint/close-sprint/SKILL.md
git commit -m "feat(close-sprint): spawn calibrate.py detached after story outcomes (Phase 8)

nohup uv run ... & — non-blocking, user never waits for LLM call.
Print [calibration scheduled in background] and continue.
Errors go to calibrate.log, never surface to user or block sprint close."
```

---

## Task 4: `scripts/setup_monitor.sh` — launchd daemon installer

**Files:**

- Create: `scripts/setup_monitor.sh`

- [ ] **Step 1: Create `scripts/setup_monitor.sh`**

```bash
#!/usr/bin/env bash
# setup_monitor.sh — install board_monitor.py as a macOS launchd daemon
#
# Usage: CLAUDE_PLUGIN_ROOT=... CLAUDE_PROJECT_DIR=... bash scripts/setup_monitor.sh
#
# Idempotent: safe to run multiple times. Uses launchctl bootstrap/bootout (not
# deprecated load/unload). All plist values are substituted at generation time —
# no ${VARIABLE} literals appear in the written XML file.

set -euo pipefail

PLIST_PATH="$HOME/Library/LaunchAgents/com.atlassian-pm.monitor.plist"
LABEL="com.atlassian-pm.monitor"

# ── Validate prerequisites ────────────────────────────────────────────────────

if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ]; then
  echo "ERROR: CLAUDE_PLUGIN_ROOT is not set" >&2
  exit 1
fi
if [ -z "${CLAUDE_PROJECT_DIR:-}" ]; then
  echo "ERROR: CLAUDE_PROJECT_DIR is not set" >&2
  exit 1
fi

PYTHON=$(command -v python3 2>/dev/null) || {
  echo "ERROR: python3 not found on PATH" >&2
  exit 1
}

# ── Prepare directories ───────────────────────────────────────────────────────

LOG_DIR="${CLAUDE_PLUGIN_ROOT}/monitor/logs"
mkdir -p "$LOG_DIR"
mkdir -p "$HOME/Library/LaunchAgents"

# ── Generate plist (values substituted by bash, no ${} in final file) ─────────

# Capture values now — heredoc expands bash variables
_PLUGIN_ROOT="$CLAUDE_PLUGIN_ROOT"
_PROJECT_DIR="$CLAUDE_PROJECT_DIR"
_PYTHON="$PYTHON"
_LOG_DIR="$LOG_DIR"

cat > "$PLIST_PATH" << PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>${_PYTHON}</string>
    <string>${_PLUGIN_ROOT}/monitor/board_monitor.py</string>
    <string>--project-dir</string>
    <string>${_PROJECT_DIR}</string>
  </array>
  <key>WorkingDirectory</key>
  <string>${_PLUGIN_ROOT}/monitor</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <dict>
    <key>SuccessfulExit</key>
    <false/>
  </dict>
  <key>ThrottleInterval</key>
  <integer>60</integer>
  <key>StandardOutPath</key>
  <string>${_LOG_DIR}/monitor.stdout.log</string>
  <key>StandardErrorPath</key>
  <string>${_LOG_DIR}/monitor.stderr.log</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>CLAUDE_PLUGIN_ROOT</key>
    <string>${_PLUGIN_ROOT}</string>
    <key>CLAUDE_PROJECT_DIR</key>
    <string>${_PROJECT_DIR}</string>
  </dict>
</dict>
</plist>
PLIST_EOF

# ── Validate generated plist ──────────────────────────────────────────────────

if ! plutil -lint "$PLIST_PATH"; then
  echo "ERROR: Generated plist failed validation (plutil -lint)" >&2
  exit 1
fi

# ── Load daemon ───────────────────────────────────────────────────────────────

# Bootout existing service silently (in case this is a re-install)
launchctl bootout "gui/$(id -u)" "$PLIST_PATH" 2>/dev/null || true

# Bootstrap (load + register for auto-start on login)
if ! launchctl bootstrap "gui/$(id -u)" "$PLIST_PATH"; then
  echo "ERROR: launchctl bootstrap failed" >&2
  exit 1
fi

# ── Verify registration ───────────────────────────────────────────────────────

echo ""
echo "✓ board_monitor daemon installed"
if launchctl list "$LABEL" 2>/dev/null; then
  echo "  (registered with launchd — RunAtLoad will start it)"
fi
echo ""
echo "Logs: ${_LOG_DIR}/monitor.stdout.log"
echo "      ${_LOG_DIR}/monitor.stderr.log"
echo ""
echo "Status: launchctl list $LABEL"
echo "Uninstall: scripts/teardown_monitor.sh"
```

- [ ] **Step 2: Make executable and run shellcheck**

```bash
chmod +x scripts/setup_monitor.sh
shellcheck scripts/setup_monitor.sh
```

Expected: no errors. If shellcheck flags `open(log_path, "a")` — that's in a different task. Here, only shell warnings matter.

Common shellcheck fix: if it flags `SC2155` (declare and assign separately), split `_PYTHON=$(command -v python3)` into two lines — but we already handle that with the `||` pattern above.

- [ ] **Step 3: Commit**

```bash
git add scripts/setup_monitor.sh
git commit -m "feat(setup_monitor): install board_monitor.py as macOS launchd daemon

- launchctl bootstrap/bootout (not deprecated load/unload)
- KeepAlive: {SuccessfulExit: false} — only restart on crash, not clean exit
- All plist values substituted at generation time (no \${} in XML)
- plutil -lint validates plist before loading
- ThrottleInterval: 60s prevents rapid restart loops
- Idempotent: bootout existing service before bootstrapping"
```

---

## Task 5: `scripts/teardown_monitor.sh` — launchd daemon uninstaller

**Files:**

- Create: `scripts/teardown_monitor.sh`

- [ ] **Step 1: Create `scripts/teardown_monitor.sh`**

```bash
#!/usr/bin/env bash
# teardown_monitor.sh — fully uninstall the board_monitor launchd daemon
#
# Usage: bash scripts/teardown_monitor.sh
#
# Moves plist to Trash (recoverable) using the `trash` CLI per project convention.
# Never uses `rm`. Safe to run even if daemon is not currently loaded.

set -euo pipefail

PLIST_PATH="$HOME/Library/LaunchAgents/com.atlassian-pm.monitor.plist"
LABEL="com.atlassian-pm.monitor"

# Bootout (silent if not loaded)
launchctl bootout "gui/$(id -u)" "$PLIST_PATH" 2>/dev/null || true

# Remove plist (recoverable via Trash — never rm)
if [ -f "$PLIST_PATH" ]; then
  if command -v trash &>/dev/null; then
    trash "$PLIST_PATH"
    echo "✓ board_monitor daemon uninstalled"
    echo "  Plist moved to Trash: $PLIST_PATH"
  else
    echo "WARNING: 'trash' command not found — falling back to rm" >&2
    rm "$PLIST_PATH"
    echo "✓ board_monitor daemon uninstalled (plist deleted)"
  fi
else
  echo "  Plist not found — daemon may already be uninstalled: $PLIST_PATH"
fi

echo ""
echo "To reinstall: scripts/setup_monitor.sh"
```

- [ ] **Step 2: Make executable and run shellcheck**

```bash
chmod +x scripts/teardown_monitor.sh
shellcheck scripts/teardown_monitor.sh
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add scripts/teardown_monitor.sh
git commit -m "feat(teardown_monitor): uninstall board_monitor launchd daemon

- launchctl bootout (silent on miss)
- Uses trash CLI for recoverable deletion (project convention)
- Falls back to rm with warning if trash not available
- Safe to run even if daemon is not loaded"
```

---

## Task 6: Discoverability — doctor check + QUICKSTART.md

**Files:**

- Modify: `skills/setup/doctor/SKILL.md`
- Modify: `QUICKSTART.md`

- [ ] **Step 1: In `skills/setup/doctor/SKILL.md`, change `TOTAL=11` to `TOTAL=12`**

Find:
```
TOTAL=11
```
Replace with:
```
TOTAL=12
```

- [ ] **Step 2: Add Check 11 for board_monitor daemon before the `REQUIRED=` line**

In `skills/setup/doctor/SKILL.md`, find the block that ends with:
```bash
  SKIP=$((SKIP+1))
fi

REQUIRED=$((TOTAL - SKIP))
```

Replace with:
```bash
  SKIP=$((SKIP+1))
fi

# Check 11: board_monitor daemon (optional — proactive intelligence)
MONITOR_PLIST="$HOME/Library/LaunchAgents/com.atlassian-pm.monitor.plist"
if launchctl list com.atlassian-pm.monitor &>/dev/null; then
  echo "  ✓  board_monitor daemon running"
  PASS=$((PASS+1))
elif [ -f "$MONITOR_PLIST" ]; then
  echo "  !  board_monitor plist exists but daemon not loaded"
  echo "     → Run: launchctl bootstrap gui/$(id -u) $MONITOR_PLIST"
  WARN=$((WARN+1))
else
  echo "  -  board_monitor daemon not installed (optional — proactive intelligence)"
  if [ -n "${PLUGIN_ROOT:-}" ]; then
    echo "     → Install: $PLUGIN_ROOT/scripts/setup_monitor.sh"
  else
    echo "     → Install: scripts/setup_monitor.sh (set CLAUDE_PLUGIN_ROOT first)"
  fi
  SKIP=$((SKIP+1))
fi

REQUIRED=$((TOTAL - SKIP))
```

- [ ] **Step 3: Add monitor setup step to `QUICKSTART.md`**

In `QUICKSTART.md`, find the Install section (Claude Code CLI block):

```markdown
Setup configures: acli auth · mcp-atlassian MCP server · `~/.config/atlassian/.env` · git smudge/clean filters · atlassian-cache SQLite server

> Claude Code must be **restarted once** after setup to activate the MCP server.
```

Replace with:

```markdown
Setup configures: acli auth · mcp-atlassian MCP server · `~/.config/atlassian/.env` · git smudge/clean filters · atlassian-cache SQLite server

> Claude Code must be **restarted once** after setup to activate the MCP server.

### Optional: Board Monitor Daemon

Runs `board_monitor.py` in the background, auto-starts on login, and feeds proactive Jira insights into AI context:

```bash
# Install once — auto-starts on login
CLAUDE_PLUGIN_ROOT=<path-to-plugin> CLAUDE_PROJECT_DIR=<path-to-project> \
  scripts/setup_monitor.sh

# Uninstall
scripts/teardown_monitor.sh
```

`/atlassian-pm:doctor` reports daemon status — run it to confirm.
```

- [ ] **Step 4: Update expected check count in `QUICKSTART.md`**

Find:
```
# Expected: 9-10 checks passed
```
Replace with:
```
# Expected: 10-12 checks passed
```

- [ ] **Step 5: Run doctor SKILL.md bash block through shellcheck (inline)**

```bash
grep -A 200 '```bash' skills/setup/doctor/SKILL.md | head -200 | shellcheck - 2>&1 | head -20
```

Expected: warnings only (shellcheck can't resolve `$PLUGIN_ROOT` etc.) — no errors that would break execution.

- [ ] **Step 6: Commit**

```bash
git add skills/setup/doctor/SKILL.md QUICKSTART.md
git commit -m "feat(doctor): add check 11 for board_monitor daemon + QUICKSTART discoverability

- doctor: TOTAL 11→12, check 11 detects loaded/plist-exists/missing states
- QUICKSTART: Optional Board Monitor section with setup/teardown commands
- QUICKSTART: expected doctor output updated to 10-12 checks passed"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task |
|---|---|
| B1: launchctl bootstrap/bootout | Task 4 |
| B2: KeepAlive {SuccessfulExit: false} | Task 4 |
| B3: plist values substituted at generation time | Task 4 |
| B4: plutil -lint before load | Task 4 |
| B8: threading.Timer 60s hard kill | Task 1 |
| B9: fcntl.flock LOCK_EX\|LOCK_NB | Task 1 |
| Component 2: detached nohup uv run | Task 3 |
| Component 3: subprocess.Popen from story_outcome_record | Task 2 |
| teardown_monitor.sh | Task 5 |
| doctor check 11 | Task 6 |
| QUICKSTART discoverability | Task 6 |

All spec requirements covered. ✓
