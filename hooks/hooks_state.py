"""Shared session state for Claude hooks.

Single state file per session at /tmp/claude-hooks-state/{session_id}.json.
Used by HR6 (cache invalidation), HR7 (sprint lookup), search tracking,
cache-prefer (cache-first reads), and qmd (codebase search).

File locking via fcntl.flock prevents race conditions when parallel
subagents access the same state file concurrently.
"""

import fcntl
import functools
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config_loader import load_project_config

STATE_DIR = Path("/tmp/claude-hooks-state")
_STATE_STR = str(STATE_DIR)  # cached str for Path ops

# State entries older than this are considered stale and auto-cleaned
STATE_EXPIRY_SECONDS = 3600  # 1 hour

# In-process read cache — avoids redundant file reads when a hook calls
# multiple state functions in one execution (each hook is its own subprocess,
# so this cache is discarded when the process exits).
_cache: dict[str, dict] = {}
_state_dir_ready: bool = False  # mkdir guard: only called once per process


def _ensure_state_dir() -> None:
    global _state_dir_ready
    if not _state_dir_ready:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        os.chmod(STATE_DIR, 0o700)  # Owner-only: directory contains sensitive session state
        _state_dir_ready = True


@functools.lru_cache(maxsize=64)
def _state_file(session_id: str) -> Path:
    return STATE_DIR / f"{session_id or 'default'}.json"


@functools.lru_cache(maxsize=64)
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
    _ensure_state_dir()
    lock = _lock_file(session_id)

    # Implementation of Non-blocking Lock with Exponential Backoff
    # Prevents the "stop hooks 7/8" hang by not waiting indefinitely for LOCK_EX
    max_retries = 5
    base_delay = 0.05  # 50ms

    with open(lock, "a+") as lf:
        for attempt in range(max_retries):
            try:
                fcntl.flock(lf, fcntl.LOCK_EX | fcntl.LOCK_NB)
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
                    os.chmod(f, 0o600)  # Owner read/write: session state may contain sensitive Jira keys
                    return # Success!
                finally:
                    fcntl.flock(lf, fcntl.LOCK_UN)
            except (BlockingIOError, IOError):
                if attempt == max_retries - 1:
                    # Final attempt failed, log and bail to prevent turn-end hang
                    log_event("hooks_state_save", "LOCK_TIMEOUT", {"session_id": session_id, "retries": max_retries})
                    return
                time.sleep(base_delay * (2 ** attempt)) # Exponential backoff


def cleanup_stale_state(session_id: str) -> None:
    """Remove state entries older than STATE_EXPIRY_SECONDS.

    Cleans both top-level dict entries with 'ts' field and list entries
    (like hr5_pending) that have 'ts' field. Call this before reading state
    to prevent stale entries from blocking operations.
    """
    state = _load(session_id)
    if not state:
        return
    now = time.time()
    modified = False

    # Clean stale top-level dict entries with 'ts' field
    for key in list(state.keys()):
        if isinstance(state[key], dict) and 'ts' in state[key]:
            if now - state[key]['ts'] > STATE_EXPIRY_SECONDS:
                del state[key]
                modified = True

    # Clean stale hr5_pending list entries
    if 'hr5_pending' in state:
        pending = state['hr5_pending']
        if isinstance(pending, list):
            original_len = len(pending)
            state['hr5_pending'] = [
                p for p in pending
                if not (isinstance(p, dict) and 'ts' in p and now - p['ts'] > STATE_EXPIRY_SECONDS)
            ]
            if len(state['hr5_pending']) != original_len:
                modified = True

    if modified:
        _save(session_id, state)


def set_state(session_id: str, key: str, value: Any) -> None:
    """Set a state value with automatic timestamp tracking.

    Stores the value with a 'ts' timestamp for expiry detection by
    cleanup_stale_state. Use this for ephemeral state that should
    expire after STATE_EXPIRY_SECONDS.
    """
    state = _load(session_id)
    state[key] = {
        'value': value,
        'ts': time.time()
    }
    _save(session_id, state)


def get_state(session_id: str, key: str) -> Any | None:
    """Get a state value set by set_state.

    Returns the value if present and not expired, None otherwise.
    """
    state = _load(session_id)
    entry = state.get(key)
    if isinstance(entry, dict) and 'value' in entry:
        # Entry with timestamp - check expiry
        if 'ts' in entry:
            if time.time() - entry['ts'] > STATE_EXPIRY_SECONDS:
                return None
        return entry['value']
    return None


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
        pending.append({"child": child_key, "parent": parent_key, "ts": time.time()})
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


# ── Cache-first warning: per-session warning count ──────────────────


def cache_warning_count(session_id: str) -> int:
    """Return number of cache-first warnings issued this session."""
    return _load(session_id).get("cache_warning_count", 0)


def cache_warning_increment(session_id: str) -> None:
    """Increment the cache-first warning count for this session."""
    state = _load(session_id)
    state["cache_warning_count"] = state.get("cache_warning_count", 0) + 1
    _save(session_id, state)


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


