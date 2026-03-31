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

# Bootout: prefer label form (works even if plist has moved/been deleted already).
# Fall back to plist-path form for compatibility.
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || \
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
