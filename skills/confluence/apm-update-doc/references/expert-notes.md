## 🎓 Domain Expert Notes

### Why This Approach

The mandatory Phase 2 (Fetch Current) before any write enforces the core evergreen documentation principle: never update content you haven't read. Documentation debt — broken references, dropped sections, silent overwrites — originates almost entirely from write-without-read patterns. The 5-phase workflow mirrors content lifecycle management: retrieve → diff → generate → review → commit.

### Industry Frameworks Used

| Framework | Applied In | Why |
| --- | --- | --- |
| Content Lifecycle Management — CLM (AIIM / Gartner framework) | Phases 2–5 (fetch → generate → review → update) | CLM defines 5 stages: Create → Review → Approve → Publish → Archive. This skill's 5-phase workflow maps directly: Fetch=Approve-gate (check for existing approved content), Generate=Create, QG=Review, Update=Publish. The 30% threshold (section vs. content update) approximates the CLM "change scope" boundary between an amendment and a new revision |
| Evergreen Documentation (Tom Johnson, *I'd Rather Be Writing*, 2015) | Phase 3 section-scoped updates | Johnson's evergreen principle: each section is independently stable; updates should scope to the changed section only, not touch unrelated stable sections. A section update touching >30% of total page content violates evergreen boundaries — it's a version revision, not an amendment |
| Keep a Changelog convention (Olivier Lacan, keepachangelog.com) | `status` update type | Status transitions (Draft → In Review → Published) are lifecycle events that warrant a human-readable summary. The 90-day stale threshold aligns with Lacan's "Unreleased" convention: content not updated in 90+ days is effectively unreleased — may not reflect current reality |
| Docs as Code version traceability (Anne Gentle, *Docs Like Code*, 2017) | Version number displayed in Phase 4 preview | Showing the current Confluence version number before write surfaces concurrent-edit risk. Gentle's principle: documentation changes should be as reviewable as code changes — the version display is the equivalent of `git status` before committing |

### Key Metrics

- **Page version drift:** If current version ≥ 10 and the last update was > 90 days ago, the page is a stale content candidate — flag for review before making incremental edits
- **Section preservation rate:** A `section` update should touch ≤ 30% of total page content; if more than 30% changes, use `content` update type and full review
- **Stale detection threshold:** Atlassian recommends a 6-month automation trigger for pages with no edits — pages beyond this window should be reviewed for accuracy before any update, not just patched
- **Concurrent edit risk:** Confluence version numbers increment on every save; if the version fetched in Phase 2 differs from the current version at Phase 5 write time, abort and re-fetch — this is the Confluence equivalent of a Git merge conflict

### Expert Decision Criteria

- If the page contains a `{toc}` or `{children}` macro anywhere → always use `update_page_storage.py`, never MCP `confluence_update_page` (HR4; MCP HTML-escapes macros to raw XML)
- If the update touches only 1–2 sentences in a known section → use `section` update, not `content` update; limits blast radius
- If the user says "rename" or "retitle" → treat as `content` update, not `replace`; title changes require `confluence_update_page` with the new title field, not a find/replace on body text
- If the page was last edited > 6 months ago → read the full content in Phase 2 and validate all external links and Jira references before updating; stale pages often contain broken issue links
- If moving a page that has children → move the parent only; Confluence automatically moves all descendants; do not batch-move children manually

### Common Failure Modes

| Symptom | Root Cause | Expert Fix |
| --- | --- | --- |
| Sections silently dropped after content update | Phase 2 skipped; new content generated from user input alone | Always fetch first; diff generated content against fetched content before writing |
| Macros render as raw XML after update | MCP `confluence_update_page` HTML-escapes `<ac:…>` tags | Use `update_page_storage.py` for any page with ToC, Children, or Code macros (HR4) |
| Wrong page overwritten | Title search returned multiple matches; first result accepted without confirmation | Always prefer page ID over title; if title used, show all matches and require explicit selection |
| Concurrent edit lost | Version fetched in Phase 2 is stale by write time | Re-fetch immediately before write in high-traffic spaces; compare version numbers |
| Move breaks child page links | Children moved manually after parent move | Move only the parent; Confluence cascades to descendants automatically |

### Authoritative References

- **Midori / Atlassian — Confluence Content Lifecycle Management:** "Content lifecycle management clarifies who is notified of stale content and defines content owners per section" — the `status` update type is the primary mechanism for formalising lifecycle transitions in Confluence
- **Docsie — Evergreen Documentation (2025):** Evergreen content requires scoped, targeted updates rather than wholesale rewrites; the `section` update type is the operational implementation of this principle
- **Keep a Changelog (keepachangelog.com):** "Don't let your friends dump git logs into changelogs" — status transitions on a Confluence page should carry a human-readable summary of what changed and why, not just a version bump
- **Atlassian Community — Knowledge Base Best Practices:** Set a 6-month automation rule to flag pages not updated since that window; stale pages erode team trust in the entire knowledge base faster than missing pages do

---
