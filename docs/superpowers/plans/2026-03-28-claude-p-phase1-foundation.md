# Claude -p Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create shared `claude_call()` utility that wraps `claude -p` with recursion guard — prerequisite for all other phases.

**Architecture:** Single utility module at `hooks/plugin/ai/claude_call.py`. All AI hooks and scripts import from here. Recursion guard via `ATLASSIAN_PM_HOOK_DEPTH` env var prevents infinite loops when `claude -p` fires a new Claude Code session that would re-trigger hooks.

**Tech Stack:** Python stdlib only (`subprocess`, `json`, `os`). Claude Code CLI (`claude -p --output-format json`).

---

## File Map

| Action | File | Responsibility |
|---|---|---|
| Create | `hooks/plugin/ai/__init__.py` | Package marker |
| Create | `hooks/plugin/ai/claude_call.py` | Shared `claude -p` wrapper + recursion guard |
| Create | `hooks/tests/test_claude_call.py` | Unit tests (subprocess mocked) |
| Modify | `hooks/plugin/session/start_prerequisite_check.py` | Add `claude` binary check |

---

### Task 1: Verify `claude -p` output format

**Files:** (no changes — discovery only)

- [ ] **Step 1: Run `claude -p` with JSON output to confirm schema**

```bash
claude -p "respond with the single word: hello" --output-format json
```

Expected output structure:

```json
{"type":"result","subtype":"success","is_error":false,"result":"hello","session_id":"...","cost_usd":...}
```

Note the `result` field — this is the text response. Log the actual output for reference.

- [ ] **Step 2: Confirm recursion guard env var works**

```bash
ATLASSIAN_PM_HOOK_DEPTH=1 claude -p "respond with the single word: hello" --output-format json
```

Verify this still works (env var doesn't affect `claude -p` itself — it's only read by our scripts).

- [ ] **Step 3: Commit discovery notes**

```bash
git commit --allow-empty -m "chore: verify claude -p output schema (see Phase 1 plan)"
```

---

### Task 2: Create package + `claude_call` utility

**Files:**

- Create: `hooks/plugin/ai/__init__.py`
- Create: `hooks/plugin/ai/claude_call.py`
- Create: `hooks/tests/test_claude_call.py`

- [ ] **Step 1: Write failing tests first**

Create `hooks/tests/test_claude_call.py`:

```python
#!/usr/bin/env python3
"""Tests for hooks/plugin/ai/claude_call.py"""

import json
import os
import subprocess
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from plugin.ai.claude_call import RECURSION_GUARD, claude_call, extract_result


class TestClaudeCall(unittest.TestCase):

    def _make_proc(self, stdout: str, returncode: int = 0) -> MagicMock:
        m = MagicMock()
        m.returncode = returncode
        m.stdout = stdout
        m.stderr = ""
        return m

    def test_returns_result_on_success(self):
        payload = json.dumps({
            "type": "result", "subtype": "success",
            "is_error": False, "result": "hello", "session_id": "s1"
        })
        with patch("subprocess.run", return_value=self._make_proc(payload)):
            result = claude_call("say hello")
        self.assertEqual(result, "hello")

    def test_sets_recursion_guard_env(self):
        payload = json.dumps({"type": "result", "subtype": "success", "is_error": False, "result": "ok"})
        captured_env = {}

        def fake_run(cmd, **kwargs):
            captured_env.update(kwargs.get("env", {}))
            return self._make_proc(payload)

        with patch("subprocess.run", side_effect=fake_run):
            claude_call("test")
        self.assertEqual(captured_env.get(RECURSION_GUARD), "1")

    def test_returns_none_when_recursion_guard_set(self):
        with patch.dict(os.environ, {RECURSION_GUARD: "1"}):
            result = claude_call("test")
        self.assertIsNone(result)

    def test_returns_none_on_timeout(self):
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("claude", 15)):
            result = claude_call("test")
        self.assertIsNone(result)

    def test_returns_none_when_claude_not_found(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = claude_call("test")
        self.assertIsNone(result)

    def test_returns_none_on_nonzero_exit(self):
        with patch("subprocess.run", return_value=self._make_proc("", returncode=1)):
            result = claude_call("test")
        self.assertIsNone(result)

    def test_returns_none_on_invalid_json(self):
        with patch("subprocess.run", return_value=self._make_proc("not json")):
            result = claude_call("test")
        self.assertIsNone(result)

    def test_extract_result_from_json(self):
        data = {"type": "result", "subtype": "success", "is_error": False, "result": "answer"}
        self.assertEqual(extract_result(data), "answer")

    def test_extract_result_returns_none_on_error(self):
        data = {"type": "result", "subtype": "error", "is_error": True, "result": ""}
        self.assertIsNone(extract_result(data))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /path/to/atlassian-pm
python3 -m pytest hooks/tests/test_claude_call.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'plugin.ai.claude_call'`

- [ ] **Step 3: Create package marker**

Create `hooks/plugin/ai/__init__.py`:

```python
```

(empty file)

- [ ] **Step 4: Implement `claude_call.py`**

Create `hooks/plugin/ai/claude_call.py`:

