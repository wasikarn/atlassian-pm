# Claude -p AI Scripts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Prerequisite:** Phase 1 complete — `hooks/plugin/ai/claude_call.py` must exist.

**Goal:** Standalone AI enrichment scripts callable from skill phases via Bash tool — enrich rough text → ADF JSON, suggest subtask breakdowns, polish ADF before QG check.

**Architecture:** Scripts in `scripts/ai/`. Each script takes CLI args, calls `claude -p`, outputs to stdout. Failure contract: exit 1 + empty stdout → skill falls back to manual ADF writing. Scripts are stateless — safe to call any time, no session state dependency.

**Tech Stack:** Python stdlib + `subprocess` calling `claude -p --output-format json`. Scripts follow same conventions as `scripts/api/` (no pip deps, `ruff` formatting).

---

## File Map

| Action | File | Responsibility |
|---|---|---|
| Create | `scripts/ai/__init__.py` | Package marker |
| Create | `scripts/ai/claude_runner.py` | Thin wrapper: call `claude -p`, same recursion guard |
| Create | `scripts/ai/enrich_description.py` | Rough text → ADF JSON with all required sections |
| Create | `scripts/ai/suggest_subtasks.py` | Story ACs → suggested subtask breakdown |
| Create | `scripts/ai/pre_qg_polish.py` | ADF draft → improve weak sections before QG |
| Create | `scripts/tests/test_ai_scripts.py` | Unit tests (claude_call mocked) |

---

### Task 1: Create `scripts/ai/claude_runner.py`

Scripts live in `scripts/` which has a different sys.path than `hooks/`. This thin wrapper avoids duplicating the recursion guard logic.

**Files:**

- Create: `scripts/ai/__init__.py`
- Create: `scripts/ai/claude_runner.py`
- Create: `scripts/tests/test_ai_scripts.py` (start with runner tests)

- [ ] **Step 1: Write failing tests**

Create `scripts/tests/test_ai_scripts.py`:

```python
#!/usr/bin/env python3
"""Tests for scripts/ai/*.py (claude -p mocked)"""

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ai.claude_runner import RECURSION_GUARD, run_claude
from ai.enrich_description import build_enrich_prompt, parse_adf_from_response
from ai.suggest_subtasks import build_subtask_prompt, parse_subtasks_from_response
from ai.pre_qg_polish import build_polish_prompt, parse_polished_adf


class TestClaudeRunner(unittest.TestCase):

    def _make_proc(self, stdout: str, returncode: int = 0) -> MagicMock:
        m = MagicMock()
        m.returncode = returncode
        m.stdout = stdout
        m.stderr = ""
        return m

    def test_returns_text_on_success(self):
        payload = json.dumps({"type": "result", "subtype": "success",
                               "is_error": False, "result": "hello"})
        with patch("subprocess.run", return_value=self._make_proc(payload)):
            result = run_claude("say hello")
        self.assertEqual(result, "hello")

    def test_recursion_guard_skips(self):
        with patch.dict(os.environ, {RECURSION_GUARD: "1"}):
            result = run_claude("test")
        self.assertIsNone(result)

    def test_returns_none_on_failure(self):
        with patch("subprocess.run", return_value=self._make_proc("", returncode=1)):
            result = run_claude("test")
        self.assertIsNone(result)


class TestEnrichDescription(unittest.TestCase):

    def test_build_prompt_contains_text(self):
        prompt = build_enrich_prompt("user needs login feature", "story")
        self.assertIn("user needs login feature", prompt)
        self.assertIn("story", prompt.lower())

    def test_parse_adf_extracts_json_block(self):
        response = '```json\n{"version": 1, "type": "doc", "content": []}\n```'
        result = parse_adf_from_response(response)
        self.assertIsNotNone(result)
        self.assertEqual(result["type"], "doc")

    def test_parse_adf_returns_none_on_invalid(self):
        result = parse_adf_from_response("no json here")
        self.assertIsNone(result)


class TestSuggestSubtasks(unittest.TestCase):

    def test_build_prompt_contains_acs(self):
        prompt = build_subtask_prompt("{{PROJECT_KEY}}-100", ["AC1: user can login", "AC2: user can logout"])
        self.assertIn("AC1", prompt)
        self.assertIn("AC2", prompt)

    def test_parse_subtasks_from_numbered_list(self):
        response = "1. Implement login endpoint\n2. Add logout button\n3. Write integration tests"
        result = parse_subtasks_from_response(response)
        self.assertEqual(len(result), 3)
        self.assertIn("Implement login endpoint", result[0])

    def test_parse_subtasks_returns_empty_on_invalid(self):
        result = parse_subtasks_from_response("")
        self.assertEqual(result, [])


class TestPreQgPolish(unittest.TestCase):

    def test_build_polish_prompt_contains_adf(self):
        adf = {"version": 1, "type": "doc", "content": []}
        prompt = build_polish_prompt(json.dumps(adf), "story")
        self.assertIn('"type": "doc"', prompt)

    def test_parse_polished_adf_extracts_json(self):
        adf = {"version": 1, "type": "doc", "content": [{"type": "paragraph"}]}
        response = f'```json\n{json.dumps(adf)}\n```'
        result = parse_polished_adf(response)
        self.assertIsNotNone(result)
        self.assertEqual(result["type"], "doc")

    def test_parse_polished_adf_returns_none_on_garbage(self):
        result = parse_polished_adf("cannot improve this")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify fail**

```bash
python3 -m pytest scripts/tests/test_ai_scripts.py -v 2>&1 | head -10
```

Expected: `ModuleNotFoundError: No module named 'ai.claude_runner'`

- [ ] **Step 3: Create package marker**

Create `scripts/ai/__init__.py`:

```python
```

(empty file)

- [ ] **Step 4: Implement `claude_runner.py`**

Create `scripts/ai/claude_runner.py`:

```python
#!/usr/bin/env python3
"""Thin wrapper around `claude -p` for scripts/ai/ scripts.

Same recursion guard as hooks/plugin/ai/claude_call.py —
prevents infinite loops when claude -p fires a new Claude Code session.
"""

