# Script Reference

> Details for all scripts in `atlassian-scripts/scripts/`
>
> For overview and script selection guide, see [SKILL.md](SKILL.md)

---

## Script 1: Create/Update Page

Create or update a Confluence page with proper code block formatting.

**Location:** `.claude/skills/atlassian-scripts/scripts/create_confluence_page.py`

### Usage

```bash
# Create new page
python3 .claude/skills/atlassian-scripts/scripts/create_confluence_page.py \
  --space BEP --title "Technical Spec: Feature X" --content-file content.md

# Create as child page
# Add: --parent-id 123456789

# Update existing page
python3 .claude/skills/atlassian-scripts/scripts/create_confluence_page.py \
  --page-id 123456789 --content-file updated-content.md

# Options: --content "inline" | --dry-run | --verbose
```

### Arguments

| Argument | Mode | Required | Description |
| --- | --- | --- | --- |
| `--space` | Create | ✅ | Space key (e.g., BEP) |
| `--title` | Create | ✅ | Page title |
| `--parent-id` | Create | ❌ | Parent page ID |
| `--page-id` | Update | ✅ | Page ID to update |
| `--content` | Both | ✅* | Inline markdown content |
| `--content-file` | Both | ✅* | Path to markdown file |
| `--dry-run` | Both | ❌ | Preview without saving |
| `--verbose` | Both | ❌ | Enable debug logging |

*Must specify either `--content` or `--content-file`.

### Supported Markdown

| Element | Syntax | Supported |
| --- | --- | --- |
| Headings | `# ## ###` | ✅ |
| Bold | `**text**` | ✅ |
| Italic | `*text*` | ✅ |
| Code blocks | ` ```lang ` | ✅ (as ac:structured-macro) |
| Inline code | `` `code` `` | ✅ |
| Links | `[text](url)` | ✅ |
| Lists | `- item` | ✅ |
| Tables | `\| col \|` | ✅ |
| Blockquotes | `> quote` | ✅ |
| HR | `---` | ✅ |

---

## Script 2: Find/Replace

Generic script for find/replace content in Confluence pages.

**Location:** `.claude/skills/atlassian-scripts/scripts/update_confluence_page.py`

### Usage

```bash
python3 .claude/skills/atlassian-scripts/scripts/update_confluence_page.py \
  --page-id 111222333 --find "old" --replace "new"

# Multiple: repeat --find/--replace pairs | --regex | --dry-run | --verbose
```

### Arguments

| Argument | Required | Description |
| --- | --- | --- |
| `--page-id` | ✅ | Confluence page ID |
| `--find` | ✅ | Text to find (repeatable) |
| `--replace` | ✅ | Replacement (must match --find count) |
| `--regex` | ❌ | Regex mode |
| `--dry-run` | ❌ | Preview only |

---

## Script 3: Move Page

Move page(s) under a different parent page without modifying content.

**Location:** `.claude/skills/atlassian-scripts/scripts/move_confluence_page.py`

### Usage

```bash
python3 .claude/skills/atlassian-scripts/scripts/move_confluence_page.py \
  --page-id 123456789 --parent-id 987654321

# Batch: --page-ids 123,456,789 | --dry-run | --verbose
```

| Argument | Required | Description |
| --- | --- | --- |
| `--page-id` / `--page-ids` | ✅ | Single or comma-separated page IDs |
| `--parent-id` | ✅ | Target parent page ID |

> **Why:** MCP can't move pages without overwriting content. Uses `PUT /rest/api/content/{pageId}/move/append/{parentId}`

---

## Script 4: Update with Storage Format

Update a page with raw storage format for macros (ToC, Children, Status).

**Location:** `.claude/skills/atlassian-scripts/scripts/update_page_storage.py`

### Usage

```bash
python3 .claude/skills/atlassian-scripts/scripts/update_page_storage.py \
  --page-id 222333444 --content-file content.html

