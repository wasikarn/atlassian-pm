"""Shared session state for Claude hooks.

Single state file per session at /tmp/claude-hooks-state/{session_id}.json.
Used by HR6 (cache invalidation), HR7 (sprint lookup), search tracking,
cache-prefer (cache-first reads), and qmd (codebase search).

File locking via fcntl.flock prevents race conditions when parallel
subagents access the same state file concurrently.
"""

import fcntl
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config_loader import load_project_config

STATE_DIR = Path("/tmp/claude-hooks-state")

# In-process read cache — avoids redundant file reads when a hook calls
# multiple state functions in one execution (each hook is its own subprocess,
# so this cache is discarded when the process exits).
_cache: dict[str, dict] = {}


def _state_file(session_id: str) -> Path:
    return STATE_DIR / f"{session_id or 'default'}.json"


def _lock_file(session_id: str) -> Path:
    return STATE_DIR / f"{session_id or 'default'}.lock"


def _load(session_id: str) -> dict:
    if session_id in _cache:
        return _cache[session_id]
    f = _state_file(session_id)
    try:
        state = json.loads(f.read_text()) if f.exists() else {}
    except Exception:
        state = {}
    _cache[session_id] = state
    return state


def _save(session_id: str, state: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    lock = _lock_file(session_id)
    lock.touch(exist_ok=True)
    with open(lock, "r") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            # Re-read under lock to merge concurrent writes
            f = _state_file(session_id)
            try:
                disk_state = json.loads(f.read_text()) if f.exists() else {}
            except Exception:
                disk_state = {}
            # Merge: our state wins for keys we touched
            disk_state.update(state)
            _cache[session_id] = disk_state
            f.write_text(json.dumps(disk_state))
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)


# ── HR6: Cache invalidation tracking ──────────────────


def hr6_add_pending(session_id: str, key: str) -> None:
    state = _load(session_id)
    pending = set(state.get("hr6_pending", []))
    pending.add(key)
    state["hr6_pending"] = sorted(pending)
    _save(session_id, state)


def hr6_remove_pending(session_id: str, key: str) -> None:
    state = _load(session_id)
    pending = set(state.get("hr6_pending", []))
    pending.discard(key)
    state["hr6_pending"] = sorted(pending)
    _save(session_id, state)


def hr6_get_pending(session_id: str) -> set[str]:
    return set(_load(session_id).get("hr6_pending", []))


def hr6_clear_all_pending(session_id: str) -> None:
    state = _load(session_id)
    state["hr6_pending"] = []
    _save(session_id, state)


# ── HR7: Sprint lookup tracking ───────────────────────


def hr7_mark_lookup_done(session_id: str) -> None:
    state = _load(session_id)
    state["hr7_lookup_done"] = True
    _save(session_id, state)


def hr7_is_lookup_done(session_id: str) -> bool:
    return _load(session_id).get("hr7_lookup_done", False)


# ── Search tracking ───────────────────────────────────


def search_mark_done(session_id: str) -> None:
    state = _load(session_id)
    state["search_done"] = True
    _save(session_id, state)


def search_is_done(session_id: str) -> bool:
    return _load(session_id).get("search_done", False)


# ── HR5: Parent verification tracking ─────────────────


def hr5_add_pending(session_id: str, child_key: str, parent_key: str) -> None:
    state = _load(session_id)
    pending = state.get("hr5_pending", [])
    if not any(p["child"] == child_key for p in pending):
        pending.append({"child": child_key, "parent": parent_key})
    state["hr5_pending"] = pending
    _save(session_id, state)


def hr5_get_pending(session_id: str) -> list:
    return list(_load(session_id).get("hr5_pending", []))


def hr5_add_known_subtask(session_id: str, child_key: str) -> None:
    """Permanently track a key as a known subtask (survives verify-clear)."""
    state = _load(session_id)
    subtasks = set(state.get("hr5_known_subtasks", []))
    subtasks.add(child_key)
    state["hr5_known_subtasks"] = sorted(subtasks)
    _save(session_id, state)


def hr5_is_known_subtask(session_id: str, issue_key: str) -> bool:
    return issue_key in set(_load(session_id).get("hr5_known_subtasks", []))


def hr5_remove_pending(session_id: str, child_key: str) -> None:
    state = _load(session_id)
    pending = [p for p in state.get("hr5_pending", []) if p["child"] != child_key]
    state["hr5_pending"] = pending
    _save(session_id, state)


# ── Event-AC: Domain Model tracking ──────────────────


def event_set_domain_events(session_id: str, epic_key: str, events: list) -> None:
    state = _load(session_id)
    catalog = state.get("domain_events", {})
    catalog[epic_key] = events
    state["domain_events"] = catalog
    _save(session_id, state)


