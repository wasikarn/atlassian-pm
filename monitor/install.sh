#!/usr/bin/env bash
set -e
PLUGIN_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PLIST_SRC="${PLUGIN_ROOT}/monitor/com.atlassian-pm.monitor.plist"
PLIST_DST="${HOME}/Library/LaunchAgents/com.atlassian-pm.monitor.plist"
echo "Installing monitor service..."
sed "s|PLUGIN_ROOT_PLACEHOLDER|${PLUGIN_ROOT}|g" "${PLIST_SRC}" > "${PLIST_DST}"
launchctl unload "${PLIST_DST}" 2>/dev/null || true
launchctl load "${PLIST_DST}"
echo "Monitor installed. Logs: ${PLUGIN_ROOT}/monitor/logs/"
