# Claude -p Autonomous Monitor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Prerequisite:** Phase 1 complete — `scripts/ai/claude_runner.py` must exist (created in Phase 3, or create standalone copy).

**Goal:** Background process that polls Jira every 5 min, detects board changes, and autonomously acts: analyze changed issues, alert on sprint health, sync PR merges to Jira.

**Architecture:** `monitor/` directory at project root. `board_monitor.py` is the main loop. Each handler is a module called with a change event dict. All Jira writes use `scripts/lib/jira_api.py` (already exists). `claude -p` is called per-event for analysis. State persisted in `monitor-state.json`. Runs as `launchd` background service on macOS.

**Tech Stack:** Python stdlib + `scripts/lib/jira_api.py` + `scripts/lib/auth.py` + `claude -p` via subprocess. No new dependencies.

---

## File Map

| Action | File | Responsibility |
|---|---|---|
| Create | `monitor/__init__.py` | Package marker |
| Create | `monitor/state.py` | Load/save monitor-state.json snapshot diff |
| Create | `monitor/runner.py` | `claude -p` wrapper for monitor (same guard) |
| Create | `monitor/handlers/__init__.py` | Package marker |
| Create | `monitor/handlers/issue_changed.py` | c1: analyze field changes → Jira comment |
| Create | `monitor/handlers/sprint_health.py` | c2: WIP/date alerts → iMessage |
| Create | `monitor/handlers/pr_sync.py` | c3/c4: PR events → Jira transition |
| Create | `monitor/board_monitor.py` | Main poll loop, dispatch to handlers |
| Create | `monitor/run.sh` | Entry point for launchd |
| Create | `monitor/com.atlassian-pm.monitor.plist` | launchd service definition |
| Create | `monitor/tests/test_monitor.py` | Unit tests (API + claude mocked) |
| Create | `monitor/logs/.gitkeep` | Ensure logs dir tracked (logs themselves gitignored) |

---

### Task 1: State management

**Files:**

- Create: `monitor/__init__.py`
- Create: `monitor/state.py`
- Create: `monitor/tests/test_monitor.py` (start with state tests)

- [ ] **Step 1: Write failing state tests**

Create `monitor/tests/__init__.py` (empty) and `monitor/tests/test_monitor.py`:

```python
#!/usr/bin/env python3
"""Tests for monitor/*.py"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from state import MonitorState, diff_snapshots


class TestMonitorState(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.state_path = Path(self.tmp.name)

    def tearDown(self):
        self.state_path.unlink(missing_ok=True)

    def test_saves_and_loads_snapshot(self):
        ms = MonitorState(self.state_path)
        ms.save_snapshot({"{{PROJECT_KEY}}-1": {"status": "In Progress", "assignee": "alice"}})
        loaded = ms.load_snapshot()
        self.assertEqual(loaded["{{PROJECT_KEY}}-1"]["status"], "In Progress")

    def test_returns_empty_dict_if_no_file(self):
        path = Path("/tmp/nonexistent_monitor_state_xyz.json")
        ms = MonitorState(path)
        self.assertEqual(ms.load_snapshot(), {})

    def test_diff_detects_status_change(self):
        old = {"{{PROJECT_KEY}}-1": {"status": "To Do", "summary": "Feature X"}}
        new = {"{{PROJECT_KEY}}-1": {"status": "In Progress", "summary": "Feature X"}}
        changes = diff_snapshots(old, new)
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]["key"], "{{PROJECT_KEY}}-1")
        self.assertIn("status", changes[0]["changed_fields"])

    def test_diff_detects_new_issue(self):
        old = {}
        new = {"{{PROJECT_KEY}}-2": {"status": "To Do", "summary": "New issue"}}
        changes = diff_snapshots(old, new)
        self.assertEqual(len(changes), 1)
        self.assertTrue(changes[0]["is_new"])

    def test_diff_ignores_unchanged(self):
        snapshot = {"{{PROJECT_KEY}}-1": {"status": "Done", "summary": "Done issue"}}
        changes = diff_snapshots(snapshot, snapshot)
        self.assertEqual(changes, [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify fail**

```bash
python3 -m pytest monitor/tests/test_monitor.py -v 2>&1 | head -10
```

Expected: `ModuleNotFoundError: No module named 'state'`

- [ ] **Step 3: Implement `monitor/state.py`**

Create `monitor/__init__.py` (empty) and `monitor/state.py`:

```python
#!/usr/bin/env python3
"""Monitor state: snapshot persistence and diff detection."""