def event_get_all_events(session_id: str) -> list:
    """Get all known domain events across all epics."""
    catalog = _load(session_id).get("domain_events", {})
    all_events = []
    for events in catalog.values():
        all_events.extend(events)
    return list(set(all_events))


# ── VS Integrity: AC coverage tracking ───────────────


def vs_set_story_acs(session_id: str, story_key: str, acs: list) -> None:
    state = _load(session_id)
    ac_map = state.get("vs_story_acs", {})
    ac_map[story_key] = acs
    state["vs_story_acs"] = ac_map
    _save(session_id, state)


def vs_add_subtask(session_id: str, story_key: str, subtask_key: str, summary: str) -> None:
    state = _load(session_id)
    subtasks = state.get("vs_subtasks", {})
    if story_key not in subtasks:
        subtasks[story_key] = []
    if not any(s["key"] == subtask_key for s in subtasks[story_key]):
        subtasks[story_key].append({"key": subtask_key, "summary": summary})
    state["vs_subtasks"] = subtasks
    _save(session_id, state)


def vs_get_coverage(session_id: str) -> dict:
    state = _load(session_id)
    return {
        "story_acs": dict(state.get("vs_story_acs", {})),
        "subtasks": dict(state.get("vs_subtasks", {})),
    }


# ── Cache-prefer: per-issue cache-first tracking ─────


def cache_mark_checked(session_id: str, issue_key: str) -> None:
    """Mark that cache was tried for this issue (allows MCP fallback)."""
    state = _load(session_id)
    checked = set(state.get("cache_checked_issues", []))
    checked.add(issue_key)
    state["cache_checked_issues"] = sorted(checked)
    _save(session_id, state)


def cache_is_checked(session_id: str, issue_key: str) -> bool:
    """Check if cache was already tried for this issue."""
    return issue_key in set(_load(session_id).get("cache_checked_issues", []))


# ── QMD: Usage tracking ─────────────────────────────

def _build_qmd_collections() -> dict[str, str]:
    """Build QMD_COLLECTIONS from project-config.json services.tags[].

    Returns empty dict if config missing — qmd hooks degrade gracefully.
    expanduser() converts ~/Codes/... to absolute path.
    Note: if two services share the same directory basename, the last one wins silently.
    """
    config = load_project_config()
    result = {}
    for svc in config.get("services", {}).get("tags", []):
        if svc.get("path"):
            resolved = Path(svc["path"]).expanduser()
            result[str(resolved)] = resolved.name
    return result


# Known indexed project roots → collection name (built from project-config.json)
QMD_COLLECTIONS = _build_qmd_collections()


def qmd_mark_collection_searched(session_id: str, collection: str) -> None:
    """Mark a collection as auto-searched (per-collection tracking)."""
    state = _load(session_id)
    searched = set(state.get("qmd_searched_collections", []))
    searched.add(collection)
    state["qmd_searched_collections"] = sorted(searched)
    _save(session_id, state)


def qmd_is_collection_searched(session_id: str, collection: str) -> bool:
    """Check if a collection was already auto-searched."""
    return collection in set(_load(session_id).get("qmd_searched_collections", []))


def qmd_collection_for_path(path: str) -> str | None:
    """Return collection name if path falls within an indexed project."""
    for root, name in QMD_COLLECTIONS.items():
        if path.startswith(root):
            return name
    return None

# ── Jira write activity tracking ────────────────────────────────────────────


def jira_write_mark_occurred(session_id: str) -> None:
    """Mark that at least one Jira write occurred this session (never cleared)."""
    state = _load(session_id)
    if not state.get("jira_write_occurred"):
        state["jira_write_occurred"] = True
        _save(session_id, state)


def jira_write_is_occurred(session_id: str) -> bool:
    """Return True if any Jira write operation occurred this session."""
    return bool(_load(session_id).get("jira_write_occurred", False))


# ── Subtask alignment tracking ──────────────────────────────────────────────

def alignment_mark_sprint_suggested(session_id: str, sprint_id: str) -> None:
    """Mark that alignment check was suggested for this sprint."""
    state = _load(session_id)
    suggested = set(state.get("alignment_suggested_sprints", []))
    suggested.add(str(sprint_id))
    state["alignment_suggested_sprints"] = sorted(suggested)
    _save(session_id, state)

def alignment_is_sprint_suggested(session_id: str, sprint_id: str) -> bool:
    """Check if alignment check was already suggested for this sprint."""
    return str(sprint_id) in set(_load(session_id).get("alignment_suggested_sprints", []))
