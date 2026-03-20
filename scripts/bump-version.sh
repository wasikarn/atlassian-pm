#!/usr/bin/env bash
# bump-version.sh — Bump plugin version across all files, tag, push, and create GitHub release.
#
# Usage:
#   ./scripts/bump-version.sh <version> [title]   # explicit: 1.2.0 "My Release"
#   ./scripts/bump-version.sh patch               # auto-increment patch: 1.1.0 → 1.1.1
#   ./scripts/bump-version.sh minor               # auto-increment minor: 1.1.0 → 1.2.0
#   ./scripts/bump-version.sh major               # auto-increment major: 1.1.0 → 2.0.0
#
# Title is auto-generated from commits since last tag if not provided.
#
# Steps:
#   1. Validate version + working tree clean
#   2. Update marketplace.json + README.md badge
#   3. Commit, tag v<new>, push --tags
#   4. Create GitHub release with auto-generated notes

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

# ── color helpers ─────────────────────────────────────────────────────────────

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info() { echo -e "${CYAN}→${NC} $*"; }
ok()   { echo -e "${GREEN}✓${NC} $*"; }
warn() { echo -e "${YELLOW}!${NC} $*"; }
die()  { echo -e "${RED}✗${NC} $*" >&2; exit 1; }

# ── helpers ───────────────────────────────────────────────────────────────────

current_version() {
  python3 -c "import json; print(json.load(open('.claude-plugin/marketplace.json'))['plugins'][0]['version'])" \
    || die "Could not read version from .claude-plugin/marketplace.json"
}

auto_bump() {
  local current="$1" bump_type="$2"
  python3 - "$current" "$bump_type" <<'PY'
import sys
parts = sys.argv[1].split('.')
major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
t = sys.argv[2]
if t == 'major':   print(f"{major+1}.0.0")
elif t == 'minor': print(f"{major}.{minor+1}.0")
elif t == 'patch': print(f"{major}.{minor}.{patch+1}")
PY
}

update_json_version() {
  local file="$1" version="$2"
  python3 - "$file" "$version" <<'PY'
import json, sys
path, version = sys.argv[1], sys.argv[2]
data = json.load(open(path))
if 'version' in data:
    data['version'] = version
if 'plugins' in data and data['plugins']:
    data['plugins'][0]['version'] = version
with open(path, 'w') as f:
    json.dump(data, f, indent=2)
    f.write('\n')
PY
}

# ── parse args ────────────────────────────────────────────────────────────────

ARG="${1:-}"
[[ -n "$ARG" ]] || die "Usage: $0 <version|patch|minor|major> [title]"

CURRENT=$(current_version)

case "$ARG" in
  patch|minor|major)
    NEW_VERSION=$(auto_bump "$CURRENT" "$ARG")
    ;;
  [0-9]*)
    [[ "$ARG" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] \
      || die "Invalid version '$ARG' — must be semver X.Y.Z"
    NEW_VERSION="$ARG"
    ;;
  *)
    die "Invalid argument '$ARG' — expected a version number or patch/minor/major"
    ;;
esac

[[ "$NEW_VERSION" != "$CURRENT" ]] || die "Already at version $CURRENT"

# ── working tree must be clean ────────────────────────────────────────────────

if ! git diff --quiet || ! git diff --cached --quiet; then
  die "Working tree has uncommitted changes — commit or stash first"
fi

# ── release title ─────────────────────────────────────────────────────────────

if [[ -n "${2:-}" ]]; then
  RELEASE_TITLE="$2"
else
  # Auto-generate from commits since last tag (first commit subject, title-cased)
  LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")
  if [[ -n "$LAST_TAG" ]]; then
    RELEASE_TITLE=$(git log "${LAST_TAG}..HEAD" --oneline --no-merges \
      | head -1 | sed 's/^[a-f0-9]* //' | sed 's/^[a-z]*: //' \
      | python3 -c "import sys; s=sys.stdin.read().strip(); print(s[0].upper()+s[1:] if s else 'Release')")
  else
    RELEASE_TITLE="Release"
  fi
