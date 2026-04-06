## 🎓 Domain Expert Notes

### Why This Approach

Living documentation (Nat Pryce & Steve Freeman, "Growing Object-Oriented Software") holds that documentation is only trustworthy when it is generated from or directly linked to the system it describes. This skill enforces that principle bidirectionally: a change to any artifact in the graph propagates to all related artifacts in a defined order (parents before children, Jira before Confluence), preventing the drift that makes documentation untrustworthy.

### Industry Frameworks Used

| Framework | Applied In | Why |
| --------- | --------- | --- |
| Single Source of Truth (Atlassian) | Phase 3 Change Classification + Phase 6 tool selection | Authoritative content lives in exactly one place (Jira for workflow state, Confluence for context/rationale); sync direction always flows from the authoritative source outward — never duplicate content across both |
| Living Documentation (Nat Pryce & Steve Freeman) | Phase 8 Verify & Report via `audit_confluence_pages.py` | Pryce/Freeman: documentation is only trustworthy when continuously verified against the system it describes, not at point-of-write. The audit step implements this — docs are verified post-sync, not assumed correct |
| Change Impact Analysis — PMBOK Integrated Change Control | Phase 3 Change Classification (LOW/MEDIUM/HIGH) | Triage by blast radius before execution. LOW changes skip Phase 5 codebase exploration entirely. PMBOK: every change should be assessed for impact on scope, schedule, and cost before approval — the blast radius map is the lightweight sprint-team equivalent |
| Scope Change Discipline (Mike Cohn, "Succeeding with Agile") | Phase 3 HIGH-impact approval gate | Cohn: scope changes during a sprint should be treated as new backlog items, not silent edits. The HIGH-impact gate operationalises this — Remove AC / Change scope requires explicit APPROVAL before Phase 7 executes |

### Key Metrics

- **Change blast radius:** HIGH-impact changes (Remove AC, Change scope, Business value change) should touch ≥ 3 artifacts in the graph; if the impact map shows fewer than 3 affected artifacts for a HIGH change, the graph discovery in Phase 2 may be incomplete
- **Sync execution order compliance:** Parents-first ordering is mandatory; executing child updates before parent updates will be detected by QG pre-check (Phase 7) via parent AC cross-reference
- **Confluence drift rate:** If `audit_confluence_pages.py` flags > 20% of pages after a sync, it indicates the Confluence pages were not updated when prior Jira changes were made — run a full `/sync-artifacts` from the epic level to re-align
- **Dedup protection:** Phase 6 shows before/after diffs; if a "before" snapshot doesn't match what is currently in Jira/Confluence, another party has edited the artifact — treat as a conflict and resolve manually before applying the sync

### Expert Decision Criteria

- If change type is "Format only" or "Clarify wording" → impact level is LOW regardless of which artifact originates the change; skip Phase 5 codebase exploration and restrict updates to the origin artifact only
- If origin is a Confluence page (not a Jira key) → Phase 1 must pivot to Jira by extracting embedded issue keys before building the artifact graph; never sync Confluence-to-Confluence without grounding in the Jira hierarchy
- If a subtask is `Done` status and a parent story AC changes → flag the subtask as `FLAG` (not `UPDATE`) and surface it for manual review; auto-updating a Done subtask creates a false re-open signal in the burndown
- If the impact map shows > 8 artifacts to update → split into two sync operations (Jira-only first, Confluence second) to reduce the risk of partial failure leaving the graph in an inconsistent state
- HIGH impact changes (Remove AC, Change scope) require an explicit APPROVAL gate before Phase 7 execution, even if all previous gates passed; scope reduction has legal/contractual implications in some environments

### Common Failure Modes

| Symptom | Root Cause | Expert Fix |
| ------- | --------- | --------- |
| Confluence page shows stale content after sync | Confluence macro-containing pages updated via MCP (HR4 violation) | Re-run Phase 7 using `update_page_storage.py` for any page with ToC, Children, or Code macros |
| Child subtask AC conflicts with updated parent story AC | Sync executed children before parent (ordering violation) | Enforce Phase 7 topological order; re-run parent update first, then re-apply child updates |
| Artifact graph missing Tech Notes | `confluence_search("{{PROJECT_KEY}}-XXX")` returned no results because the Tech Note title doesn't embed the issue key | Search by story title as fallback; manually add the issue key to the Confluence page title for future syncs |
| Phase 1 gate blocks because change description is too vague | User passed only the issue key with no change description | Prompt user for specific change description before building the artifact graph; "update" is not classifiable — needs "what changed and how" |
| Cache reads stale data after sync | HR6 `cache_invalidate` skipped for one or more writes | Run `cache_invalidate` for every key in `applied_keys[]`; re-verify with `cache_get_issue` to confirm fresh data |

### Authoritative References

- **Nat Pryce & Steve Freeman, "Growing Object-Oriented Software" (2009):** "Tests are living documentation" — extend to all artifacts: Jira issues and Confluence pages must reflect the current state of the system, not its intended state
- **Atlassian, "Single Source of Truth" (2024):** "Link, don't duplicate — reference Confluence from Jira and vice versa; avoid copying the same content into both systems"; the artifact graph enforces this by treating each artifact as authoritative for its own content type
- **Atlassian Engineering Blog:** 76% of Jira+Confluence integrated teams reported faster shipping; 66% reported improved cross-team communication — integration value is realised only if sync discipline prevents drift
- **Mike Cohn, "Succeeding with Agile" (2009):** Scope changes during a sprint should be treated as new backlog items, not silent edits to in-progress stories; Phase 3 HIGH-impact classification is the operationalised version of this discipline
