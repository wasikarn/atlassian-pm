# Intelligence Automation Design

**Goal:** Automate the 3 remaining manual steps of the intelligence pipeline: board_monitor daemon startup, calibration trigger at sprint close, and calibration trigger on any story_outcome_record.py call.

**Architecture:** Three independent components — a macOS launchd setup script, a close-sprint skill step, and a direct call from story_outcome_record.py — layered over the existing intelligence pipeline (calibrate.py → calibration.json; board_monitor.py → intelligence_analyzer.py → insights.json; start_intelligence_inject.py → agent prompts). The PostToolUse hook approach was evaluated and eliminated in favor of a direct internal call (see Component 3).

**Tech Stack:** bash (setup_monitor.sh, teardown_monitor.sh), macOS launchd (plist), Python 3.x stdlib (story_outcome_record.py spawn, calibrate.py locking/timeout), SKILL.md edit (close-sprint).

---

## Component 1: `scripts/setup_monitor.sh` — launchd daemon installer

**Purpose:** Install board_monitor.py as a macOS launchd daemon that autostarts on login and restarts on crash.

**File:** `scripts/setup_monitor.sh`

**Behavior:**

- Idempotent: safe to run multiple times (bootout existing service before bootstrapping)
- Reads `$CLAUDE_PLUGIN_ROOT` and `$CLAUDE_PROJECT_DIR` — exits with error if either is unset
- Detects Python interpreter at install time: `PYTHON=$(command -v python3)` — resolves the absolute path written into ProgramArguments. Re-run setup after changing Python environments.
- Generates `~/Library/LaunchAgents/com.atlassian-pm.monitor.plist` with all variable values substituted at generation time (bash heredoc or `envsubst`) — launchd does NOT expand `${}` syntax in plist string values, so no `${VARIABLE}` literals may appear in the written XML
- Runs `plutil -lint "$PLIST_PATH"` after generating the plist to validate XML structure before loading
- Calls `launchctl bootout gui/$(id -u) "$PLIST_PATH" 2>/dev/null; true` (silent on miss) then `launchctl bootstrap gui/$(id -u) "$PLIST_PATH"`
- Verifies registration after bootstrap: `launchctl list com.atlassian-pm.monitor` — note that "registered" ≠ "running"; RunAtLoad starts it, but a crash would stop it
- Prints confirmation with PID
- Creates logs directory automatically if missing

**Generated plist** (all `<substituted-*>` placeholders show values written by the script at generation time — no shell variables appear in the actual file):

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
    <string><substituted-python-absolute-path></string>
    <string><substituted-plugin-root>/monitor/board_monitor.py</string>
    <string>--project-dir</string>
    <string><substituted-project-dir></string>
  </array>
  <key>WorkingDirectory</key>
  <string><substituted-plugin-root>/monitor</string>
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
  <string><substituted-plugin-root>/monitor/logs/monitor.stdout.log</string>
  <key>StandardErrorPath</key>
  <string><substituted-plugin-root>/monitor/logs/monitor.stderr.log</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>CLAUDE_PLUGIN_ROOT</key>
    <string><substituted-plugin-root></string>
    <key>CLAUDE_PROJECT_DIR</key>
    <string><substituted-project-dir></string>
  </dict>
</dict>
</plist>
```

**KeepAlive semantics:** `SuccessfulExit: false` means launchd only restarts the process on non-zero exit (crash), not on clean exit(0). Consequently, `board_monitor.py`'s PID lockfile guard **must** call `sys.exit(0)` (not `sys.exit(1)`) when it detects another instance is already running — otherwise launchd treats it as a crash and triggers a restart storm.

**ThrottleInterval:** The 60-second throttle prevents rapid restart loops during transient failures (network down, config error, etc.).

**Error handling:**
- Missing env vars → print error + exit 1 (not silent)
- `python3` not found on PATH → print error + exit 1
- `plutil -lint` failure → print stderr + exit 1 (do not load a malformed plist)
- `launchctl bootstrap` failure → print stderr + exit 1
- Logs directory auto-created if missing

---

### Teardown: `scripts/teardown_monitor.sh`

**Purpose:** Fully uninstall the launchd daemon and remove the plist.

**Behavior:**

1. Runs `launchctl bootout gui/$(id -u) "$PLIST_PATH" 2>/dev/null; true` (silent if not loaded)
2. Removes the plist using `trash "$PLIST_PATH"` (project convention: `trash` for recoverable deletion — never `rm`)
3. Prints confirmation

---

### Discoverability

- **`/atlassian-pm:doctor`**: Add a check that detects whether `~/Library/LaunchAgents/com.atlassian-pm.monitor.plist` exists and the daemon is loaded (`launchctl list com.atlassian-pm.monitor`). Emit a setup hint if missing, pointing to `scripts/setup_monitor.sh`.
- **`QUICKSTART.md`**: Reference `scripts/setup_monitor.sh` under the first-time setup section so new users install the daemon as part of initial configuration.

---

## Component 2: close-sprint SKILL.md — Phase 8 calibration step

**Purpose:** Explicitly run calibrate.py at sprint close when story_outcome_record.py has just written fresh data. Spawned as a detached background process so it never blocks the interactive skill.

**File modified:** `skills/sprint/close-sprint/SKILL.md`

**Change:** Add after the `story_outcome_record.py` bash block in Phase 8:

```
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

**Behavior:**

