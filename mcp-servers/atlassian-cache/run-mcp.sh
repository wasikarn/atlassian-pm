#!/bin/bash
# run-mcp.sh — Self-discovering MCP launcher.
#
# Placed at stable data dir by setup.sh:
#   ~/.claude/plugins/data/atlassian-pm-atlassian-pm/run-mcp.sh
#
# Resolves the latest plugin version from cache, sets UV_PROJECT_ENVIRONMENT
# to the pre-installed venv, then delegates to run.sh in that version.
#
# .mcp.json references this via:
#   "command": "bash",
#   "args": ["${HOME}/.claude/plugins/data/atlassian-pm-atlassian-pm/run-mcp.sh"]

set -euo pipefail

DATA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PLUGIN_ROOT=$(find "$HOME/.claude/plugins/cache/atlassian-pm/atlassian-pm" \
  -maxdepth 1 -mindepth 1 -type d 2>/dev/null | sort -V | tail -1)

if [ -z "$PLUGIN_ROOT" ]; then
  printf 'atlassian-cache: plugin not found in cache.\n' >&2
  printf 'Install: /plugin install atlassian-pm@atlassian-pm\n' >&2
  exit 1
fi

export UV_PROJECT_ENVIRONMENT="$DATA_DIR/venv"
export PYTHONPATH="$PLUGIN_ROOT/scripts${PYTHONPATH:+:$PYTHONPATH}"

exec bash "$PLUGIN_ROOT/mcp-servers/atlassian-cache/run.sh"
