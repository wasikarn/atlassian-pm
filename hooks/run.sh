#!/usr/bin/env bash
# Resilient hook runner with telemetry
SCRIPT="${CLAUDE_PLUGIN_ROOT}/${1}"
LOG_FILE="${CLAUDE_PLUGIN_DATA}/hooks_telemetry.log"

if [ -f "$SCRIPT" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] START: $1" >> "$LOG_FILE"

    # Use gtimeout (GNU coreutils) on macOS, timeout on Linux
    TIMEOUT_CMD="timeout"
    if ! command -v timeout &>/dev/null; then
        if command -v gtimeout &>/dev/null; then
            TIMEOUT_CMD="gtimeout"
        else
            TIMEOUT_CMD=""
        fi
    fi

    # ATLASSIAN_PM_INTERNAL=true enables parse_stdin() to work
    if [ -n "$TIMEOUT_CMD" ]; then
        ATLASSIAN_PM_INTERNAL=true $TIMEOUT_CMD 30s python3 "$SCRIPT" 2>> "$LOG_FILE"
    else
        ATLASSIAN_PM_INTERNAL=true python3 "$SCRIPT" 2>> "$LOG_FILE"
    fi
    EXIT_CODE=$?

    echo "[$(date '+%Y-%m-%d %H:%M:%S')] END: $1 | Exit: $EXIT_CODE" >> "$LOG_FILE"

    if [ $EXIT_CODE -eq 124 ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1 timed out after 30s" >> "$LOG_FILE"
    fi

    exit $EXIT_CODE
else
    exit 0
fi