- calibrate.py is spawned as a detached background process (`nohup … &`) so the user never waits 10–60s for an LLM call
- The skill prints `[calibration scheduled in background]` and proceeds immediately
- calibrate.py self-gating handles "not enough data yet" gracefully — it exits cleanly on its own
- Errors from calibrate.py are written to `calibrate.log`; they do NOT surface to the user and do NOT block sprint close
- Success → calibration summary is written to the log, not inline

**Implementation note — why detached spawn:**
`close-sprint` is an interactive user-facing skill. calibrate.py may take 10–60s due to LLM calls. Using `nohup uv run … &` detaches the child process from the shell session, preventing it from blocking or being killed when the skill session ends.

---

## calibrate.py — Required changes

**File modified:** `scripts/ai/calibrate.py`

### B8 — Internal timeout (60s hard kill)

Add a `threading.Timer` at the start of `run_calibration()` that calls `os._exit(1)` after 60 seconds. This prevents runaway LLM calls from holding file locks or accumulating as zombie processes when calibrate.py is fire-and-forget (no parent waiting on it).

```python
import threading, os

def _hard_timeout(seconds: int = 60) -> threading.Timer:
    """Kill the process if calibration takes too long."""
    def _kill():
        os._exit(1)
    t = threading.Timer(seconds, _kill)
    t.daemon = True
    t.start()
    return t  # caller can cancel on success
```

Call `_hard_timeout()` at the start of `run_calibration()` and cancel the timer on normal completion:

```python
def run_calibration(...):
    timer = _hard_timeout(60)
    try:
        # ... calibration logic ...
    finally:
        timer.cancel()
```

### B9 — fcntl.flock for TOCTOU prevention

Both Component 2 (skill step) and Component 3 (story_outcome_record.py direct call) can invoke calibrate.py within seconds of each other. Without a file lock, both processes pass the self-gate simultaneously and race to write `calibration.json`.

Add `fcntl.flock` before reading `calibration.json`:

```python
import fcntl

LOCK_FILE = DATA_DIR / "calibration.lock"

def run_calibration(...):
    timer = _hard_timeout(60)
    lock_fd = open(LOCK_FILE, "w")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        timer.cancel()
        return None  # another calibration is running — exit cleanly
    try:
        # ... rest of calibration logic ...
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()
        timer.cancel()
```

Using `LOCK_NB` (non-blocking) means if another calibrate.py holds the lock, this instance exits immediately rather than waiting — correct behavior for fire-and-forget invocations.

---

## Component 3: `scripts/story_outcome_record.py` — detached calibrate spawn

**Purpose:** Auto-trigger calibrate.py whenever story_outcome_record.py writes new records — catches manual runs outside the close-sprint flow, without the overhead and fragility of a PostToolUse hook.

**Files:**

- Modify: `scripts/story_outcome_record.py` — add detached calibrate spawn at end of `main()`
- ~~Create: `hooks/plugin/session/post_story_outcome_calibrate.py`~~ — ELIMINATED
- ~~Modify: `hooks/hooks.json`~~ — NO CHANGE NEEDED

**Implementation:**

At the end of `main()`, after writing records and pruning, add:

```python
import subprocess, os
from pathlib import Path

# After writing outcomes — trigger calibration in background (non-blocking)
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
            stderr=open(log_path, "a"),
        )
```

**Key design decisions:**

- `start_new_session=True` — detached, non-blocking; does not affect story_outcome_record.py's own exit
- `stderr=open(log_path, "a")` — calibrate.py failures are logged to `calibrate.log` (not DEVNULL) for debuggability
- Guarded by `if plugin_root:` and `if calibrate_path.exists():` — silent skip if plugin not loaded or path missing
- No hooks.json changes needed — Component 3 is entirely internal to story_outcome_record.py

**Why the PostToolUse hook was eliminated:**

- Hook fired on every Bash call with string matching — unnecessary overhead on every tool use
- Fragile command-string detection is a reliability and security concern
- Both Component 2 (close-sprint flow) and a hook firing at sprint close creates a TOCTOU race condition
- story_outcome_record.py and calibrate.py are internal implementation details of the same plugin — a direct call is the correct coupling level

**Dedup:** calibrate.py's `fcntl.flock` ensures only one calibration runs at a time even if story_outcome_record.py is called multiple times in quick succession. The self-gating logic (`< 10 new records` or `< 7 days`) prevents redundant work when Component 2 (close-sprint) also triggers calibration.

---

## File Map

| File | Action |
|------|--------|
| `scripts/setup_monitor.sh` | CREATE |
| `scripts/teardown_monitor.sh` | CREATE |
| `scripts/story_outcome_record.py` | MODIFY (add calibrate spawn at end of main()) |
| `scripts/ai/calibrate.py` | MODIFY (add B8 timeout + B9 fcntl.flock) |
| `skills/sprint/close-sprint/SKILL.md` | MODIFY (Phase 8 — detached nohup spawn) |
| ~~`hooks/plugin/session/post_story_outcome_calibrate.py`~~ | ~~CREATE~~ — ELIMINATED |
| ~~`hooks/hooks.json`~~ | ~~MODIFY~~ — NO CHANGE NEEDED |

## Testing

- `setup_monitor.sh`: manual verify — run script, check plist exists + `launchctl list | grep atlassian-pm`
- `teardown_monitor.sh`: manual verify — run script, confirm service unloaded + plist removed
- `story_outcome_record.py` spawn: unit test — mock subprocess.Popen, assert called with correct args when CLAUDE_PLUGIN_ROOT set; assert not called when unset or calibrate_path missing
- `calibrate.py` flock: unit test — two concurrent processes, assert only one proceeds
- `close-sprint SKILL.md`: no automated test — skill text change only