@functools.cache
def _get_qmd_collections() -> dict[str, str]:
    """Lazy-loaded QMD collection map. Only evaluated on first call."""
    return _build_qmd_collections()


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
    for root, name in _get_qmd_collections().items():
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


# ── Sprint risk assessment tracking ─────────────────────────────────────────


def risk_mark_sprint_assessed(session_id: str, sprint_id: str) -> None:
    """Mark that risk-forecaster was run for this sprint."""
    state = _load(session_id)
    assessed = set(state.get("risk_assessed_sprints", []))
    assessed.add(str(sprint_id))
    state["risk_assessed_sprints"] = sorted(assessed)
    _save(session_id, state)


def risk_is_sprint_assessed(session_id: str, sprint_id: str) -> bool:
    """Return True if risk-forecaster was already run for this sprint."""
    return str(sprint_id) in set(_load(session_id).get("risk_assessed_sprints", []))


# ── Skill checkpoint tracking ────────────────────────────────────────────────
#
# Saves issue keys created during skill workflows so they survive context
# compaction. Compact-reinject reads these and outputs them to Claude's context,
# restoring the "what was created so far" context without any skill re-execution.
#
# Schema per checkpoint:
#   {"key": "TP-123", "type": "Story", "ts": 1234567890.0}
# For subtasks, also includes: {"parent": "TP-100"}


def skill_checkpoint_save(session_id: str, key: str, issue_type: str, parent_key: str | None = None) -> None:
    """Save a created issue checkpoint. Stores up to 10 subtasks; story/epic overwrite."""
    state = _load(session_id)
    cp = state.get("skill_checkpoints", {})
    entry = {"key": key, "type": issue_type, "ts": time.time()}
    if parent_key:
        entry["parent"] = parent_key

    issue_type_lower = issue_type.lower()
    if "subtask" in issue_type_lower or "sub-task" in issue_type_lower:
        subtasks = cp.get("subtasks", [])
        if not any(s["key"] == key for s in subtasks):
            subtasks.append(entry)
        cp["subtasks"] = subtasks[-10:]  # keep last 10
    elif "epic" in issue_type_lower:
        cp["latest_epic"] = entry
    else:
        cp["latest_story"] = entry

    state["skill_checkpoints"] = cp
    _save(session_id, state)


def skill_checkpoint_get(session_id: str) -> dict:
    """Return all skill checkpoints: {latest_story, latest_epic, subtasks:[]}."""
    return dict(_load(session_id).get("skill_checkpoints", {}))


def skill_checkpoint_clear(session_id: str) -> None:
    """Clear all skill checkpoints (call when a workflow completes cleanly)."""
    state = _load(session_id)
    state.pop("skill_checkpoints", None)
    _save(session_id, state)


# ── Session-level state (no session_id required) ─────────────────────────
#
# Convenience wrappers for global/session-agnostic state such as AI cost
# tracking. Uses the "default" session key so data persists for the lifetime
# of /tmp/claude-hooks-state/default.json.


def load_state() -> dict:
    """Load global session state (session-id-agnostic convenience wrapper)."""
    return dict(_load("default"))


def save_state(state: dict) -> None:
    """Persist global session state (session-id-agnostic convenience wrapper)."""
    _save("default", state)


# ── Response size tracking (token usage observability) ───────────────────


def response_size_track(session_id: str, tool: str, chars: int, tokens: int) -> None:
    """Track response size for a tool call in session state.

    Accumulates per-tool and total stats for the session, enabling
    analysis of token-heavy operations via cache_stats or similar.

    Args:
        session_id: Claude session identifier
        tool: Short tool name (e.g., "jira_get_issue", "cache_search")
        chars: Response size in characters
        tokens: Estimated token count
    """
    state = _load(session_id)
    sizes = state.get("response_sizes", {})

    # Per-tool accumulation
    if tool not in sizes:
        sizes[tool] = {"chars": 0, "tokens": 0, "calls": 0}
    sizes[tool]["chars"] += chars
    sizes[tool]["tokens"] += tokens
    sizes[tool]["calls"] += 1

    # Total accumulation
    totals = state.get("response_totals", {"chars": 0, "tokens": 0, "calls": 0})
    totals["chars"] += chars
    totals["tokens"] += tokens
    totals["calls"] += 1

    state["response_sizes"] = sizes
    state["response_totals"] = totals
    _save(session_id, state)


def response_size_get_stats(session_id: str) -> dict:
    """Get cumulative response size stats for the session.

    Returns:
        {
            "totals": {"chars": N, "tokens": N, "calls": N},
            "by_tool": {"jira_get_issue": {"chars": N, "tokens": N, "calls": N}, ...}
        }
    """
    state = _load(session_id)
    return {
        "totals": dict(state.get("response_totals", {"chars": 0, "tokens": 0, "calls": 0})),
        "by_tool": dict(state.get("response_sizes", {})),
    }
