## 🎓 Domain Expert Notes

### Why This Approach

Release notes serve two distinct audiences with opposing needs: engineers want completeness and traceability (every fix key, every breaking change), while stakeholders want impact narrative ("what does this mean for me?"). The skill's phase structure — fetch → group → draft → review → publish — enforces the separation: grouping by type (Features / Bug Fixes / Improvements) satisfies the engineer audience; the "What's Changed" narrative paragraph satisfies stakeholders.

### Industry Frameworks Used

| Framework | Applied In | Why |
| --------- | --------- | --- |
| Keep a Changelog format (Olivier Lacan, keepachangelog.com) | Phase 3 issue table structure (Added/Fixed/Changed groupings) | Changelog = developer-facing, entry per commit/PR, all changes including internal. Release notes = stakeholder-facing, curated summary of user-visible changes only. They are distinct artifacts: this skill produces **release notes** that adopt changelog *structure* for the issue table but adds a stakeholder narrative layer that a raw changelog never has |
| Semantic Versioning (SemVer 2.0, Tom Preston-Werner, semver.org) | `--version` argument parsing | MAJOR.MINOR.PATCH communicates breaking change risk before stakeholders read content: MAJOR = read everything carefully; MINOR = scan for new features; PATCH = safe to upgrade. Sets expectation before opening the page |
| Audience-based writing (Ginny Redish, *Letting Go of the Words*, 2012) | Phase 3 narrative paragraph vs. issue table | Different reading goals = different content layers. Engineers scan the issue table (find my fix). Stakeholders read the narrative (understand the impact). Single-page dual-track: the page succeeds for both audiences without being written twice |

### Key Metrics

- **Coverage ratio:** `(issues in release notes) / (issues in Fix Version with resolution=Done)` — target 100%; any gap means a delivered change is invisible to stakeholders
- **Time-to-publish:** Duration from sprint close to release notes published — industry target is same-day; notes published >3 days after release lose stakeholder trust
- **Narrative readability:** The "What's Changed" paragraph should pass the "non-engineer stakeholder test" — zero Jira keys, zero technical acronyms, focus on user-facing outcomes only

### Expert Decision Criteria

- If a Fix Version contains >30 issues → group sub-epics before listing individual tasks to avoid list overload; the narrative paragraph becomes critical at this scale
- If the release contains any MAJOR version bump (SemVer) → add a dedicated "Breaking Changes" section at the top of Phase 3 draft, before Features — breaking changes must be impossible to miss
- If `--dry-run` output shows issues in the "Other" group → those issues lack proper issuetype or label classification; fix at the Jira level before publishing, not in the notes
- If publishing notes for an Unreleased version → add a banner "DRAFT — not yet released" to the Confluence page to prevent stakeholder confusion

### Common Failure Modes

| Symptom | Root Cause | Expert Fix |
| ------- | --------- | --------- |
| Phase 2 returns 0 issues | Fix Version not created in Jira, or no issues have `fixVersion` set | Create the version in Jira Project Settings → Versions, then bulk-edit issues to set `fixVersion` |
| All issues land in "Other" group | Issues use non-standard issuetypes or missing labels | Standardise: Stories → Features, Tasks with `[Bug]` prefix → Bug Fixes, Tasks with `tech-debt` label → Improvements |
| Confluence page published with broken ADF | ADF draft generated with unsupported macro via MCP (HR4) | Use `--dry-run` first; if macros appear in draft, switch to `update_page_storage.py` for the publish step |
| Stakeholders ask "what changed for me?" after reading | Notes written for engineers only — all Jira keys, no narrative | The "What's Changed" paragraph is mandatory; tech jargon in that section is a content quality failure |
| Duplicate "Release Notes" pages in Confluence | Ran without `--update` when page already exists | Add parent page ID convention and check for existing page title before creating |

### Authoritative References

- **Olivier Lacan — Keep a Changelog:** "Don't dump your git log into changelogs" — the discipline of curating change entries rather than auto-generating them is what makes the document trustworthy. The timing tension: publish immediately (incomplete but timely) vs. publish when complete (accurate but late). Resolution: publish a DRAFT within hours of release, mark clearly as draft, update within 24h — trust comes from speed + accuracy together, not either alone
- **Tom Preston-Werner — Semantic Versioning 2.0.0 (semver.org):** "If your software is used by others, you owe them compatibility guarantees." Version numbers are a promise, not a label — MAJOR bump means you broke that promise intentionally and stakeholders must be informed before upgrading
- **Ginny Redish — *Letting Go of the Words* (2012):** "People don't read web pages; they scan them." The dual-track layout (table for scanning, narrative for reading) applies this directly — engineers scan the table, stakeholders read the paragraph. A single wall of text fails both audiences
- **Atlassian Fix Versions:** Sprints are planning units; Fix Versions are delivery units — conflating them (using sprint names as release identifiers) breaks the release notes chain and corrupts burndown reporting
