# Plan: Port All ACP Client Tools to Pydantic AI (Roadmap 3.3)

## Context

Phase 3.2 established the adapter pattern: PunieAgent bridges ACP Agent protocol to Pydantic AI, with `read_file` as the sole tool. Phase 3.3 completes the toolset by adding all remaining ACP Client methods as Pydantic AI tools: `write_file` (with permission flow), `run_command` (with permission flow), and terminal lifecycle tools (`get_terminal_output`, `release_terminal`, `wait_for_terminal_exit`, `kill_terminal`).

The key challenge is **permission flow** — `write_file` and `run_command` must request user permission from the IDE via `Client.request_permission()` before executing, and handle denied/cancelled outcomes gracefully.

**Goal:** Expose all 6 remaining ACP Client methods as Pydantic AI tools, implement the permission flow, update FakeClient terminal stubs, and prove everything works with comprehensive tests.

## Architecture

### Tool Categories

**Permission-required tools** (new pattern):
1. `write_file(path, content)` → `Client.request_permission()` → `Client.write_text_file()`
2. `run_command(command, args, cwd)` → `Client.request_permission()` → `Client.create_terminal()` → `Client.wait_for_terminal_exit()` → `Client.terminal_output()`

**Direct tools** (no permission needed):
3. `get_terminal_output(terminal_id)` → `Client.terminal_output()`
4. `release_terminal(terminal_id)` → `Client.release_terminal()`
5. `wait_for_terminal_exit(terminal_id)` → `Client.wait_for_terminal_exit()`
6. `kill_terminal(terminal_id)` → `Client.kill_terminal()`

### Permission Flow

For `write_file` and `run_command`:
1. Start tracking tool call via `tracker.start()` → send `ToolCallStart` via `session_update`
2. Call `Client.request_permission()` with `default_permission_options()` from `punie.acp.contrib.permissions`
3. Check outcome: `AllowedOutcome` (proceed) or `DeniedOutcome` (return denial message)
4. Execute the actual operation
5. Report completion via `tracker.progress()` → send `ToolCallProgress` via `session_update`
6. Clean up via `tracker.forget()`

### FakeClient Terminal Support

Currently all 5 terminal methods in `FakeClient` raise `NotImplementedError`. They need in-memory implementations:
- `create_terminal()` → stores terminal in `self.terminals` dict, returns `CreateTerminalResponse(terminal_id=...)`
- `terminal_output()` → returns stored output
- `wait_for_terminal_exit()` → returns stored exit code
- `release_terminal()` / `kill_terminal()` → removes terminal from dict

## Tasks

See implementation tracking in roadmap.md Phase 3.3.

## Files Summary

| Action | Files |
|--------|-------|
| **Create (spec)** | `agent-os/specs/2026-02-07-pydantic-ai-tools/{plan,shape,standards,references}.md` |
| **Modify** | `src/punie/agent/toolset.py` (add 6 new tool functions, update `create_toolset()`) |
| **Modify** | `src/punie/testing/fakes.py` (implement FakeClient terminal methods) |
| **Modify** | `tests/test_pydantic_agent.py` (add ~9 new tests) |
| **Modify** | `agent-os/product/roadmap.md` (mark 3.3 complete) |

## Design Decisions

1. **No PermissionBroker** — Use `Client.request_permission()` directly in each tool rather than introducing the `PermissionBroker` helper class. Keeps tools self-contained and easier to test.

2. **Permission check via outcome type** — Check `perm_response.outcome.outcome == "selected"` for allowed, anything else is denied.

3. **run_command is a compound tool** — It calls `create_terminal` → `wait_for_terminal_exit` → `terminal_output` → `release_terminal` in sequence.

4. **FakeTerminal as a simple dataclass** — Just holds `command`, `args`, `output`, `exit_code` for test configuration.

5. **Tool call lifecycle for permission tools only** — `write_file` and `run_command` use tracker lifecycle. Direct terminal tools skip tracking as they're utility operations.
