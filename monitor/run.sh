#!/usr/bin/env bash
set -e
PLUGIN_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "${PLUGIN_ROOT}"
exec python3 monitor/board_monitor.py --interval 300 >> "${PLUGIN_ROOT}/monitor/logs/monitor.log" 2>&1