```python
#!/usr/bin/env python3
"""Shared utility: call `claude -p` for LLM reasoning in hooks and scripts.

Usage:
    from plugin.ai.claude_call import claude_call

    result = claude_call("classify this intent: create a bug for login failure")
    if result:
        # result is the plain text response from claude
        print(result)

Recursion guard: sets ATLASSIAN_PM_HOOK_DEPTH=1 in subprocess env.
Any hook that checks this var on entry will skip the AI call,
preventing infinite loops when claude -p fires a new Claude Code session.
"""

import json
import os
import subprocess
from typing import Optional

RECURSION_GUARD = "ATLASSIAN_PM_HOOK_DEPTH"
_CLAUDE_TIMEOUT = 15  # seconds


def claude_call(prompt: str, timeout: int = _CLAUDE_TIMEOUT) -> Optional[str]:
    """Call `claude -p` non-interactively and return the text response.

    Args:
        prompt:  The prompt to send to claude.
        timeout: Subprocess timeout in seconds (default 15).

    Returns:
        The text response string, or None on any error.
    """
    # Recursion guard: if we are already inside a claude -p session, skip
    if os.environ.get(RECURSION_GUARD):
        return None

    env = {**os.environ, RECURSION_GUARD: "1"}
    try:
        proc = subprocess.run(
            ["claude", "-p", prompt, "--output-format", "json"],
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return None
    except (FileNotFoundError, OSError):
        # `claude` binary not found
        return None

    if proc.returncode != 0 or not proc.stdout.strip():
        return None

    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None

    return extract_result(data)


def extract_result(data: dict) -> Optional[str]:
    """Extract the text result from a `claude -p --output-format json` response.

    Returns None if the response indicates an error.
    """
    if data.get("is_error"):
        return None
    result = data.get("result", "")
    return result if result else None
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
python3 -m pytest hooks/tests/test_claude_call.py -v
```

Expected: `8 passed`

- [ ] **Step 6: Commit**

```bash
git add hooks/plugin/ai/__init__.py hooks/plugin/ai/claude_call.py hooks/tests/test_claude_call.py
git commit -m "feat(ai): add claude_call utility with recursion guard (Phase 1)"
```

---

### Task 3: Add `claude` binary check to prerequisite check

**Files:**

- Modify: `hooks/plugin/session/start_prerequisite_check.py`

- [ ] **Step 1: Read the current file**

```bash
cat hooks/plugin/session/start_prerequisite_check.py
```

Understand the existing check pattern before modifying.

- [ ] **Step 2: Add `claude` binary check**

Find the section that checks prerequisites (likely checks for `acli`, `python3`, or similar tools).
Add after existing checks:

```python
# Check claude CLI available (needed for AI hooks — Phase 2+)
import shutil
claude_found = shutil.which("claude") is not None
if not claude_found:
    # Non-blocking: AI hooks degrade gracefully if claude not found
    lines.append("⚠️  claude CLI not found — AI hooks (Phase 2+) will be skipped. Install Claude Code to enable.")
```

Note: this check is **non-blocking** — exit 0 always. AI hooks degrade gracefully.

- [ ] **Step 3: Verify hook still exits 0**

```bash
echo '{"session_id": "test", "hook_event_name": "SessionStart"}' | python3 hooks/plugin/session/start_prerequisite_check.py
echo "exit: $?"
```

Expected: exit code 0 (regardless of whether claude is found)

- [ ] **Step 4: Commit**

```bash
git add hooks/plugin/session/start_prerequisite_check.py
git commit -m "feat(ai): add claude CLI prerequisite check (non-blocking)"
```

---

### Task 4: Smoke test end-to-end

**Files:** (no changes)

- [ ] **Step 1: Test `claude_call` from command line**

```bash
python3 -c "
import sys; sys.path.insert(0, 'hooks')
from plugin.ai.claude_call import claude_call
result = claude_call('respond with only the word: WORKING')
print('Result:', repr(result))
print('Pass' if result and 'WORKING' in result.upper() else 'FAIL')
"
```

Expected: `Result: 'WORKING'` and `Pass`

- [ ] **Step 2: Test recursion guard**

```bash
ATLASSIAN_PM_HOOK_DEPTH=1 python3 -c "
import sys; sys.path.insert(0, 'hooks')
from plugin.ai.claude_call import claude_call
result = claude_call('respond with only the word: WORKING')
print('Guard blocked:', result is None)
"
```

Expected: `Guard blocked: True`

- [ ] **Step 3: Run full hook test suite to confirm no regressions**

```bash
python3 -m pytest hooks/tests/ -v --tb=short
```

Expected: all existing tests pass + 8 new claude_call tests pass

- [ ] **Step 4: Final commit**

```bash
git commit --allow-empty -m "chore: Phase 1 complete — claude_call foundation ready"
```

---

## Phase 1 Complete

Foundation is ready. Next phases can now be executed independently:

- `2026-03-28-claude-p-phase2-ai-hooks.md` — smarter hook scripts
- `2026-03-28-claude-p-phase3-ai-scripts.md` — enrichment scripts
- `2026-03-28-claude-p-phase4-monitor.md` — autonomous monitor
