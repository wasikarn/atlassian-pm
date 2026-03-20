#!/usr/bin/env bash
# bump-version.sh — bump atlassian-pm version across all files, tag, push, release
#
# Usage:
#   ./scripts/bump-version.sh <new-version>
#   ./scripts/bump-version.sh 1.2.0
#
# Steps:
#   1. Validate semver + working tree clean
#   2. Update marketplace.json, README.md, CHANGELOG.md (template)
#   3. Open $EDITOR for changelog entry
#   4. Commit, tag v<new>, push
#   5. Create GitHub release from changelog entry
#   6. Refresh marketplace cache + update plugin

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

# ── validate args ─────────────────────────────────────────────────────────────

NEW_VERSION="${1:-}"
[[ -z "$NEW_VERSION" ]] && die "Usage: $0 <new-version>  (e.g. $0 1.2.0)"
[[ "$NEW_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] \
  || die "Invalid version '$NEW_VERSION' — must be semver X.Y.Z"

# ── working tree must be clean ────────────────────────────────────────────────

if ! git diff --quiet || ! git diff --cached --quiet; then
  die "Working tree has uncommitted changes — commit or stash first"
fi

# ── read current version ──────────────────────────────────────────────────────

MARKETPLACE_JSON=".claude-plugin/marketplace.json"
[[ -f "$MARKETPLACE_JSON" ]] || die "Not found: $MARKETPLACE_JSON"

OLD_VERSION=$(python3 -c "
import json
print(json.load(open('$MARKETPLACE_JSON'))['plugins'][0]['version'])
") || die "Could not read version from $MARKETPLACE_JSON"

[[ "$NEW_VERSION" == "$OLD_VERSION" ]] && die "Already at version $OLD_VERSION"

echo ""
echo -e "  ${CYAN}atlassian-pm${NC}  ${YELLOW}$OLD_VERSION${NC} → ${GREEN}$NEW_VERSION${NC}"
echo ""

# ── 1. marketplace.json ───────────────────────────────────────────────────────

info "Updating $MARKETPLACE_JSON..."
python3 - "$MARKETPLACE_JSON" "$NEW_VERSION" <<'PY'
import json, sys
path, version = sys.argv[1], sys.argv[2]
data = json.load(open(path))
data['plugins'][0]['version'] = version
with open(path, 'w') as f:
    json.dump(data, f, indent=2)
    f.write('\n')
PY
ok "marketplace.json → $NEW_VERSION"

# ── 2. README.md badge ────────────────────────────────────────────────────────

if [[ -f "README.md" ]]; then
  info "Updating README.md badge..."
  sed -i '' "s/version-${OLD_VERSION}-blue\.svg/version-${NEW_VERSION}-blue.svg/g" README.md
  ok "README.md badge → $NEW_VERSION"
else
  warn "README.md not found — skipping"
fi

# ── 3. CHANGELOG.md template ─────────────────────────────────────────────────

info "Inserting CHANGELOG template..."
TODAY=$(date +%Y-%m-%d)
python3 - "$NEW_VERSION" "$TODAY" <<'PY'
import sys

new_version, today = sys.argv[1], sys.argv[2]
template = f"""## [{new_version}] - {today}

### Added

-

### Changed

-

### Fixed

-

"""

with open('CHANGELOG.md', 'r') as f:
    content = f.read()

# Insert before first ## [ section
marker = '\n## ['
idx = content.find(marker)
if idx == -1:
    content += '\n' + template
else:
    content = content[:idx] + '\n' + template + content[idx + 1:]

with open('CHANGELOG.md', 'w') as f:
    f.write(content)
PY
ok "CHANGELOG.md → template inserted"

# ── 4. open editor ────────────────────────────────────────────────────────────

EDITOR="${EDITOR:-vi}"
echo ""
echo -e "${YELLOW}Fill in the release notes for $NEW_VERSION, then save and close.${NC}"
echo "  (empty '- ' bullets will be removed automatically)"
echo ""
read -r -p "Press Enter to open $EDITOR..." _
$EDITOR CHANGELOG.md

# clean up empty bullets and excess blank lines
python3 - <<'PY'
import re

with open('CHANGELOG.md', 'r') as f:
    content = f.read()

content = re.sub(r'^- \s*$', '', content, flags=re.MULTILINE)
content = re.sub(r'\n{3,}', '\n\n', content)

with open('CHANGELOG.md', 'w') as f:
    f.write(content)
PY
ok "CHANGELOG.md cleaned"

# ── 5. extract release notes ─────────────────────────────────────────────────

RELEASE_NOTES=$(python3 - "$NEW_VERSION" <<'PY'
import re, sys

new_version = sys.argv[1]
with open('CHANGELOG.md', 'r') as f:
    content = f.read()

pattern = rf'## \[{re.escape(new_version)}\][^\n]*\n(.*?)(?=\n## \[|\Z)'
m = re.search(pattern, content, re.DOTALL)
print(m.group(1).strip() if m else 'See CHANGELOG.md for details.')
PY
)

# ── 6. confirm ────────────────────────────────────────────────────────────────

echo ""
echo "────────────────────────────────────────────"
echo "  Files to commit:"
git diff --name-only | sed 's/^/    /'
echo ""
echo "  Release notes preview:"
echo "$RELEASE_NOTES" | head -20 | sed 's/^/    /'
[[ $(echo "$RELEASE_NOTES" | wc -l) -gt 20 ]] && echo "    ... (truncated)"
echo "────────────────────────────────────────────"
echo ""
read -r -p "Commit, tag v$NEW_VERSION, push, and create GitHub release? [y/N] " CONFIRM
[[ "$CONFIRM" =~ ^[Yy]$ ]] || { warn "Aborted — changes left unstaged"; exit 0; }

# ── 7. commit + tag + push ────────────────────────────────────────────────────

info "Committing..."
git add .claude-plugin/marketplace.json README.md CHANGELOG.md
git commit -m "chore: bump version to $NEW_VERSION"
ok "Committed"

info "Tagging v$NEW_VERSION..."
git tag "v$NEW_VERSION"
ok "Tagged"

info "Pushing..."
git push origin main --tags
ok "Pushed"

# ── 8. GitHub release ─────────────────────────────────────────────────────────

info "Creating GitHub release v$NEW_VERSION..."
RELEASE_URL=$(gh release create "v$NEW_VERSION" \
  --title "v$NEW_VERSION" \
  --notes "$RELEASE_NOTES")
ok "Release: $RELEASE_URL"

# ── done ─────────────────────────────────────────────────────────────────────

echo ""
echo -e "${GREEN}✅ $OLD_VERSION → v$NEW_VERSION complete${NC}"
echo ""
echo "  Next:"
echo "  1. claude plugin marketplace update atlassian-pm"
echo "  2. claude plugin update atlassian-pm@atlassian-pm"
echo "  3. Restart Claude Code to load v$NEW_VERSION"
