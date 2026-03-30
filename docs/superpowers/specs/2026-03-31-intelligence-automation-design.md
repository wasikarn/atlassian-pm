# Intelligence Automation Design

**Goal:** Automate the 3 remaining manual steps of the intelligence pipeline: board_monitor daemon startup, calibration trigger at sprint close, and calibration trigger on any story_outcome_record.py call.

**Architecture:** Three independent components — a macOS launchd setup script, a close-sprint skill step, and a PostToolUse hook — layered over the existing intelligence pipeline (calibrate.py → calibration.json; board_monitor.py → intelligence_analyzer.py → insights.json; start_intelligence_inject.py → agent prompts).

**Tech Stack:** bash (setup_monitor.sh), macOS launchd (plist), Python 3.x stdlib (hook script), SKILL.md edit (close-sprint).

---

## Component 1: `scripts/setup_monitor.sh` — launchd daemon installer

**Purpose:** Install board_monitor.py as a macOS launchd daemon that autostarts on login and restarts on crash.

**File:** `scripts/setup_monitor.sh`

**Behavior:**
- Idempotent: safe to run multiple times (unload existing plist before reloading)
- Reads `$CLAUDE_PLUGIN_ROOT` and `$CLAUDE_PROJECT_DIR` — exits with error if either is unset
- Generates `~/Library/LaunchAgents/com.atlassian-pm.monitor.plist` with absolute paths substituted
- Calls `launchctl unload` (silent on miss) then `launchctl load`
- Prints confirmation with PID

**Generated plist:**

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
    <string>/usr/bin/python3</string>
    <string>${CLAUDE_PLUGIN_ROOT}/monitor/board_monitor.py</string>
    <string>--project-dir</string>
    <string>${CLAUDE_PROJECT_DIR}</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>${CLAUDE_PLUGIN_ROOT}/monitor/logs/monitor.stdout.log</string>
  <key>StandardErrorPath</key>
  <string>${CLAUDE_PLUGIN_ROOT}/monitor/logs/monitor.stderr.log</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>CLAUDE_PLUGIN_ROOT</key>
    <string>${CLAUDE_PLUGIN_ROOT}</string>
    <key>CLAUDE_PROJECT_DIR</key>
    <string>${CLAUDE_PROJECT_DIR}</string>
  </dict>
</dict>
</plist>
```

**Error handling:**
- Missing env vars → print error + exit 1 (not silent)
- `launchctl load` failure → print stderr + exit 1
- Logs directory auto-created if missing

**Uninstall:** `launchctl unload ~/Library/LaunchAgents/com.atlassian-pm.monitor.plist && rm ~/Library/LaunchAgents/com.atlassian-pm.monitor.plist`

---

## Component 2: close-sprint SKILL.md — Phase 8 calibration step

**Purpose:** Explicitly run calibrate.py at sprint close when story_outcome_record.py has just written fresh data.

**File modified:** `skills/sprint/close-sprint/SKILL.md`

**Change:** Add after the `story_outcome_record.py` bash block in Phase 8:

```
> Then run calibration update:
>
> ```bash
> python3 scripts/ai/calibrate.py
> ```
>
> If calibrate skips (< 10 new records or < 7 days since last run), continue — not a blocker.
```

**Behavior:**
- calibrate.py self-gating handles "not enough data yet" gracefully
- Error from calibrate.py → log warning, do NOT block sprint close
- Success → prints calibration summary inline

---

## Component 3: `hooks/plugin/session/post_story_outcome_calibrate.py` — PostToolUse hook

**Purpose:** Auto-trigger calibrate.py whenever story_outcome_record.py is called — catches manual runs outside the close-sprint flow.

**Files:**
- Create: `hooks/plugin/session/post_story_outcome_calibrate.py`
- Modify: `hooks/hooks.json` PostToolUse:Bash array

**Hook logic:**

```python
# 1. Read stdin JSON
data = json.loads(sys.stdin.read())
command = data.get("tool_input", {}).get("command", "")

# 2. Fast path — not our command
if "story_outcome_record" not in command:
    sys.exit(0)

# 3. Spawn calibrate.py detached (non-blocking)
plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
calibrate_path = Path(plugin_root) / "scripts" / "ai" / "calibrate.py"
subprocess.Popen(
    [sys.executable, str(calibrate_path)],
    start_new_session=True,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
sys.exit(0)
```

**Key design decisions:**
- `start_new_session=True` — detaches from Claude's process group, survives hook exit
- `stdout/stderr=DEVNULL` — calibrate output goes to its own log, not hook stdout
- Exit 0 immediately — never blocks agent
- No error if `calibrate_path` doesn't exist — silent skip (CLAUDE_PLUGIN_ROOT may be unset in some contexts)

**Dedup:** calibrate.py self-gating (`< 10 new records` or `< 7 days`) prevents double-run when both Component 2 and Component 3 fire at sprint close.

**hooks.json registration:**
```json
{
  "type": "command",
  "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/run.sh\" hooks/plugin/session/post_story_outcome_calibrate.py",
  "timeout": 5
}
```
Added to the PostToolUse `"Bash"` matcher hooks array.

---

## File Map

| File | Action |
|------|--------|
| `scripts/setup_monitor.sh` | CREATE |
| `hooks/plugin/session/post_story_outcome_calibrate.py` | CREATE |
| `skills/sprint/close-sprint/SKILL.md` | MODIFY (Phase 8) |
| `hooks/hooks.json` | MODIFY (PostToolUse:Bash) |

## Testing

- `setup_monitor.sh`: manual verify — run script, check plist exists + `launchctl list | grep atlassian-pm`
- `post_story_outcome_calibrate.py`: unit test with fake stdin JSON (command with/without story_outcome_record)
- `close-sprint SKILL.md`: no automated test — skill text change only
