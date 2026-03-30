# Token Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ลด token consumption ของ atlassian-pm plugin โดยไม่ลด capability — เน้น skill file compression, references compression, model routing, และ MCP response optimization

**Architecture:** Compression-first approach — ลด context ที่โหลดต่อ invocation ให้เล็กลงมากที่สุด ส่วนที่ทำได้เร็วทำ inline, ส่วนที่เป็น large file compression ใช้ parallel agents

**Tech Stack:** Python 3.x, Markdown, atlassian-pm plugin hooks/skills/agents

---

## ผล Analysis

| ไฟล์ | ขนาดปัจจุบัน | เป้าหมาย | เหตุผล |
|------|------------|---------|-------|
| `agents/quality-gate.md` | model: sonnet | model: haiku | ADF validation เป็น rule-based ไม่ต้องการ reasoning ลึก |
| `CLAUDE.md` | 8,693 bytes | ~5,000 | HR verbose details ซ้ำกับ hook enforcement |
| `post_filter_mcp_response.py` | no desc truncation | truncate search desc | search results ไม่ต้องการ full ADF description |
| `references/templates-subtask.md` | 15,128 bytes | ~6,000 | ADF examples ซ้ำกับ templates-core.md |
| `references/vertical-slice-guide.md` | 8,961 bytes | ~3,500 | Framework reference ใช้ ~30% เท่านั้น |
| `references/templates-vibe.md` | 9,972 bytes | ~4,500 | Overlap กับ templates-core.md |
| `skills/story/create-story/SKILL.md` | 37,092 bytes | ~14,000 | Phase boilerplate + inline examples bloat |
| `skills/sprint/plan-sprint/SKILL.md` | 22,634 bytes | ~10,000 | Domain notes + inline examples |
| `skills/epic/blueprint/SKILL.md` | 20,824 bytes | ~9,000 | Verbose debate protocol inline |
| `skills/story/analyze-story/SKILL.md` | 16,801 bytes | ~8,000 | Inline subtask examples |

---

## Universal Compression Rules

ใช้กับทุก file compression task:

1. **ลบ inline ADF JSON examples** ที่มีอยู่แล้วใน `references/templates-core.md` → เหลือแค่ pointer `→ see references/templates-core.md`
2. **ลบ phase boilerplate structure** (`**Goal:**`, `**Required inputs:**`, `**Constraints:**`, `**Output:**`) เมื่อ header ของ phase บอกอยู่แล้ว
3. **ย่อ MCP call examples** จาก multi-line JSON → 1-line function call signature
4. **ย่อ Domain Expert Notes** เหลือ key bullets (max 5 bullets per section)
5. **ย่อ numbered steps ที่ obvious** → เหลือเฉพาะ non-obvious rules
6. **ลบ duplicate instructions** ที่บอกซ้ำในหลาย phases
7. **คงไว้**: Gate markers (`⛔ GATE`), Phase structure, Hard Rule references, MCP tool names + fields

---

## Task 1: quality-gate Agent → Haiku

**Files:**
- Modify: `agents/quality-gate.md` line 17

- [ ] **Step 1: Change model**

```markdown
# เปลี่ยน
model: sonnet
# เป็น
model: haiku
```

- [ ] **Step 2: Commit**
```bash
git add agents/quality-gate.md
git commit -m "perf(agents): quality-gate model sonnet→haiku — rule-based validation"
```

---

## Task 2: CLAUDE.md — Add Compaction Instructions + Trim HR Verbose

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Add compaction instructions block** (ก่อน `## Context Management`)

เพิ่มหลัง line สุดท้ายของ `## Efficiency` section:

```markdown
## Compact Instructions

When compacting, **preserve**: issue keys created/modified · pending HR5/HR6 operations · active skill phase name · sprint IDs · QG scores.
**Discard**: verbose tool output · intermediate search results · exploration steps · full ADF bodies already written.
```

- [ ] **Step 2: ย่อ HR Rules block** — แทน `<important if="...">` block ทุก rule ด้วย compact table:

แทนที่ทั้ง `### HARD RULES` section (HR1–HR10 `<important>` blocks) ด้วย:

```markdown
### HARD RULES (hooks enforce HR2–HR10 automatically)

| Rule | Trigger | Action |
|------|---------|--------|
| **HR1** QG ≥ 90% | Before any Jira write | `uv run scripts/api/validate_adf.py {file} --json` must score ≥ 90 |
| **HR2** JQL ORDER BY | `parent =` / `key in` JQL | NEVER add `ORDER BY` — parser error |
| **HR3** Assignee | Assign to team member | `acli jira workitem assign -k "KEY" -a "email" -y` only |
| **HR4** Confluence macros | ToC/Children/Code blocks | `update_page_storage.py` only — MCP corrupts XML |
| **HR5** Subtask parent | Create subtask | MCP create → verify `parent.key` via `jira_get_issue` → acli edit if orphan |
| **HR6** Cache invalidate | Any MCP write | `cache_invalidate(issue_key)` after every write. Use `auto_refresh=true`. |
| **HR7** Sprint ID | Set `{{SPRINT_FIELD}}` | Never hardcode — `jira_get_sprints_from_board()` always |
| **HR8** Subtask dates | Create/update subtask | Dates within parent range. SP sum ≈ parent. |
| **HR9** Desc alignment | Create/update any issue | Story ACs → subtask objectives. Run `verify-issue --with-subtasks`. |
| **HR10** Subtask sprint | Create subtask | NEVER set `{{SPRINT_FIELD}}` on subtasks — inherited from parent. |

Full definitions: `references/hr-rules.md`
```

- [ ] **Step 3: Commit**
```bash
git add CLAUDE.md
git commit -m "perf(claude-md): compact HR rules table + add compaction instructions"
```

---

## Task 3: post_filter_mcp_response.py — Description Truncation for Search

**Files:**
- Modify: `hooks/plugin/session/post_filter_mcp_response.py`

**Goal:** เมื่อ `jira_search` คืน issues หลายตัว ให้ truncate/remove ADF description body (ซึ่งเป็น nested object ใหญ่) เพราะ list view ไม่ต้องการ full description

- [ ] **Step 1: เพิ่ม constant และ function ใน `_clean_fields()`**

เพิ่มหลัง `_PROJECT_NOISE` constant:

```python
# Max chars to keep from description text in search results (list mode)
# Full ADF description objects can be 2,000–8,000 bytes per issue
_MAX_DESC_SEARCH_CHARS = 300
```

เพิ่ม helper function หลัง `_clean_project()`:

```python
def _truncate_description_for_search(desc: object) -> object:
    """Replace full ADF description object with a short text summary for list views."""
    if desc is None:
        return None
    if isinstance(desc, dict):
        # ADF object — extract first text nodes only
        def _extract_text(node: object, limit: int = _MAX_DESC_SEARCH_CHARS) -> str:
            if not isinstance(node, dict):
                return ""
            if node.get("type") == "text":
                return node.get("text", "")
            parts = []
            total = 0
            for child in node.get("content", []):
                text = _extract_text(child, limit - total)
                parts.append(text)
                total += len(text)
                if total >= limit:
                    break
            return "".join(parts)
        text = _extract_text(desc).strip()[:_MAX_DESC_SEARCH_CHARS]
        if not text:
            return None  # drop entirely if no text extractable
        return {"_summary": text + ("…" if len(text) == _MAX_DESC_SEARCH_CHARS else "")}
    if isinstance(desc, str):
        return desc[:_MAX_DESC_SEARCH_CHARS] + ("…" if len(desc) > _MAX_DESC_SEARCH_CHARS else "")
    return None
```

- [ ] **Step 2: Apply truncation in `_clean_fields()` for search mode**

เปลี่ยน signature และเพิ่ม `is_search` param:

```python
def _clean_fields(fields: dict, is_search: bool = False) -> dict:
    result = {k: v for k, v in fields.items() if k not in _FIELD_NOISE}
    # ... (existing person/status/issuetype/priority/project cleaners unchanged) ...
    # Add at end of function:
    if is_search and "description" in result:
        result["description"] = _truncate_description_for_search(result["description"])
        if result["description"] is None:
            del result["description"]
    return result
```

- [ ] **Step 3: Pass `is_search` flag down the call chain**

เปลี่ยน `_clean_issue()`:

