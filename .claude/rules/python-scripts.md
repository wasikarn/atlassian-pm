---
paths:
  - "scripts/**/*.py"
  - "hooks/**/*.py"
  - "skills/atlassian-scripts/**/*.py"
---

# Python Script Conventions

- Use stdlib only (no pip install) — scripts must run on any machine with Python 3.x
- SSL bypass already built into Atlassian scripts — don't add redundant SSL handling
- Use `hooks_lib.py` and `hooks_state.py` for shared hook utilities (don't duplicate)
- Exit codes in hooks: 0 = proceed, 2 = block with stderr feedback, other = proceed with warning
- Hook scripts receive JSON on stdin — parse with `json.loads(sys.stdin.read())`
- Use `$CLAUDE_PROJECT_DIR` for absolute paths in hook commands
- Format with `ruff` (config in `ruff.toml`)
