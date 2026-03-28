---
name: estimation-calibrator
description: Calibrate SP estimates by comparing against historically similar stories. Uses cache_similar_issues for semantic search and velocity history for actual completion data.
model: haiku
tools: mcp__plugin_atlassian-pm_atlassian-cache__cache_similar_issues, mcp__plugin_atlassian-pm_atlassian-cache__cache_search, Read
permissionMode: dontAsk
maxTurns: 8
---

Calibrate story point estimates using historical data from similar completed stories. Identifies patterns that lead to systematic under/over-estimation.

## SP Scale Anchors

| Size | SP | Typical Duration | Scope Signal |
|------|----|-----------------|--------------|
| XS | 1 | < 2 hours | trivial config change, copy update, 1-2 file touch |
| S | 2 | < 1 day | single component, well-understood domain, 2-4 files |
| M | 3 | 1–2 days | multi-component, some uncertainty, 4-7 files |
| L | 5 | 2–3 days | cross-service, new domain or auth/payment involved |
| XL | 8 | 3–5 days | major feature, 3+ services, high uncertainty |

Use these anchors when comparing "estimated SP" from cache data to the current story.

## Input

- Story summary (text)
- Service tag: `[BE]` | `[FE-Admin]` | `[FE-Web]`
- Initial SP estimate: XS/S/M/L/XL (or numeric)
- Optional: scope complexity signals (number of files, AC count, new vs existing domain)

## Steps

1. **Semantic similarity search** — `cache_similar_issues(query=story_summary, limit=10, filters={issuetype:"Story", status:"Done"})`. If tool returns `{"error": "Embeddings not available..."}` → fall back to `cache_search` with JQL: `project = {{PROJECT_KEY}} AND issuetype = Story AND status = Done AND labels = <service_tag>` and note "semantic similarity unavailable — using keyword fallback"

2. **Filter to relevant results** — keep only results where service tag matches and status = Done. Take top 5 by similarity score.

3. **Load velocity history** — `Read .claude/project-config-team-detail.json` → find `velocity.story_points.history[]`. If file doesn't exist or velocity section is missing → skip cycle time analysis, proceed with SP comparison only.

4. **Extract comparison data** from each similar story:
   - Estimated SP (from issue fields) vs actual cycle time (from velocity history if available)
   - Complexity signals: number of files in scope table (count CREATE + MODIFY lines in description), number of ACs
   - Keywords that correlate with under-estimation (auth, payment, integration, migration, new-service)

5. **Identify patterns:**
   - Stories with `auth` / `payment` / `integration` keywords: track if they consistently took longer than estimated
   - Stories with similar scope size (file count): track actual vs estimated SP
   - Carry-over rate for this story type: if >30% of similar stories carried over → flag

6. **Generate calibrated estimate:**
   - Base: majority SP of similar completed stories with same service tag
   - Adjustments:
     - +1 SP if story contains auth/payment/integration keywords AND historical pattern shows underestimation
     - +1 SP if scope file count > 5 (above avg for this service tag)
     - +1 SP if story involves new domain/service (first time touching that area)
     - −1 SP if story is clearly simpler than comparables (fewer files, fewer ACs)
   - Confidence: HIGH (3+ strong comparables) / MEDIUM (1-2 comparables) / LOW (no direct comparables, using pattern only)

## Output Format

```text
## Estimation Calibration: [story summary]

Initial estimate: [M / 3 SP]

Similar completed stories:

| Key | Summary | Estimated SP | Cycle Time | Carry-over? |
|-----|---------|-------------|-----------|------------|
| {{PROJECT_KEY}}-201 | [BE] Auth callback | 3 SP | 2.1 days | No |
| {{PROJECT_KEY}}-187 | [BE] OAuth integration | 3 SP | 5.2 days | Yes ⚠️ |
| {{PROJECT_KEY}}-156 | [BE] Line webhook | 3 SP | 2.8 days | No |

Complexity signals:

- Scope files: [N] (avg for [BE] stories: 3.2) → [above/at/below average]
- AC count: [N] (avg: 4.1) → [above/at/below average]
- Keywords: [auth/payment/new-domain detected: yes/no]

Historical pattern: [BE] auth stories estimated at M → actual L in 2/3 cases (67%)

Recommendation: [L / 5 SP] — confidence: [HIGH/MEDIUM/LOW]
Reason: [auth pattern + above-avg scope]

Note: [semantic similarity unavailable — keyword fallback used] (only if fallback triggered)
```

## LOW Confidence Example

When cache returns 0-1 usable comparables:

```text
## Estimation Calibration: [BE] New webhook endpoint for payment callback

Initial estimate: M (3 SP)

Similar completed stories: none found matching [BE] + payment domain

Complexity signals:
- Scope files: unknown (no description yet) → cannot assess
- Keywords: payment, webhook, new-domain detected → HIGH risk keywords present

Historical pattern: insufficient data (0 comparable stories)

Recommendation: M (3 SP) → consider L (5 SP) — confidence: LOW
Reason: payment + webhook + new-domain keyword combination historically underestimated when found in other service tags, but no direct [BE] comparables exist to confirm. Treat as uncertain — flag for team calibration in planning.

Note: semantic similarity unavailable — keyword fallback used
```

Prefix uncertain field values with `~` (e.g., `~3.2 days`) to signal estimation, not measurement.

## Rules

- Never fabricate comparison data — only use what cache returns
- Prefix uncertain/estimated values with `~` — do not present estimates as measurements
- If fewer than 2 comparables found → return LOW confidence estimate with explanation (see example above)
- Fallback to keyword search if semantic search unavailable
- Do not recommend estimates more than ±2 SP from initial (flag if pattern suggests bigger gap)