import json
from pathlib import Path
from typing import Any


class MonitorState:
    """Persist Jira board snapshot between poll cycles."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def save_snapshot(self, snapshot: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2))

    def load_snapshot(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text())
        except (json.JSONDecodeError, OSError):
            return {}


def diff_snapshots(
    old: dict[str, Any],
    new: dict[str, Any],
    tracked_fields: tuple[str, ...] = ("status", "assignee", "priority", "summary"),
) -> list[dict[str, Any]]:
    """Return list of change events between two board snapshots.

    Each change: {"key": "TP-X", "is_new": bool, "changed_fields": {"field": (old, new)}, "issue": new_data}
    """
    changes = []
    for key, new_issue in new.items():
        if key not in old:
            changes.append({"key": key, "is_new": True, "changed_fields": {}, "issue": new_issue})
            continue
        old_issue = old[key]
        changed = {}
        for field in tracked_fields:
            old_val = old_issue.get(field)
            new_val = new_issue.get(field)
            if old_val != new_val:
                changed[field] = (old_val, new_val)
        if changed:
            changes.append({"key": key, "is_new": False, "changed_fields": changed, "issue": new_issue})
    return changes
```

- [ ] **Step 4: Run state tests**

```bash
python3 -m pytest monitor/tests/test_monitor.py::TestMonitorState -v
```

Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add monitor/__init__.py monitor/state.py monitor/tests/__init__.py monitor/tests/test_monitor.py
git commit -m "feat(monitor): add MonitorState + diff_snapshots (Phase 4 foundation)"
```

---

### Task 2: Implement `runner.py` and handlers

**Files:**

- Create: `monitor/runner.py`
- Create: `monitor/handlers/__init__.py`
- Create: `monitor/handlers/issue_changed.py`
- Create: `monitor/handlers/sprint_health.py`
- Create: `monitor/handlers/pr_sync.py`

- [ ] **Step 1: Create `monitor/runner.py`**

```python
#!/usr/bin/env python3
"""claude -p wrapper for monitor — identical guard to scripts/ai/claude_runner.py."""

import json
import os
import subprocess
from typing import Optional

RECURSION_GUARD = "ATLASSIAN_PM_HOOK_DEPTH"
_TIMEOUT = 20


def run_claude(prompt: str, timeout: int = _TIMEOUT) -> Optional[str]:
    if os.environ.get(RECURSION_GUARD):
        return None
    env = {**os.environ, RECURSION_GUARD: "1"}
    try:
        proc = subprocess.run(
            ["claude", "-p", prompt, "--output-format", "json"],
            env=env, capture_output=True, text=True, timeout=timeout,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None
    if data.get("is_error"):
        return None
    return data.get("result") or None
```

- [ ] **Step 2: Create `monitor/handlers/__init__.py`** (empty file)

- [ ] **Step 3: Implement `issue_changed.py`**

Create `monitor/handlers/issue_changed.py`:

```python
#!/usr/bin/env python3
"""Handler: analyze field changes and post Jira comment."""

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))

from monitor.runner import run_claude

_ANALYZE_PROMPT = """\
A Jira issue changed. Briefly analyze the impact (2-3 sentences max).

Issue: {key} — {summary}
Changes: {changes}
Current status: {status}