import json
import os
import subprocess
from typing import Optional

RECURSION_GUARD = "ATLASSIAN_PM_HOOK_DEPTH"
_TIMEOUT = 20  # scripts can afford slightly longer timeout than hooks


def run_claude(prompt: str, timeout: int = _TIMEOUT) -> Optional[str]:
    """Call `claude -p` and return plain text response, or None on any error."""
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
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None

    if proc.returncode != 0 or not proc.stdout.strip():
        return None

    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None

    if data.get("is_error"):
        return None
    return data.get("result") or None
```

- [ ] **Step 5: Run claude_runner tests**

```bash
python3 -m pytest scripts/tests/test_ai_scripts.py::TestClaudeRunner -v
```

Expected: `3 passed`

- [ ] **Step 6: Commit runner**

```bash
git add scripts/ai/__init__.py scripts/ai/claude_runner.py scripts/tests/test_ai_scripts.py
git commit -m "feat(ai-scripts): add claude_runner wrapper for scripts/ai/ layer"
```

---

### Task 2: Implement `enrich_description.py`

**Files:**

- Create: `scripts/ai/enrich_description.py`

Converts rough description text into a structured ADF JSON with all required sections (Background, Goals, ACs, Out of Scope). Called from create-story skill Phase 3.

- [ ] **Step 1: Implement `enrich_description.py`**

Create `scripts/ai/enrich_description.py`:

```python
#!/usr/bin/env python3
"""AI script: enrich rough description → structured ADF JSON.

Usage:
    python3 scripts/ai/enrich_description.py --text "rough description" --type story
    python3 scripts/ai/enrich_description.py --text "rough description" --type task

Output (stdout): ADF JSON string ready to embed in Jira create/edit payload.
Exit 0: success (ADF JSON on stdout)
Exit 1: claude unavailable or parse failure (empty stdout — caller falls back)
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from claude_runner import run_claude

_ENRICH_PROMPT = """\
You are writing a Jira {issue_type} description in Atlassian Document Format (ADF).

User's rough description:
{text}

Write a complete ADF JSON document with these sections as headings:
1. Background — why this is needed
2. Goals — what success looks like (2-4 bullet points)
3. Acceptance Criteria — numbered list, each starting "AC{n}:"
4. Out of Scope — what this does NOT cover

Return ONLY a valid JSON code block in this format:
```json
{{"version": 1, "type": "doc", "content": [...]}}
```