# Options: --content "inline" | --title "New Title" | --dry-run | --verbose
```

### Common Macros

| Macro | Storage Format |
| --- | --- |
| Table of Contents | `<ac:structured-macro ac:name="toc"><ac:parameter ac:name="maxLevel">2</ac:parameter></ac:structured-macro>` |
| Children Display | `<ac:structured-macro ac:name="children"><ac:parameter ac:name="all">true</ac:parameter><ac:parameter ac:name="sort">title</ac:parameter></ac:structured-macro>` |
| Status | `<ac:structured-macro ac:name="status"><ac:parameter ac:name="colour">Green</ac:parameter><ac:parameter ac:name="title">Complete</ac:parameter></ac:structured-macro>` |
| Info Panel | `<ac:structured-macro ac:name="info"><ac:rich-text-body><p>Info text</p></ac:rich-text-body></ac:structured-macro>` |
| Warning Panel | `<ac:structured-macro ac:name="warning"><ac:rich-text-body><p>Warning text</p></ac:rich-text-body></ac:structured-macro>` |

### Why Use This Script

MCP tools do not convert storage format correctly -- macros will render as plain text instead.
This script sends raw storage format directly to the API.

---

## Script 5: Fix Code Blocks

Fix code blocks from `<pre class="highlight"><code>` to `<ac:structured-macro ac:name="code">`.

**Location:** `.claude/skills/atlassian-scripts/scripts/fix_confluence_code_blocks.py`

### Usage

```bash
python3 .claude/skills/atlassian-scripts/scripts/fix_confluence_code_blocks.py \
  --page-id 123456789
# Batch: --page-ids 123,456,789 | --dry-run | --verbose
```

Converts `<pre class="highlight"><code>` → `<ac:structured-macro ac:name="code">` via REST API.

---

## Script 6: Audit Pages

Verify content across multiple Confluence pages for presence/absence of specified strings.

**Location:** `.claude/skills/atlassian-scripts/scripts/audit_confluence_pages.py`

### Usage

```bash
# Single page
python3 .claude/skills/atlassian-scripts/scripts/audit_confluence_pages.py \
  --page-id 987654321 --should-have "BEP-2883" --should-not-have "2025-01-21"

# Batch from JSON config
python3 .claude/skills/atlassian-scripts/scripts/audit_confluence_pages.py --config audit.json
```

Config: `[{"page_id":"123","label":"Name","should_have":["X"],"should_not_have":["Y"]}]`

| Argument | Description |
| --- | --- |
| `--config` / `--page-id` | JSON config or single page (one required) |
| `--should-have` / `--should-not-have` | Presence/absence checks (with --page-id) |
| `--label`, `--verbose` | Display label, debug logging |

---

## Script 7: Update Jira Description

Fix Jira issue descriptions via REST API v3 (ADF format) directly.
Preserves all formatting (panels, tables, marks, code blocks).

**Location:** `.claude/skills/atlassian-scripts/scripts/update_jira_description.py`

### Usage

```bash
# Single issue
python3 .claude/skills/atlassian-scripts/scripts/update_jira_description.py \
  --issue BEP-2819 --find "old" --replace "new"

# Batch: --config fixes.json | --dry-run | --verbose
```

Config: `{"BEP-2819": [["old","new"]], "BEP-2755": [["old1","new1"],["old2","new2"]]}`

| Argument | Description |
| --- | --- |
| `--config` / `--issue` | JSON config or single issue key (one required) |
| `--find`, `--replace` | Text pairs (repeatable, with --issue) |

**How:** GET ADF via REST v3 → walk tree → replace text nodes → PUT back. Preserves all formatting (panels, tables, marks).

**vs MCP:** MCP converts to wiki markup (loses formatting). `acli` replaces entire description. This script does **surgical text-only edits**.

---

---

## Script 8: Validate ADF (HR1 Enforcement)

Validate ADF JSON against quality gate before writing to Jira. Enforces HR1 (QG ≥ 90% before writes).

**Location:** `.claude/skills/atlassian-scripts/scripts/validate_adf.py`

### Usage

```bash
# Validate story ADF
python3 .claude/skills/atlassian-scripts/scripts/validate_adf.py \
  tasks/story.json --type story

# Auto-fix + re-validate → writes -fixed.json
python3 .claude/skills/atlassian-scripts/scripts/validate_adf.py \
  tasks/story.json --type story --fix

