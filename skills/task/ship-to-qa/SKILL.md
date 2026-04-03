---
name: ship-to-qa
context: fork
agent: general-purpose
x-compatibility: [atlassian-cache, mcp-atlassian]
argument-hint: "[issue-key]"
effort: medium
allowed-tools: Read, Bash, mcp__mcp-atlassian__jira_get_issue, mcp__mcp-atlassian__jira_get_transitions, mcp__mcp-atlassian__jira_transition_issue, mcp__mcp-atlassian__jira_add_comment, mcp__plugin_atlassian-pm_atlassian-cache__cache_get_issue, mcp__plugin_atlassian-pm_atlassian-cache__cache_invalidate
description: |
  Bundle: post PR + preview URLs to Jira + transition to Ready for QA in one command.
  Auto-detects PR from current branch. Constructs CF Pages URLs from project-config.json.

  Triggers: "ship to qa", "ready for qa", "send to qa", "ส่ง qa", "ship {{PROJECT_KEY}}-XXX", "ready for qa review"
  Use when: after PR is open — adds PR link + preview URLs to Jira comment and transitions ticket
  Do NOT use for: merging (use superpowers:finishing-a-development-branch); post-merge sync (use pr-review-jira-sync); asking if code is ready for peer review (that is not a QA handoff)
---

# /ship-to-qa

**Role:** Developer shipping work for QA review
**Output:** Jira comment (PR + preview URLs) + ticket transitioned to Ready for QA

## Dynamic Context

- **Config:** @.claude/project-config.json → `environments.preview`, `environments.staging`
- **Note:** `board.columns` is consumed by the WIP gate hook automatically — the skill does not query it directly

## Steps

**Step 1A — Fetch (parallel)**

> **PARALLEL** — run these simultaneously:

1. Try `cache_get_issue` first; on cache miss or stale data, call `jira_get_issue` with fields: `summary,status,labels`
2. `Bash: gh pr view --json url,number,headRefName`

If `gh pr view` fails (no PR found): stop and ask user "Could not auto-detect PR. Please provide PR URL and number:"

**Step 1B — Guard**

Check current status from `jira_get_issue` result:

- status = "In Progress" → proceed
- status ≠ "In Progress" → warn: "currently {status} — expected In Progress before shipping to QA. Continue? (y/n)"

**Step 2 — Build Preview URLs**

1. Read @.claude/project-config.json → `environments.preview`
2. Get branch name from `gh pr view` result (`headRefName`)
3. Build slug: replace `/` → `-`, replace `_` → `-`, lowercase
4. If slug length > 28: truncate to 28 chars, note "CF Pages slug truncated to 28 chars"
5. For each service key in `environments.preview`, construct:
   `https://{slug}.{preview[service]}.pages.dev`

If `environments.preview` is missing from config: warn "environments.preview not found in project-config.json" and ask user for URLs manually. Continue to Step 4 without preview lines if user cannot provide.

**Step 3 — Hybrid URL Selection**

Labels are service tags (`be`, `fe-admin`, `fe-web`, `video`, `player`, `ai-agent`). Multiple labels allowed.

| Condition | Preview URLs | Staging BE |
|-----------|-------------|-----------|
| Has `be` label | All services from `environments.preview` | `environments.staging.api` |
| No `be` label | All services from `environments.preview` | Hidden |
| _(no labels)_ | All services from `environments.preview` | `environments.staging.api` (safe default) |

**Step 4 — Post Jira Comment**

Call `jira_add_comment` with plain text body (no ADF wrapper needed):

```
[ship-to-qa] {issue_key} — {summary}

PR: #{pr_number} — {pr_url}
Preview ({service_key}): {preview_url}   ← one line per service in environments.preview
Staging (BE): {staging_api_url}
```

**Example:**

