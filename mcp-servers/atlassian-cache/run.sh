#!/bin/bash
# run.sh — Locate uv and start the atlassian-cache MCP server.
#
# Called by .mcp.json via:
#   "command": "bash",
#   "args": ["${CLAUDE_PLUGIN_ROOT}/mcp-servers/atlassian-cache/run.sh"]
#
# UV_PROJECT_ENVIRONMENT is injected by .mcp.json so uv uses the
# pre-installed venv in ${CLAUDE_PLUGIN_DATA}/venv rather than
# creating a new one on every startup.

set -euo pipefail

# ── locate uv ─────────────────────────────────────────────────────────────────
# Check PATH first (covers system-wide and shell-profile installs).
# Fall back to common per-user locations that are not always in MCP PATH.
UV_CMD=""
if command -v uv &>/dev/null; then
  UV_CMD="uv"
else
  for candidate in \
    "$HOME/.local/bin/uv" \
    "$HOME/.cargo/bin/uv" \
    "/opt/homebrew/bin/uv" \
    "/usr/local/bin/uv"; do
    if [ -x "$candidate" ]; then
      UV_CMD="$candidate"
      break
    fi
  done
fi

if [ -z "$UV_CMD" ]; then
  printf 'atlassian-cache: uv not found.\n' >&2
  printf 'Install uv: https://docs.astral.sh/uv/getting-started/installation/\n' >&2
  exit 1
fi

# ── resolve script directory ──────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── start server ──────────────────────────────────────────────────────────────
PID_FILE="/tmp/atlassian-cache.pid"

# Write PID file and cleanup on exit
echo $$ > "$PID_FILE"
trap "rm -f '$PID_FILE'" EXIT

exec "$UV_CMD" run \
  --project "$SCRIPT_DIR" \
  "$SCRIPT_DIR/server.py"