# JSON output (for piping)
python3 .claude/skills/atlassian-scripts/scripts/validate_adf.py \
  tasks/story.json --type story --json

# Options: --verbose (show all checks) | --summary-only
```

### Arguments

| Argument | Required | Description |
| --- | --- | --- |
| `file` | ✅ | Path to ADF JSON file (CREATE, EDIT, or raw ADF) |
| `--type` / `-t` | ✅ | Issue type: `story`, `subtask`, `epic`, `qa` |
| `--fix` | ❌ | Auto-fix and write to `-fixed.json` |
| `--json` | ❌ | JSON output only |
| `--verbose` / `-v` | ❌ | Show all checks (not just failures) |
| `--summary-only` | ❌ | Score only, no details |

### Quality Checks

| Type | Checks | Max Points |
| --- | --- | --- |
| All types | T1-T5 (ADF structure, panels, code marks, headings, links) | 5 |
| Story | S1-S6 (INVEST, narrative, anti-patterns, AC, scope, language) | 6 |
| Subtask | ST1-ST5 (objective, scope/files, AC, tag, language) | 5 |
| Epic | E1-E4 (vision, RICE, scope, stories) | 4 |
| QA | QA1-QA5 (coverage, format, scenarios, data, language) | 5 |

**Scoring:** pass=1, warn=0.5, fail=0. Overall ≥ 90% = pass.

**Exit codes:** 0=pass, 1=fail, 2=error

---

## Script 9: Verify Write (HR3/HR5/HR6 Enforcement)

Post-write verifier — reads back from Jira API to confirm writes took effect.

**Location:** `.claude/skills/atlassian-scripts/scripts/verify_write.py`

### Usage

```bash
# Verify parent link
python3 .claude/skills/atlassian-scripts/scripts/verify_write.py \
  BEP-1234 --check parent --expected-parent BEP-1200

# Verify assignee
python3 .claude/skills/atlassian-scripts/scripts/verify_write.py \
  BEP-1234 --check assignee

# Multiple issues + checks
python3 .claude/skills/atlassian-scripts/scripts/verify_write.py \
  BEP-1234 BEP-1235 --check parent,assignee,description

# JSON output
python3 .claude/skills/atlassian-scripts/scripts/verify_write.py \
  BEP-1234 --check parent --json
```

### Arguments

| Argument | Required | Description |
| --- | --- | --- |
| `issues` | ✅ | One or more issue keys |
| `--check` / `-c` | ✅ | Comma-separated: `parent`, `assignee`, `description` |
| `--expected-parent` | ❌ | Expected parent key (for parent check) |
| `--json` | ❌ | JSON output only |
| `--verbose` / `-v` | ❌ | Show actions needed |

### Checks

| Check | Verifies | HR |
| --- | --- | --- |
| `parent` | Parent link set + matches expected | HR5 |
| `assignee` | Assignee field populated | HR3 |
| `description` | ADF description exists with content | — |

Always reports `cache_invalidate` actions needed (HR6).

**Exit codes:** 0=all pass, 1=some fail, 2=error

---

## Script 10: Jira Write Wrapper (HR1/HR3/HR5/HR6)

Unified write pipeline with all HARD RULES enforced at every step.

**Location:** `.claude/skills/atlassian-scripts/scripts/jira_write.py`

### Usage

```bash
# Create subtask (full 5-step pipeline)
python3 .claude/skills/atlassian-scripts/scripts/jira_write.py create-subtask \
  --parent BEP-1200 --adf tasks/sub.json --assignee user@email.com

# Update description only
python3 .claude/skills/atlassian-scripts/scripts/jira_write.py update-description \
  --issue BEP-1234 --adf tasks/fixed.json --type story

# Dry run (validate only, no writes)
python3 .claude/skills/atlassian-scripts/scripts/jira_write.py create-subtask \
  --parent BEP-1200 --adf tasks/sub.json --dry-run
