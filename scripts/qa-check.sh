#!/usr/bin/env bash
# qa-check.sh — QA gates for atlassian-pm (mirrors .github/workflows/qa.yml)
# Usage: bash scripts/qa-check.sh

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT" || exit 1

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'

PASS=0; FAIL=0; SKIP=0
pass()    { echo -e "  ${GREEN}✓${NC} $*"; PASS=$((PASS + 1)); }
fail()    { echo -e "  ${RED}✗${NC} $*" >&2; FAIL=$((FAIL + 1)); }
skip()    { echo -e "  ${YELLOW}–${NC} $*"; SKIP=$((SKIP + 1)); }
section() { echo -e "\n${CYAN}$*${NC}"; }

# ── 1. shellcheck ─────────────────────────────────────────────────────────────
section "1. shellcheck"
if ! command -v shellcheck > /dev/null 2>&1; then
  skip "shellcheck not installed — skipping"
else
  SH_FILES=()
  while IFS= read -r -d $'\0' f; do SH_FILES+=("$f"); done \
    < <(find hooks scripts -name "*.sh" -print0 2>/dev/null | sort -z)
  if [ ${#SH_FILES[@]} -eq 0 ]; then
    skip "no .sh files found"
  elif shellcheck --severity=warning "${SH_FILES[@]}" 2>&1; then
    pass "shellcheck — ${#SH_FILES[@]} scripts OK"
  else
    fail "shellcheck — errors found in one or more scripts"
  fi
fi

# ── 2. markdownlint ───────────────────────────────────────────────────────────
section "2. markdownlint"
if ! command -v markdownlint-cli2 > /dev/null 2>&1; then
  skip "markdownlint-cli2 not installed — skipping"
else
  MD_OUTPUT=$(
    cd "$REPO_ROOT" || exit 0
    markdownlint-cli2 "**/*.md" "!.omc/**" "!.claude/**" 2>&1 || true
  )
  MD_ERRORS=$(echo "$MD_OUTPUT" | grep "^Summary:" | grep -oE '[0-9]+' | head -1 || true)
  MD_FILES=$(echo "$MD_OUTPUT" | grep "^Linting:" | grep -oE '[0-9]+' | head -1 || true)
  if [ "${MD_ERRORS:-0}" -eq 0 ]; then
    pass "markdownlint — ${MD_FILES:-?} files, 0 errors"
  else
    fail "markdownlint — $MD_ERRORS error(s) across ${MD_FILES:-?} file(s)"
    echo "$MD_OUTPUT" | grep -v "^Linting:\|^Summary:" >&2 || true
  fi
fi

# ── 3. plugin.json ────────────────────────────────────────────────────────────
section "3. plugin.json"
if _OUT=$(python3 - <<'PY' 2>&1
import json, sys
required = ["name", "version", "description"]
try:
    p = json.load(open(".claude-plugin/plugin.json"))
except FileNotFoundError:
    print("plugin.json not found"); sys.exit(1)
missing = [k for k in required if not p.get(k)]
if missing:
    print(f"missing fields: {missing}"); sys.exit(1)
print(f"version {p['version']}, all required fields present")
PY
); then
  pass "plugin.json — $_OUT"
else
  fail "plugin.json — $_OUT"
fi

# ── 4. SKILL.md frontmatter ───────────────────────────────────────────────────
section "4. SKILL.md frontmatter"
if _OUT=$(python3 - <<'PY' 2>&1
import os, sys
errors = []; count = 0
for root, _, files in os.walk("skills"):
    if "SKILL.md" in files:
        count += 1
        path = os.path.join(root, "SKILL.md")
        content = open(path).read()
        if not content.startswith("---"):
            errors.append(f"{path}: missing frontmatter"); continue
        block = content.split("---")[1]
        for field in ["name", "description"]:
            if f"{field}:" not in block:
                errors.append(f"{path}: missing '{field}'")
if errors:
    for e in errors: print(e)
    sys.exit(1)
print(f"{count} skills OK")
PY
); then
  pass "SKILL.md frontmatter — $_OUT"
else
  fail "SKILL.md frontmatter — $_OUT"
fi

# ── 5. agent frontmatter ──────────────────────────────────────────────────────
section "5. agent frontmatter"
if _OUT=$(python3 - <<'PY' 2>&1
import os, sys
errors = []; count = 0
for fname in os.listdir("agents"):
    if not fname.endswith(".md"): continue
    count += 1
    path = os.path.join("agents", fname)
    content = open(path).read()
    if not content.startswith("---"):
        errors.append(f"{path}: missing frontmatter"); continue
    block = content.split("---")[1]
    for field in ["name", "description"]:
        if f"{field}:" not in block:
            errors.append(f"{path}: missing '{field}'")
if errors:
    for e in errors: print(e)
    sys.exit(1)
print(f"{count} agents OK")
PY
); then
  pass "agent frontmatter — $_OUT"
else
  fail "agent frontmatter — $_OUT"
fi

# ── 6. hooks.json script references ──────────────────────────────────────────
section "6. hooks.json script references"
if _OUT=$(python3 - <<'PY' 2>&1
import json, os, re, sys
try:
    hooks = json.load(open("hooks/hooks.json"))
except FileNotFoundError:
    print("hooks/hooks.json not found"); sys.exit(1)
missing = []
for event, entries in hooks.get("hooks", {}).items():
    for entry in entries:
        for hook in entry.get("hooks", []):
            cmd = hook.get("command", "")
            for m in re.finditer(r'hooks/[^\s"\']+\.(?:sh|py)', cmd):
                script = m.group(0)
                if not os.path.exists(script):
                    missing.append(f"{event}: {script}")
if missing:
    for m in missing: print(m)
    sys.exit(1)
print("all script references found")
PY
); then
  pass "hooks.json — $_OUT"
else
  fail "hooks.json — $_OUT"
fi

# ── 7. Python hook tests ──────────────────────────────────────────────────────
section "7. Python hook tests"
if ! command -v python3 > /dev/null 2>&1; then
  skip "python3 not found — skipping"
elif [ ! -d "hooks/tests" ]; then
  skip "hooks/tests not found — skipping"
elif python3 -m pytest hooks/tests/ -q --tb=short 2>&1; then
  pass "pytest — hooks/tests/ OK"
else
  fail "pytest — test failures found"
fi

# ── 8. CHANGELOG ──────────────────────────────────────────────────────────────
section "8. CHANGELOG"
VERSION=$(python3 -c "import json; print(json.load(open('.claude-plugin/plugin.json'))['version'])" 2>/dev/null || true)
if [ -z "$VERSION" ]; then
  fail "CHANGELOG — could not read version from plugin.json"
elif grep -q "\[${VERSION}\]" CHANGELOG.md 2>/dev/null; then
  pass "CHANGELOG.md — v${VERSION} entry found"
else
  fail "CHANGELOG.md — missing entry for v${VERSION}"
fi

# ── 9. required files ─────────────────────────────────────────────────────────
section "9. required files"
for f in LICENSE README.md CHANGELOG.md; do
  if [ -f "$f" ]; then
    pass "$f found"
  else
    fail "$f missing"
  fi
done

# ── summary ───────────────────────────────────────────────────────────────────
echo ""
echo "────────────────────────────────────────────"
echo "  Passed  : $PASS"
[ "$SKIP" -gt 0 ] && echo "  Skipped : $SKIP"
[ "$FAIL" -gt 0 ] && echo -e "  ${RED}Failed  : $FAIL${NC}"
echo "────────────────────────────────────────────"

if [ "$FAIL" -gt 0 ]; then
  echo -e "${RED}✗ QA FAILED${NC} — $FAIL check(s) need attention"
  exit 1
else
  echo -e "${GREEN}✓ QA PASSED${NC}"
fi