Use ADF paragraph, heading (level 3), bulletList, orderedList nodes.
Do not add any text outside the JSON block."""

def build_enrich_prompt(text: str, issue_type: str) -> str:
    return _ENRICH_PROMPT.format(text=text[:1000], issue_type=issue_type)

def parse_adf_from_response(response: str) -> Optional[dict]:
    """Extract JSON from a ```json ...``` block or bare JSON."""
    # Try fenced block first
    match = re.search(r"```json\s*(\{.*?\})\s*```", response, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    # Try bare JSON
    match = re.search(r"(\{[\"']version[\"'].*\})", response, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    return None

def main() -> None:
    parser = argparse.ArgumentParser(description="Enrich rough description to ADF JSON")
    parser.add_argument("--text", required=True, help="Rough description text")
    parser.add_argument("--type", default="story", dest="issue_type",
                        choices=["story", "task", "epic", "bug"],
                        help="Issue type (default: story)")
    args = parser.parse_args()

    prompt = build_enrich_prompt(args.text, args.issue_type)
    response = run_claude(prompt, timeout=25)

    if not response:
        sys.exit(1)

    adf = parse_adf_from_response(response)
    if not adf:
        sys.exit(1)

    print(json.dumps(adf, ensure_ascii=False, indent=2))

if **name** == "**main**":
    main()

```

- [ ] **Step 2: Run enrich tests**

```bash
python3 -m pytest scripts/tests/test_ai_scripts.py::TestEnrichDescription -v
```

Expected: `3 passed`

- [ ] **Step 3: Smoke test the script**

```bash
python3 scripts/ai/enrich_description.py \
  --text "Users can't reset password via email link — link expires too fast" \
  --type bug
```

Expected: valid ADF JSON printed to stdout with `version`, `type`, `content` fields.

- [ ] **Step 4: Commit**

```bash
git add scripts/ai/enrich_description.py
git commit -m "feat(ai-scripts): add enrich_description — rough text → ADF JSON"
```

---

### Task 3: Implement `suggest_subtasks.py`

**Files:**

- Create: `scripts/ai/suggest_subtasks.py`

Takes a story key + AC list, returns suggested subtask names. Called from create-story Phase 5 as an optional enrichment step.

- [ ] **Step 1: Implement `suggest_subtasks.py`**

Create `scripts/ai/suggest_subtasks.py`:

```python
#!/usr/bin/env python3
"""AI script: suggest subtask breakdown from story ACs.

Usage:
    python3 scripts/ai/suggest_subtasks.py --story {{PROJECT_KEY}}-123 --acs "AC1: ...\nAC2: ..."

Output (stdout): JSON array of suggested subtask summaries.
Exit 0: success
Exit 1: claude unavailable (empty stdout — caller continues without suggestions)
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from claude_runner import run_claude

_SUBTASK_PROMPT = """\
You are a senior software engineer breaking down a Jira story into implementation subtasks.

Story key: {story_key}
Acceptance Criteria:
{acs}

Generate a numbered list of implementation subtasks. Each subtask should:
- Map to one or more ACs (note which AC in brackets)
- Be completable in 1-2 days
- Include service layer hint: [BE], [FE-Admin], [FE-Web], [Video], or [AI-Agent]

Format each line as:
N. [SERVICE] Subtask name — covers AC1, AC3

List only the subtasks, no extra commentary."""


def build_subtask_prompt(story_key: str, acs: list[str]) -> str:
    acs_text = "\n".join(acs[:15])
    return _SUBTASK_PROMPT.format(story_key=story_key, acs=acs_text)


def parse_subtasks_from_response(response: str) -> list[str]:
    """Extract numbered list items from response."""
    if not response.strip():
        return []
    lines = response.strip().split("\n")
    subtasks = []
    for line in lines:
        # Match: "1. [BE] Implement something"
        match = re.match(r"^\d+\.\s+(.+)$", line.strip())
        if match:
            subtasks.append(match.group(1).strip())
    return subtasks


def main() -> None:
    parser = argparse.ArgumentParser(description="Suggest subtask breakdown from story ACs")
    parser.add_argument("--story", required=True, help="Story key e.g. {{PROJECT_KEY}}-123")
    parser.add_argument("--acs", required=True,
                        help="Acceptance criteria, one per line (newline-separated)")
    args = parser.parse_args()

    acs = [ac.strip() for ac in args.acs.strip().split("\n") if ac.strip()]
    if not acs:
        print("[]")
        sys.exit(0)

    prompt = build_subtask_prompt(args.story, acs)
    response = run_claude(prompt, timeout=25)

    if not response:
        sys.exit(1)

    subtasks = parse_subtasks_from_response(response)
    if not subtasks:
        sys.exit(1)

    print(json.dumps(subtasks, ensure_ascii=False))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run subtask tests**

```bash
python3 -m pytest scripts/tests/test_ai_scripts.py::TestSuggestSubtasks -v
```

Expected: `3 passed`

- [ ] **Step 3: Smoke test**

```bash
python3 scripts/ai/suggest_subtasks.py \
  --story {{PROJECT_KEY}}-100 \
  --acs "AC1: User can login with email\nAC2: User can reset password\nAC3: Login errors shown inline"
```

Expected: JSON array like `["[BE] Implement login endpoint — covers AC1", "[FE-Web] Login form with error display — covers AC1, AC3", ...]`

- [ ] **Step 4: Commit**

```bash
git add scripts/ai/suggest_subtasks.py
git commit -m "feat(ai-scripts): add suggest_subtasks — story ACs → subtask breakdown"
```

