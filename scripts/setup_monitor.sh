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

# Capture values at install time (heredoc expands these bash variables).
# No ${VARIABLE} literals appear in the final XML — launchd does not expand them.
_PLUGIN_ROOT="$CLAUDE_PLUGIN_ROOT"
_PROJECT_DIR="$CLAUDE_PROJECT_DIR"
_PYTHON="$PYTHON"
_LOG_DIR="$LOG_DIR"
# Capture user PATH at install time so the daemon inherits Homebrew tools etc.
# launchd agents do not inherit shell PATH — provide it explicitly.
_USER_PATH="$PATH"

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
    <key>PATH</key>
    <string>${_USER_PATH}</string>
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
# || true: launchctl list returns exit 113 if service not yet settled — non-fatal
if launchctl list "$LABEL" 2>/dev/null || true; then
  echo "  (registered with launchd — RunAtLoad will start it)"
fi
echo ""
echo "Logs: ${_LOG_DIR}/monitor.stdout.log"
echo "      ${_LOG_DIR}/monitor.stderr.log"
echo ""
echo "Status: launchctl list $LABEL"
echo "Uninstall: scripts/teardown_monitor.sh"