```python
def _clean_issue(issue: object, is_search: bool = False) -> object:
    if not isinstance(issue, dict):
        return issue
    result = {k: v for k, v in issue.items() if k not in _TOP_NOISE}
    if isinstance(result.get("fields"), dict):
        result["fields"] = _clean_fields(result["fields"], is_search=is_search)
    return result
```

เปลี่ยน main() search branch:

```python
elif is_search and isinstance(response, dict) and "issues" in response:
    filtered = {
        k: ([_clean_issue(i, is_search=True) for i in v] if k == "issues" else v)
        for k, v in response.items()
        if k not in {"expand", "warningMessages"}
    }
```

- [ ] **Step 4: Commit**
```bash
git add hooks/plugin/session/post_filter_mcp_response.py
git commit -m "perf(hooks): truncate ADF description in search results — saves 2-8K tokens/search"
```

---

## Task 4–7: Parallel Compression (References + Skills)

> **🟢 PARALLEL** — Tasks 4, 5, 6, 7 ไม่มี dependency ต่อกัน dispatch พร้อมกัน

### Task 4: Compress references/templates-subtask.md

**Target:** 15,128 → ~6,000 bytes

**File:** `references/templates-subtask.md`

- [ ] Read file ทั้งหมด
- [ ] ลบ ADF JSON full examples ที่ซ้ำกับ `references/templates-core.md`
- [ ] เหลือเฉพาะ subtask-specific fields + 1 minimal example per type (BE/FE/QA)
- [ ] ย่อ field explanations เป็น table แทน paragraph
- [ ] Commit: `perf(refs): compress templates-subtask.md ~60%`

### Task 5: Compress references/vertical-slice-guide.md

**Target:** 8,961 → ~3,500 bytes

**File:** `references/vertical-slice-guide.md`

- [ ] Read file ทั้งหมด
- [ ] เหลือเฉพาะ: VS label definitions, sizing rules, checklist (compact)
- [ ] ลบ rationale/background sections
- [ ] Commit: `perf(refs): compress vertical-slice-guide.md ~60%`

### Task 6: Compress references/templates-vibe.md

**Target:** 9,972 → ~4,500 bytes

**File:** `references/templates-vibe.md`

- [ ] Read file ทั้งหมด
- [ ] ลบ content ที่ overlap กับ templates-core.md
- [ ] เหลือเฉพาะ vibe-specific patterns (AI-Ready subtasks, 2-phase structure)
- [ ] Commit: `perf(refs): compress templates-vibe.md ~55%`

### Task 7: Compress skills/story/create-story/SKILL.md

**Target:** 37,092 → ~14,000 bytes — ใหญ่ที่สุด ใช้ Universal Compression Rules

**File:** `skills/story/create-story/SKILL.md`

- [ ] Read file ทั้งหมด
- [ ] Apply Universal Compression Rules
- [ ] คงไว้: Gate markers, Phase numbering, Context Object table, HR references, MCP field lists
- [ ] ย่อ Blueprint Handoff Check (verbose 3-step → concise rules)
- [ ] Commit: `perf(skills): compress create-story SKILL.md ~60%`

---

## Task 8–10: Parallel Compression (More Skills)

> **🟢 PARALLEL** — Tasks 8, 9, 10 ไม่มี dependency ต่อกัน

### Task 8: Compress skills/sprint/plan-sprint/SKILL.md

**Target:** 22,634 → ~10,000 bytes

- [ ] Read file ทั้งหมด, apply Universal Compression Rules
- [ ] Commit: `perf(skills): compress plan-sprint SKILL.md ~55%`

### Task 9: Compress skills/epic/blueprint/SKILL.md

**Target:** 20,824 → ~9,000 bytes

- [ ] Read file ทั้งหมด, apply Universal Compression Rules
- [ ] Commit: `perf(skills): compress blueprint SKILL.md ~55%`

### Task 10: Compress skills/story/analyze-story/SKILL.md

**Target:** 16,801 → ~8,000 bytes

- [ ] Read file ทั้งหมด, apply Universal Compression Rules
- [ ] Commit: `perf(skills): compress analyze-story SKILL.md ~50%`

---

## Task 11: Version Bump + Summary Commit

- [ ] `./scripts/bump-version.sh <next-version>` — bumps marketplace.json + README badge
- [ ] Final commit message: `perf: token optimization — skill/ref compression + model routing (~60% context reduction)`
