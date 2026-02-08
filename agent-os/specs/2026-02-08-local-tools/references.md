# Phase 6.3: Local Tools - References

## Key Files

### Protocol Definition
- `src/punie/acp/interfaces.py:74-166` — Client protocol with all methods

### Existing Implementations
- `src/punie/acp/fake_client.py` — In-memory client (reference for LocalClient)
- `src/punie/acp/client.py` — ACP JSON-RPC client (what LocalClient replaces)

### Tool Functions
- `src/punie/agent/toolset.py` — 7 tool functions using Client protocol
- `src/punie/agent/models.py:22-27` — ACPDeps dataclass

### Agent Factory
- `src/punie/agent/factory.py` — create_pydantic_agent function

### CLI Entry Point
- `src/punie/cli.py` — Main CLI with serve command

### Tracker
- `src/punie/agent/tracker.py` — ToolCallTracker (calls session_update)

## Related Tests

- `tests/test_fake_client.py` — Tests for FakeClient (pattern for LocalClient tests)
- `tests/test_toolset.py` — Tests for tool functions with FakeClient

## Python Documentation

### asyncio.subprocess
- https://docs.python.org/3/library/asyncio-subprocess.html
- `asyncio.create_subprocess_exec()` for running commands
- `Process.communicate()` for reading output
- `Process.wait()` for exit code
- `Process.kill()` for termination

### pathlib
- https://docs.python.org/3/library/pathlib.html
- `Path.read_text()` for reading files
- `Path.write_text()` for writing files
- `Path.is_relative_to()` for safety checks (Phase 6.5)

## Design Decisions

### Why LocalClient, not just functions?
Implements existing Client protocol so all 7 tools work unchanged. Swap client, not tools.

### Why dataclass, not frozen?
Must track mutable subprocess state in `_terminals` dict.

### Why auto-approve permissions?
No IDE to prompt user. Phase 6.5 will add workspace safety checks instead.

### Why no-op session_update?
ToolCallTracker still runs, but notifications go nowhere (no IDE to receive them).

### Why return empty dict from discover_tools?
Local mode has no IDE to discover tools from. Extensions are IDE-only feature.
