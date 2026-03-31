#!/usr/bin/env bash
# Install git hooks for local development
set -euo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOKS_SRC="$REPO_ROOT/scripts/git-hooks"
GIT_HOOKS_DIR="$REPO_ROOT/.git/hooks"
for hook in "$HOOKS_SRC"/*; do
  name=$(basename "$hook")
  cp "$hook" "$GIT_HOOKS_DIR/$name"
  chmod +x "$GIT_HOOKS_DIR/$name"
  echo "Installed: $name"
done
echo "✓ Git hooks installed."