---

### Task 4: Implement `pre_qg_polish.py`

**Files:**

- Create: `scripts/ai/pre_qg_polish.py`

Takes ADF JSON draft, asks Claude to identify and fix weak sections before QG check.

- [ ] **Step 1: Implement `pre_qg_polish.py`**

Create `scripts/ai/pre_qg_polish.py`:

```python
#!/usr/bin/env python3
"""AI script: polish ADF draft before QG check.

Usage:
    python3 scripts/ai/pre_qg_polish.py --file /path/to/draft.json --type story
    cat draft.json | python3 scripts/ai/pre_qg_polish.py --stdin --type story

Output (stdout): improved ADF JSON.
Exit 0: success (improved ADF on stdout)
Exit 1: unavailable — caller uses original draft unchanged.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from claude_runner import run_claude

_POLISH_PROMPT = """\
You are reviewing a Jira {issue_type} ADF JSON description before it goes through a quality gate.

Current ADF:
```json
{adf}
```

Quality gate checks for:

- At least 3 acceptance criteria (AC1:, AC2:, AC3: format)
- Background section present and non-trivial (>20 words)
- Goals section with 2+ bullet points
- Out of Scope section present
- No placeholder text like "TBD" or "Lorem ipsum"

Improve the ADF to pass these checks. Keep existing good content.
Return ONLY the improved ADF as a JSON code block:

```json
{{"version": 1, "type": "doc", "content": [...]}}
```"""


def build_polish_prompt(adf_json: str, issue_type: str) -> str:
    return _POLISH_PROMPT.format(adf=adf_json[:3000], issue_type=issue_type)


def parse_polished_adf(response: str) -> Optional[dict]:
    """Extract improved ADF from response."""
    match = re.search(r"```json\s*(\{.*?\})\s*```", response, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Polish ADF JSON before QG check")
    parser.add_argument("--file", help="Path to ADF JSON file")
    parser.add_argument("--stdin", action="store_true", help="Read ADF from stdin")
    parser.add_argument("--type", default="story", dest="issue_type",
                        choices=["story", "task", "epic", "bug", "subtask"])
    args = parser.parse_args()

    if args.stdin:
        raw = sys.stdin.read()
    elif args.file:
        raw = Path(args.file).read_text()
    else:
        parser.error("Provide --file or --stdin")

    try:
        adf_data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    prompt = build_polish_prompt(json.dumps(adf_data, indent=2), args.issue_type)
    response = run_claude(prompt, timeout=30)

    if not response:
        sys.exit(1)

    polished = parse_polished_adf(response)
    if not polished:
        sys.exit(1)

    print(json.dumps(polished, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run all AI script tests**

```bash
python3 -m pytest scripts/tests/test_ai_scripts.py -v
```

Expected: `12 passed`

- [ ] **Step 3: Smoke test polish flow**

```bash
# Create a weak ADF draft
cat > /tmp/weak_adf.json << 'EOF'
{
  "version": 1,
  "type": "doc",
  "content": [
    {"type": "paragraph", "content": [{"type": "text", "text": "We need a login feature. TBD."}]}
  ]
}
EOF

python3 scripts/ai/pre_qg_polish.py --file /tmp/weak_adf.json --type story | python3 -m json.tool | head -20
```

Expected: valid ADF JSON with expanded content (Background, Goals, ACs, Out of Scope sections).

- [ ] **Step 4: Commit**

```bash
git add scripts/ai/pre_qg_polish.py
git commit -m "feat(ai-scripts): add pre_qg_polish — improve ADF before quality gate"
```

---

### Task 5: Run full test suite

- [ ] **Step 1: Run all tests**

```bash
python3 -m pytest hooks/tests/ scripts/tests/ -v --tb=short 2>&1 | tail -20
```

Expected: all tests pass, no regressions in existing hooks tests.

- [ ] **Step 2: Final commit**

```bash
git commit --allow-empty -m "chore: Phase 3 complete — AI enrichment scripts ready"
```

---

## Phase 3 Complete

Three enrichment scripts available. Call from skill phases via Bash tool:

```bash
# In create-story skill, Phase 3 (ADF enrichment step):
python3 scripts/ai/enrich_description.py --text "..." --type story

# In create-story skill, Phase 5 (subtask planning):
python3 scripts/ai/suggest_subtasks.py --story {{PROJECT_KEY}}-123 --acs "AC1: ...\nAC2: ..."

# Before QG check in any skill:
python3 scripts/ai/pre_qg_polish.py --file /tmp/draft.json --type story
```

All scripts degrade gracefully (exit 1, empty stdout) if `claude -p` is unavailable.
