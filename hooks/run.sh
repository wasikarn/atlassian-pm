#!/usr/bin/env bash
# Resilient hook runner — skips gracefully if script not found (e.g. stale CLAUDE_PLUGIN_ROOT after version bump)
SCRIPT="${CLAUDE_PLUGIN_ROOT}/${1}"
if [ -f "$SCRIPT" ]; then
    python3 "$SCRIPT"
else
    printf '{"ok": true}'
fi