fi

# ── preview ───────────────────────────────────────────────────────────────────

echo ""
echo -e "  ${CYAN}atlassian-pm${NC}  ${YELLOW}$CURRENT${NC} → ${GREEN}$NEW_VERSION${NC}"
echo -e "  ${CYAN}Title${NC}  $RELEASE_TITLE"
echo ""

# ── 1. update files ───────────────────────────────────────────────────────────

info "Updating .claude-plugin/marketplace.json..."
update_json_version ".claude-plugin/marketplace.json" "$NEW_VERSION"
ok "marketplace.json → $NEW_VERSION"

info "Updating README.md badge..."
sed -i '' "s/version-${CURRENT}-blue\.svg/version-${NEW_VERSION}-blue.svg/g" README.md
ok "README.md badge → $NEW_VERSION"

# ── 2. summary ────────────────────────────────────────────────────────────────

echo "────────────────────────────────────────────"
echo "  Files to commit:"
git diff --name-only | sed 's/^/    /'
echo ""
echo -e "  Tag   : ${GREEN}v${NEW_VERSION}${NC}"
echo -e "  Title : v${NEW_VERSION} — ${RELEASE_TITLE}"
echo "────────────────────────────────────────────"
echo ""

# ── 3. commit + tag + push ────────────────────────────────────────────────────

info "Committing..."
git add .claude-plugin/marketplace.json README.md
git commit -m "chore: bump version to $NEW_VERSION"
ok "Committed"

info "Tagging v$NEW_VERSION..."
git tag "v$NEW_VERSION"
ok "Tagged"

info "Pushing..."
git push origin main --tags
ok "Pushed"

# ── 4. GitHub release ─────────────────────────────────────────────────────────

REPO=$(gh repo view --json nameWithOwner --jq '.nameWithOwner')

info "Creating GitHub release v$NEW_VERSION..."
RELEASE_URL=$(gh release create "v$NEW_VERSION" \
  --repo "$REPO" \
  --title "v$NEW_VERSION — $RELEASE_TITLE" \
  --generate-notes)
ok "Release: $RELEASE_URL"

# ── 5. update plugin + copy config ───────────────────────────────────────────

info "Refreshing marketplace cache..."
claude plugin marketplace update atlassian-pm 2>&1 | grep -E "✔|✘|Error" || true
ok "Marketplace refreshed"

info "Updating plugin..."
claude plugin update atlassian-pm@atlassian-pm 2>&1 | grep -E "✔|✘|already" || true

PLUGIN_CACHE="$HOME/.claude/plugins/cache/atlassian-pm/atlassian-pm/$NEW_VERSION"
if [[ -d "$PLUGIN_CACHE" ]]; then
  info "Copying config to plugin cache..."
  for f in project-config.json project-config-team-detail.json; do
    if [[ -f "$REPO_ROOT/.claude/$f" ]]; then
      cp "$REPO_ROOT/.claude/$f" "$PLUGIN_CACHE/.claude/$f"
      ok "Copied $f"
    fi
  done
else
  warn "Plugin cache not found at $PLUGIN_CACHE — copy config manually after restart"
fi

# Backup config for future reinstall recovery (read by setup skill Phase 0)
if [[ -f "$REPO_ROOT/.claude/project-config.json" ]]; then
  mkdir -p "$HOME/.config/atlassian"
  cp "$REPO_ROOT/.claude/project-config.json" "$HOME/.config/atlassian/project-config.json"
  ok "Backed up project-config.json to ~/.config/atlassian/"
fi

# ── done ──────────────────────────────────────────────────────────────────────

echo ""
echo -e "${GREEN}✅ $CURRENT → v$NEW_VERSION complete${NC}"
echo ""
echo "  Next: Restart Claude Code, then /atlassian-pm:doctor to verify"
