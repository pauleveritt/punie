# Phase 6.3: Local Tools - Plan

## Problem

Punie's tools currently work only through ACP (Agent Communication Protocol) — they delegate file reads, writes, and command execution to PyCharm via JSON-RPC. This makes the agent completely dependent on IDE integration and unable to run standalone.

## Solution

Create a `LocalClient` that implements the same `Client` protocol using real filesystem and subprocess operations instead of ACP delegation.

## Key Design Goal

**Easy switching between local tools and IDE-discovered tools.** By implementing the existing `Client` protocol, the same 7 tool functions and `ACPDeps` work unchanged — only the `Client` implementation is swapped.

```
┌─────────────────────────────────────────────┐
│  Same 7 tools in src/punie/agent/toolset.py │
│  Same ACPDeps (client_conn, session_id,     │
│               tracker)                      │
└──────────────┬──────────────────────────────┘
               │ client_conn is either:
    ┌──────────┴──────────┐
    │                     │
 ACP Client          LocalClient
 (PyCharm RPC)       (real filesystem)
```

## Architecture

LocalClient mirrors FakeClient but uses real I/O:
- FakeClient: in-memory dict for files, no subprocess
- LocalClient: real filesystem via Path, subprocess via asyncio

Both satisfy the same `Client` protocol from `src/punie/acp/interfaces.py`.

## Tasks

1. Save spec documentation
2. Create LocalClient with real filesystem and subprocess
3. Create package structure
4. Wire into agent factory
5. Wire into CLI
6. Write comprehensive tests
7. Update docs and roadmap

## Success Criteria

- LocalClient satisfies Client protocol at runtime
- All 7 existing tools work with LocalClient
- ToolCallTracker works (session_update is no-op)
- Tests pass using real tmp_path filesystem
- Agent can run standalone without ACP/PyCharm
