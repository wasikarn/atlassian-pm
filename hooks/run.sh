#!/usr/bin/env bash
# Resilient hook runner with telemetry
SCRIPT="${CLAUDE_PLUGIN_ROOT}/${1}"
LOG_FILE="${CLAUDE_PLUGIN_DATA}/hooks_telemetry.log"

if [ -f "$SCRIPT" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] START: $1" >> "$LOG_FILE"

    # ATLASSIAN_PM_INTERNAL=true enables parse_stdin() to work
    ATLASSIAN_PM_INTERNAL=true timeout 30s python3 "$SCRIPT" 2>> "$LOG_FILE"
    EXIT_CODE=$?

    echo "[$(date '+%Y-%m-%d %H:%M:%S')] END: $1 | Exit: $EXIT_CODE" >> "$LOG_FILE"

    if [ $EXIT_CODE -eq 124 ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1 timed out after 30s" >> "$LOG_FILE"
    fi

    exit $EXIT_CODE
else
    exit 0
fi