```

### Subcommands

**`create-subtask`** — 5-step pipeline:

1. Validate ADF (HR1: QG ≥ 90%)
2. REST create subtask shell (with parent)
3. Verify parent link (HR5)
4. Update description via acli (ADF)
5. Assign via acli (HR3)

| Argument | Required | Description |
| --- | --- | --- |
| `--parent` | ✅ | Parent story key |
| `--adf` | ✅ | Path to ADF JSON file |
| `--assignee` | ❌ | Assignee email (acli) |
| `--dry-run` | ❌ | Validate only |

**`update-description`** — 3-step pipeline:

1. Validate ADF (HR1)
2. Update via acli
3. Report cache_invalidate (HR6)

| Argument | Required | Description |
| --- | --- | --- |
| `--issue` | ✅ | Issue key |
| `--adf` | ✅ | Path to ADF JSON file |
| `--type` / `-t` | ❌ | Issue type for validation (default: subtask) |
| `--dry-run` | ❌ | Validate only |

**Exit codes:** 0=success, 1=validation/write failed, 2=error

---

## Script 11: Workflow Checkpoint

Track workflow phases and enforce prerequisites across multi-step skill workflows.

**Location:** `.claude/skills/atlassian-scripts/scripts/workflow_checkpoint.py`

### Usage

```bash
# Start workflow
python3 .claude/skills/atlassian-scripts/scripts/workflow_checkpoint.py \
  start story-full BEP-1200

# Record quality gate pass
python3 .claude/skills/atlassian-scripts/scripts/workflow_checkpoint.py \
  pass-gate qg-story 94

# Advance to next phase
python3 .claude/skills/atlassian-scripts/scripts/workflow_checkpoint.py \
  advance create-story

# Check prerequisite (exit code 0=met, 1=not met)
python3 .claude/skills/atlassian-scripts/scripts/workflow_checkpoint.py \
  check qg-story

# Show current status
python3 .claude/skills/atlassian-scripts/scripts/workflow_checkpoint.py status

# Complete workflow
python3 .claude/skills/atlassian-scripts/scripts/workflow_checkpoint.py complete

# Cleanup stale state (>24h)
python3 .claude/skills/atlassian-scripts/scripts/workflow_checkpoint.py cleanup
```

### Commands

| Command | Description |
| --- | --- |
| `start <workflow> <context>` | Start new workflow (e.g., `story-full BEP-1200`) |
| `pass-gate <gate> <score>` | Record gate pass with score |
| `advance <phase>` | Mark phase as completed, advance to next |
| `check <gate>` | Check if prerequisite met (exit code) |
| `status` | Show current workflow state |
| `complete` | Mark workflow as completed |
| `cleanup` | Remove stale state files (>24h TTL) |

State persists in `tasks/.workflow-state.json`. Auto-clears after 24h.

**Exit codes:** 0=success/met, 1=not met/failed, 2=error

---

## Script Selection Guide

```text
What do you need to do?
    │
    ├─ Create a new page
    │     └─ create_confluence_page.py --space --title
    │
    ├─ Update entire content
    │     └─ create_confluence_page.py --page-id --content-file
    │
    ├─ Find/Replace text
    │     └─ update_confluence_page.py --find --replace
    │
    ├─ Move page(s) to new parent
    │     └─ move_confluence_page.py --page-id(s) --parent-id
    │
    ├─ Add macros (ToC, Children, Status)
    │     └─ update_page_storage.py --page-id --content-file
    │
    ├─ Fix broken code blocks
    │     └─ fix_confluence_code_blocks.py --page-id(s)
    │
    ├─ Verify content alignment
    │     └─ audit_confluence_pages.py --config audit.json
    │
    ├─ Fix Jira issue descriptions (ADF)
    │     └─ update_jira_description.py --config fixes.json
    │
    ├─ Validate ADF before Jira write (HR1)
    │     └─ validate_adf.py tasks/story.json --type story [--fix]
    │
    ├─ Verify writes took effect (HR3/HR5/HR6)
    │     └─ verify_write.py BEP-1234 --check parent,assignee
    │
    ├─ Create subtask (full pipeline)
    │     └─ jira_write.py create-subtask --parent BEP-1200 --adf tasks/sub.json
    │
    └─ Track workflow state
          └─ workflow_checkpoint.py start story-full BEP-1200
```