Is this change significant? If yes, what should the team know?
If trivial (e.g. assignee shuffle, minor wording), respond: SKIP
Otherwise respond with a brief impact note starting with: NOTE:"""


def handle(change: dict[str, Any], jira_api: Any) -> bool:
    """Analyze change and post comment if significant. Returns True if comment posted."""
    key = change["key"]
    issue = change["issue"]
    summary = issue.get("summary", "")
    status = issue.get("status", "")
    changed_fields = change.get("changed_fields", {})

    if not changed_fields:
        return False

    changes_text = ", ".join(
        f"{field}: {old!r} → {new!r}"
        for field, (old, new) in changed_fields.items()
    )

    prompt = _ANALYZE_PROMPT.format(
        key=key, summary=summary[:100],
        changes=changes_text, status=status,
    )

    result = run_claude(prompt, timeout=15)
    if not result or result.strip().startswith("SKIP"):
        return False

    comment = f"🤖 Monitor: {result.strip()}"
    try:
        jira_api.add_comment(key, comment)
        return True
    except Exception:
        return False
```

- [ ] **Step 4: Implement `sprint_health.py`**

Create `monitor/handlers/sprint_health.py`:

```python
#!/usr/bin/env python3
"""Handler: check WIP limits and sprint end date, send iMessage alert."""

import json
import subprocess
from datetime import date, datetime
from typing import Any


def _send_imessage(message: str) -> None:
    """Send alert via iMessage using osascript."""
    # Reads target from ATLASSIAN_PM_ALERT_NUMBER env var
    import os
    number = os.environ.get("ATLASSIAN_PM_ALERT_NUMBER", "")
    if not number:
        return
    script = f'tell application "Messages" to send "{message}" to buddy "{number}"'
    try:
        subprocess.run(["osascript", "-e", script], timeout=5, check=False)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass


def handle(board_config: dict[str, Any], issues: list[dict[str, Any]]) -> list[str]:
    """Check WIP limits and sprint end. Return list of alert messages sent."""
    alerts = []
    columns = board_config.get("columns", {})

    # WIP check per column
    for col_name, col_config in columns.items():
        wip_max = col_config.get("wip_max")
        if wip_max is None:
            continue
        statuses = col_config.get("statuses", [])
        count = sum(1 for i in issues if i.get("status") in statuses)
        if count > wip_max:
            msg = f"⚠️ WIP LIMIT: {col_name} has {count}/{wip_max} issues. Consider pulling from In Progress."
            _send_imessage(msg)
            alerts.append(msg)

    # Sprint end check (if sprint end date available)
    for issue in issues:
        sprint_end = issue.get("sprint_end_date")
        if not sprint_end:
            continue
        try:
            end = datetime.fromisoformat(sprint_end).date()
            days_left = (end - date.today()).days
            if 0 <= days_left <= 2:
                msg = f"⏰ SPRINT ENDS in {days_left} day(s) ({end}). Check remaining backlog."
                _send_imessage(msg)
                alerts.append(msg)
                break  # Alert once per cycle
        except ValueError:
            continue

    return alerts
```

- [ ] **Step 5: Implement `pr_sync.py`**

Create `monitor/handlers/pr_sync.py`:

```python
#!/usr/bin/env python3
"""Handler: detect PR merge events and sync Jira status.

