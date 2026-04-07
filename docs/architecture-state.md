# State Management Architecture: atlassian-pm Plugin

This document describes the high-performance session state management system used by the plugin hooks.

## Overview

The system implements a multi-tier storage strategy to eliminate lock contention and minimize disk I/O, moving from a legacy JSON-lock system to a Zero-Disk RAM-based approach.

## Architecture Layers

### Layer 1: In-Process L1 Cache (`functools.lru_cache`)

- **Purpose**: Instant access to frequently read state within a single hook execution.
- **Mechanism**: `get_state` is wrapped in an LRU cache.
- **Invalidation**: Any `set_state` call triggers `cache_clear()` to ensure consistency.

### Layer 2: State-Daemon (RAM via Unix Domain Sockets)

- **Purpose**: The "Hot Path." Zero-Disk I/O state management.
- **Mechanism**: A background daemon manages state in a Python dictionary. Hooks communicate via UDS.
- **Lifecycle**: 
  - Auto-starts on first hook call.
  - Heartbeat: Exits after 10 minutes of inactivity.
  - PID File: Prevents duplicate daemons per session.
- **Fallback**: If the daemon is unavailable, the system transparently falls back to Layer 3.

### Layer 3: SQLite WAL Database (Persistent Storage)

- **Purpose**: Durability and high-concurrency fallback.
- **Mechanism**: SQLite in **Write-Ahead Logging (WAL)** mode.
- **Tuning**:
  - `mmap_size`: Maps DB into virtual memory to avoid `read()` syscalls.
  - `synchronous=NORMAL`: Balances ACID safety with write speed.
- **Advanced Features**:
  - **Bloom Filter**: Probabilistic check to skip DB queries for non-existent keys.
  - **Delta Tracking**: Stores only changes for large objects (>1KB) to reduce WAL pressure.

## Data Flow (Read Path)

`L1 Cache` $\rightarrow$ `State-Daemon (RAM)` $\rightarrow$ `Bloom Filter (Check)` $\rightarrow$ `SQLite (Disk)`

## Data Flow (Write Path)

`L1 Cache Invalidation` $\rightarrow$ `State-Daemon (Update)` $\rightarrow$ `SQLite (Persistent Commit)`

## Maintenance & Debugging

- State directory: `/tmp/claude-hooks-state/`
- Clear state: `rm -rf /tmp/claude-hooks-state/`
- Database inspection: `sqlite3 /tmp/claude-hooks-state/{session_id}.db`