```
[ship-to-qa] {{PROJECT_KEY}}-42 — Add video upload feature

PR: #157 — https://github.com/org/repo/pull/157
Preview (be): https://feat-video-upload.be.tathep.pages.dev
Preview (fe-admin): https://feat-video-upload.fe-admin.tathep.pages.dev
Staging (BE): https://staging-api.tathep.com
```

Omit lines that don't apply: no "Staging (BE)" line when no `be` label; omit preview lines if config was missing and user couldn't provide URLs.

**Step 5 — WIP Check + Transition**

1. Call `jira_get_transitions` → find transition named "Ready for QA" (case-insensitive; also check "QA"). If not found: show available transitions and ask user to pick
2. Call `jira_transition_issue` passing the transition **name** (not numeric ID) using the `transition` field — the `pre_wip_limit_check` hook will **automatically block** if QA column WIP limit is reached
3. If blocked by hook:
   - Run the JQL the hook provides
   - Count results
   - If count < wip_max: run `export CLAUDE_WIP_CONFIRMED={issue_key}:{col_name}` where `{col_name}` is the column name from the hook's block message, then retry `jira_transition_issue`
   - If count >= wip_max: **STOP** — "QA WIP limit reached ({count}/{wip_max}). Wait for QA to finish an item first."

**Step 6 — HR6**

`cache_invalidate(issue_key="{issue_key}")`

**Step 7 — Output**

```
{issue_key} -> Ready for QA [OK]

Comment posted:
  PR: #{number} — {url}
  Preview: {comma-joined service URLs}
  Staging (BE): {staging_url}  ← only if applicable

Card moved to Ready for QA.
```

## Edge Cases

| Situation | Handling |
|-----------|---------|
| `gh pr view` fails | Ask for PR URL + number before posting comment |
| `environments.preview` missing in config | Warn + ask for URLs manually; still transition if user confirms |
| "Ready for QA" transition not found | Show available transitions, ask user to pick |
| QA WIP limit reached | Stop — report count/limit, do not transition |
| Slug > 28 chars | Truncate; add note in output |
| status ≠ In Progress | Warn + confirm before proceeding |

## Examples

### ✅ Good

```text
/ship-to-qa {{PROJECT_KEY}}-42                           # post PR + preview URLs + transition
/ship-to-qa {{PROJECT_KEY}}-42 --env production          # use production preview URLs (if configured)
```

### ❌ Bad

```text
/ship-to-qa                                 # no issue key — cannot fetch issue or detect PR
/ship-to-qa {{PROJECT_KEY}}-42 --branch                  # --branch is not valid; branch auto-detected from PR
/ship-to-qa {{PROJECT_KEY}}-42 --force                   # --force is not valid; WIP gate requires explicit override
```

**Common mistakes:**

- Running without a PR open — `gh pr view` will fail; open PR first or provide URL manually
- Running when QA column is at WIP limit — transition blocked; wait for QA to finish an item
- Forgetting `be` label on BE tasks — Staging URL hidden; add `be` label before shipping

## Domain Expert Notes

Bundling the comment + transition eliminates two failure modes common in team workflows: (1) PR opened but Jira card never moves — QA doesn't know to pick it up; (2) Card moved but no preview URL — QA has nowhere to test. This skill makes both atomic.

Preview URL construction follows Cloudflare Pages' branch alias format: the branch name is slugified (replace `/` and `_` with `-`, lowercase, truncate at 28 chars) and used as the subdomain prefix against the CF Pages project domain stored in `environments.preview`.

The WIP gate enforces flow efficiency: QA column overflow causes context switching overhead and degrades cycle time for the entire board (Anderson, _Kanban_, 2010).

## References

- [HR Rules](../../../references/hr-rules.md) — HR6: cache_invalidate after every Jira write
- [WIP Gate](../../../hooks/plugin/guards/pre_wip_limit_check.py) — Hard WIP enforcement via CLAUDE_WIP_CONFIRMED env var
- [project-config template](../../../.claude/project-config.json.template) — `environments.preview` schema