Watches hooks-logs/*.jsonl for post_pr_sync events written by the
existing hooks/dev/post_pr_sync.py hook. When a merge is detected,
transitions the linked Jira issue to Done and adds a PR link comment.
"""

import json
import os
import re
from pathlib import Path
from typing import Any

_HOOKS_LOG_DIR = Path(os.environ.get("CLAUDE_PLUGIN_DATA",
                                      Path.home() / ".claude")) / "hooks-logs"
_ISSUE_KEY_RE = re.compile(r"\b([A-Z]+-\d+)\b")
_PROCESSED_FILE = Path(os.environ.get("CLAUDE_PLUGIN_DATA",
                                       Path.home() / ".claude")) / "monitor-pr-processed.json"


def _load_processed() -> set[str]:
    if not _PROCESSED_FILE.exists():
        return set()
    try:
        return set(json.loads(_PROCESSED_FILE.read_text()))
    except (json.JSONDecodeError, OSError):
        return set()


def _save_processed(processed: set[str]) -> None:
    _PROCESSED_FILE.write_text(json.dumps(sorted(processed)))


def _find_new_pr_events(processed: set[str]) -> list[dict[str, Any]]:
    """Scan today's hook log for unprocessed post_pr_sync events."""
    from datetime import date
    log_file = _HOOKS_LOG_DIR / f"{date.today().isoformat()}.jsonl"
    if not log_file.exists():
        return []

    events = []
    try:
        for line in log_file.read_text().splitlines():
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("hook") != "post-pr-sync":
                continue
            event_id = f"{entry.get('ts')}-{entry.get('pr_url', '')}"
            if event_id not in processed:
                events.append({**entry, "_event_id": event_id})
    except OSError:
        pass
    return events


def handle(jira_api: Any) -> list[str]:
    """Process new PR merge events. Return list of issue keys synced."""
    processed = _load_processed()
    events = _find_new_pr_events(processed)
    synced = []

    for event in events:
        pr_url = event.get("pr_url", "")
        branch = event.get("branch", "")

        # Extract issue key from branch name or PR title
        keys = _ISSUE_KEY_RE.findall(branch) or _ISSUE_KEY_RE.findall(pr_url)
        if not keys:
            processed.add(event["_event_id"])
            continue

        issue_key = keys[0]
        try:
            # Add PR comment
            comment = f"PR merged: {pr_url}" if pr_url else f"PR merged from branch: {branch}"
            jira_api.add_comment(issue_key, f"🔗 {comment}")
            # Transition to Done (get available transitions first)
            transitions = jira_api.get_transitions(issue_key)
            done_id = next(
                (t["id"] for t in transitions if "done" in t["name"].lower()),
                None
            )
            if done_id:
                jira_api.transition_issue(issue_key, done_id)
            synced.append(issue_key)
        except Exception:
            pass

        processed.add(event["_event_id"])

    _save_processed(processed)
    return synced
```

- [ ] **Step 6: Commit all handlers**

```bash
git add monitor/runner.py monitor/handlers/__init__.py \
        monitor/handlers/issue_changed.py monitor/handlers/sprint_health.py \
        monitor/handlers/pr_sync.py
git commit -m "feat(monitor): add issue_changed, sprint_health, pr_sync handlers"
```

---

### Task 3: Implement `board_monitor.py` main loop

**Files:**

- Create: `monitor/board_monitor.py`

- [ ] **Step 1: Read `scripts/lib/jira_api.py` to understand API**

```bash
head -80 scripts/lib/jira_api.py
```

Note the `JiraAPI` class constructor and available methods (e.g., `search_issues`, `add_comment`, `get_transitions`, `transition_issue`).

- [ ] **Step 2: Implement `board_monitor.py`**

Create `monitor/board_monitor.py`:

```python
#!/usr/bin/env python3
"""Autonomous Jira board monitor.

Polls Jira every POLL_INTERVAL seconds. Detects changes, dispatches handlers.
Runs as a background process — independent of Claude Code session.

Usage:
    python3 monitor/board_monitor.py
    python3 monitor/board_monitor.py --interval 300 --dry-run
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

# Add scripts to path for jira_api reuse
_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "scripts"))
sys.path.insert(0, str(_ROOT))

from lib.auth import load_credentials
from lib.jira_api import JiraAPI, derive_jira_url
from monitor.state import MonitorState, diff_snapshots
from monitor.handlers import issue_changed, sprint_health, pr_sync

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [monitor] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr),
        logging.FileHandler(_ROOT / "monitor" / "logs" / "monitor.log"),
    ],
)
log = logging.getLogger(__name__)

_STATE_PATH = Path(os.environ.get("CLAUDE_PLUGIN_DATA",
                                   Path.home() / ".claude")) / "monitor-state.json"


def fetch_board_snapshot(jira: JiraAPI, project_key: str) -> dict:
    """Fetch all non-Done issues and return as key → fields dict."""
    try:
        issues = jira.search_issues(
            f'project = {project_key} AND statusCategory != Done',
            fields=["summary", "status", "assignee", "priority", "parent"],
            max_results=100,
        )
        return {
            i["key"]: {
                "summary": i["fields"].get("summary", ""),
                "status": i["fields"].get("status", {}).get("name", ""),
                "assignee": (i["fields"].get("assignee") or {}).get("displayName", ""),
                "priority": (i["fields"].get("priority") or {}).get("name", ""),
            }
            for i in issues
        }
    except Exception as e:
        log.error("Failed to fetch board snapshot: %s", e)
        return {}


def load_board_config() -> dict:
    """Load board column config from project-config.json."""
    config_path = _ROOT / ".claude" / "project-config.json"
    try:
        data = json.loads(config_path.read_text())
        return data.get("board", {})
    except (json.JSONDecodeError, OSError):
        return {}


def run_cycle(jira: JiraAPI, state: MonitorState, config: dict,
              project_key: str, dry_run: bool = False) -> None:
    """Single poll cycle: fetch → diff → dispatch handlers."""
    old_snapshot = state.load_snapshot()
    new_snapshot = fetch_board_snapshot(jira, project_key)

    if not new_snapshot:
        log.warning("Empty snapshot — skipping cycle")
        return

    changes = diff_snapshots(old_snapshot, new_snapshot)
    log.info("Cycle: %d issues, %d changes", len(new_snapshot), len(changes))

    if not dry_run:
        # c1: analyze changed issues
        for change in changes[:10]:  # limit per cycle to avoid rate limit
            if issue_changed.handle(change, jira):
                log.info("Commented on %s", change["key"])

        # c2: sprint health check
        board_config = config
        issues_list = [{"status": v["status"], "summary": v["summary"]}
                       for v in new_snapshot.values()]
        alerts = sprint_health.handle(board_config, issues_list)
        if alerts:
            log.info("Sent %d health alerts", len(alerts))

        # c3/c4: PR sync
        synced = pr_sync.handle(jira)
        if synced:
            log.info("Synced PRs for: %s", ", ".join(synced))

        state.save_snapshot(new_snapshot)
    else:
        log.info("[DRY RUN] %d changes detected, no writes", len(changes))
        for c in changes[:5]:
            log.info("  %s: %s", c["key"], list(c["changed_fields"].keys()))


def main() -> None:
    parser = argparse.ArgumentParser(description="Atlassian-pm autonomous board monitor")
    parser.add_argument("--interval", type=int, default=300, help="Poll interval in seconds")
    parser.add_argument("--dry-run", action="store_true", help="Detect changes but do not write")
    parser.add_argument("--once", action="store_true", help="Run one cycle and exit")
    args = parser.parse_args()

    # Load config
    config_path = _ROOT / ".claude" / "project-config.json"
    try:
        config = json.loads(config_path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        log.error("Cannot read project-config.json: %s", e)
        sys.exit(1)

    project_key = config["jira"]["project_key"]
    site = config["jira"]["site"]
    board_config = config.get("board", {})

    # Auth
    try:
        creds = load_credentials()
        jira = JiraAPI(derive_jira_url(site), creds)
    except Exception as e:
        log.error("Auth failed: %s", e)
        sys.exit(1)

    state = MonitorState(_STATE_PATH)
    (Path(__file__).parent / "logs").mkdir(exist_ok=True)

    log.info("Monitor started. Project: %s, interval: %ds, dry_run: %s",
             project_key, args.interval, args.dry_run)

    if args.once:
        run_cycle(jira, state, board_config, project_key, dry_run=args.dry_run)
        return

    while True:
        try:
            run_cycle(jira, state, board_config, project_key, dry_run=args.dry_run)
        except KeyboardInterrupt:
            log.info("Monitor stopped by user")
            break
        except Exception as e:
            log.error("Cycle error: %s", e)
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Create logs directory**

```bash
mkdir -p monitor/logs
touch monitor/logs/.gitkeep
echo "monitor/logs/*.log" >> .gitignore
```

- [ ] **Step 4: Smoke test with dry-run**

```bash
python3 monitor/board_monitor.py --once --dry-run
```

Expected: logs showing issue count and `[DRY RUN]` line with 0 changes (first run, no old snapshot).

- [ ] **Step 5: Commit main loop**

```bash
git add monitor/board_monitor.py monitor/logs/.gitkeep .gitignore
git commit -m "feat(monitor): add board_monitor.py main poll loop"
```

---

### Task 4: launchd service setup

**Files:**

- Create: `monitor/run.sh`
- Create: `monitor/com.atlassian-pm.monitor.plist`

- [ ] **Step 1: Create `monitor/run.sh`**

```bash
#!/usr/bin/env bash
# Entry point for launchd service
set -e

PLUGIN_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_FILE="${PLUGIN_ROOT}/monitor/logs/monitor.log"

cd "${PLUGIN_ROOT}"
exec python3 monitor/board_monitor.py \
  --interval 300 \
  >> "${LOG_FILE}" 2>&1
```

Make executable:

```bash
chmod +x monitor/run.sh
```

- [ ] **Step 2: Create launchd plist**

Create `monitor/com.atlassian-pm.monitor.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.atlassian-pm.monitor</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>PLUGIN_ROOT_PLACEHOLDER/monitor/run.sh</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <dict>
    <key>Crashed</key>
    <true/>
  </dict>
  <key>ThrottleInterval</key>
  <integer>60</integer>
  <key>StandardOutPath</key>
  <string>PLUGIN_ROOT_PLACEHOLDER/monitor/logs/launchd-stdout.log</string>
  <key>StandardErrorPath</key>
  <string>PLUGIN_ROOT_PLACEHOLDER/monitor/logs/launchd-stderr.log</string>
</dict>
</plist>
```

Note: `PLUGIN_ROOT_PLACEHOLDER` must be replaced with absolute path during install. See Step 3.

- [ ] **Step 3: Create install script**

Create `monitor/install.sh`:

```bash
#!/usr/bin/env bash
# Install monitor as launchd service
set -e

PLUGIN_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PLIST_SRC="${PLUGIN_ROOT}/monitor/com.atlassian-pm.monitor.plist"
PLIST_DST="${HOME}/Library/LaunchAgents/com.atlassian-pm.monitor.plist"

echo "Installing monitor service..."
echo "Plugin root: ${PLUGIN_ROOT}"

# Substitute placeholder with real path
sed "s|PLUGIN_ROOT_PLACEHOLDER|${PLUGIN_ROOT}|g" \
  "${PLIST_SRC}" > "${PLIST_DST}"

# Load service
launchctl unload "${PLIST_DST}" 2>/dev/null || true
launchctl load "${PLIST_DST}"

echo "Monitor service installed and started."
echo "Logs: ${PLUGIN_ROOT}/monitor/logs/"
echo "Stop: launchctl unload ${PLIST_DST}"
```

```bash
chmod +x monitor/install.sh
```

- [ ] **Step 4: Test install (dry run)**

```bash
# Test the plist substitution without loading
PLUGIN_ROOT="$(pwd)"
sed "s|PLUGIN_ROOT_PLACEHOLDER|${PLUGIN_ROOT}|g" monitor/com.atlassian-pm.monitor.plist | \
  plutil -lint -
```

Expected: `stdin: OK`

- [ ] **Step 5: Install and verify service**

```bash
bash monitor/install.sh
sleep 3
launchctl list | grep atlassian-pm
```

Expected: service appears in list with PID (not 0).

- [ ] **Step 6: Verify logs**

```bash
tail -20 monitor/logs/monitor.log
```

Expected: `Monitor started. Project: TP, interval: 300s`

- [ ] **Step 7: Commit**

```bash
git add monitor/run.sh monitor/com.atlassian-pm.monitor.plist monitor/install.sh
git commit -m "feat(monitor): add launchd service files + install script"
```

---

### Task 5: Set alert phone number (for sprint health alerts)

- [ ] **Step 1: Set alert number env var**

Add to your shell profile (`~/.zshrc` or `~/.bash_profile`):

```bash
export ATLASSIAN_PM_ALERT_NUMBER="+66XXXXXXXXX"  # your phone number
```

Reload:

```bash
source ~/.zshrc
```

- [ ] **Step 2: Test iMessage alert manually**

```bash
python3 -c "
import sys; sys.path.insert(0, 'monitor')
from handlers.sprint_health import _send_imessage
_send_imessage('🧪 Test alert from atlassian-pm monitor')
"
```

Expected: iMessage received on phone.

- [ ] **Step 3: Final end-to-end test**

```bash
# Run one cycle with real Jira data (no dry-run)
python3 monitor/board_monitor.py --once
```

Expected: `Cycle: N issues, M changes` in logs. No errors.

- [ ] **Step 4: Final commit**

```bash
git commit --allow-empty -m "chore: Phase 4 complete — autonomous monitor running"
```

---

## Phase 4 Complete

Monitor is live. Management commands:

```bash
# Stop
launchctl unload ~/Library/LaunchAgents/com.atlassian-pm.monitor.plist

# Restart
launchctl unload ~/Library/LaunchAgents/com.atlassian-pm.monitor.plist && bash monitor/install.sh

# Watch logs live
tail -f monitor/logs/monitor.log

# Test one cycle
python3 monitor/board_monitor.py --once --dry-run
```
