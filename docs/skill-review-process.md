# Skill Review Process

## Overview

All atlassian-pm skills must pass quality review before deployment. This document defines the review process using the skill-reviewer agent.

## When to Review

- **New skill creation** - Before merging to main
- **Significant changes** - When modifying description, triggers, or core workflow
- **Periodic audit** - Quarterly review of all skills for consistency

## Review Criteria

### 1. Description Quality (Score: 1-10)

- ✅ Uses third person ("This skill should be used when...")
- ✅ Includes specific trigger phrases
- ✅ Lists concrete scenarios
- ❌ Not vague or generic
- ❌ Not second person ("You should...")

### 2. Content Organization (Score: 1-10)

- ✅ SKILL.md lean (ideal: 1,500-2,000 words, max 5,000)
- ✅ Progressive disclosure (core in SKILL.md, details in references/)
- ✅ Clear phase structure
- ❌ All content in one file
- ❌ Missing references for detailed content

### 3. Writing Style (Score: 1-10)

- ✅ Imperative/infinitive form ("Fetch", "Create", "Output")
- ❌ Second person ("You should", "You need to")
- ❌ Passive voice ("The issue should be created")

### 4. Examples & References (Score: 1-10)

- ✅ Working code examples
- ✅ Complete input/output examples
- ✅ References exist and are valid
- ❌ Broken links
- ❌ Incomplete examples

### 5. Trigger Accuracy (Score: 1-10)

- ✅ Triggers on expected user queries
- ✅ Includes Thai variants (if applicable)
- ✅ Has "Do NOT use for" section
- ❌ Missing common trigger phrases
- ❌ Competing skills overlap

## Minimum Passing Score

- **Overall: ≥ 7/10**
- **Description: ≥ 6/10** (critical for skill invocation)
- **No critical issues** (broken references, missing files)

## Review Process

### Step 1: Invoke skill-reviewer Agent

```bash
# Single skill
Agent(name: "skill-reviewer", prompt: "Review skills/task/create-task/SKILL.md")

# Multiple skills (batch)
Agent(name: "skill-reviewer", prompt: "Review skills/epic/create-epic/SKILL.md, skills/epic/vibe-plan/SKILL.md")
```

### Step 2: Review Output

The agent returns:

- Quality score (1-10) per criterion
- Critical/Major/Minor issues
- Actionable recommendations
- File locations for fixes

### Step 3: Fix Issues

- **Critical**: Must fix before merge
- **Major**: Should fix in same PR
- **Minor**: Can fix in follow-up

### Step 4: Re-review

After fixes, re-run skill-reviewer to verify:

- Score ≥ 7/10
- No critical issues remaining

## Common Issues & Fixes

### Issue: Description not third person

```yaml
# ❌ Bad
description: "Create a new Jira Task — vibe mode by default"

# ✅ Good
description: |
  This skill creates a new Jira Task in vibe mode (fast, auto-detect type) by default.
```

### Issue: Missing trigger phrases

```yaml
# ❌ Bad
Triggers: "create task", "new task"

# ✅ Good
Triggers: "create task", "new task", "add task", "create a task", "สร้าง task", "create spike", "create bug task"
```

### Issue: SKILL.md too long

```
# ❌ Bad
SKILL.md: 8,000 words - everything in one file

# ✅ Good
SKILL.md: 1,800 words
references/advanced.md: 2,500 words
references/examples.md: 1,500 words
```

### Issue: Missing domain-expert.md

```
# ❌ Bad
SKILL.md references domain-expert.md but file doesn't exist

# ✅ Good
Create domain-expert.md with:
- Why This Approach
- Industry Frameworks Used
- Key Metrics
- Expert Decision Criteria
- Common Failure Modes
- Authoritative References
```

## CI/CD Integration

Pre-commit hook runs skill-reviewer on modified SKILL.md files:

```bash
# .githooks/pre-commit
#!/bin/bash
changed_skills=$(git diff --cached --name-only | grep 'SKILL.md$')
if [ -n "$changed_skills" ]; then
  echo "Running skill-reviewer on modified skills..."
  # Integration with skill-reviewer agent
fi
```

## Review Checklist

Before marking skill as reviewed:

- [ ] Description uses third person
- [ ] All trigger phrases tested
- [ ] SKILL.md under 3,000 words
- [ ] references/ files exist
- [ ] Examples complete and working
- [ ] No second person anywhere
- [ ] "Do NOT use for" section present
- [ ] Score ≥ 7/10 from skill-reviewer

## Quarterly Audit

Every quarter, run full skill audit:

```bash
# Review all skills
for skill in skills/*/SKILL.md skills/*/*/SKILL.md; do
  Agent(name: "skill-reviewer", prompt: "Review $skill")
done
```

Generate report:

- Average score per skill category
- Skills below 7/10
- Common issues across skills
- Improvement trends

## Memory Record

After completing skill review, save to memory:

```markdown
---
name: skill-review-[YYYY-MM-DD]
description: Skill review audit for [date]
type: project
---

**Date:** [YYYY-MM-DD]
**Skills Reviewed:** [N]
**Average Score:** [X/10]
**Critical Issues:** [N]
**Major Issues:** [N]

**Top Issues:**
1. [Issue category] - [count] skills affected
2. [Issue category] - [count] skills affected

**Fixed:**
- [List of fixed issues]

**Follow-up Required:**
- [List of minor issues deferred]
```
