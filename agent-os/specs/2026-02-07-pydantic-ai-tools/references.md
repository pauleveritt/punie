# Reference Files

## Core Implementation Files

### `src/punie/agent/toolset.py`
Existing `read_file` tool demonstrates the pattern to follow:
- Uses `RunContext[ACPDeps]` for dependency injection
- Accesses client via `ctx.deps.client_conn`
- Uses tracker for lifecycle notifications
- Returns string results

**Key sections:**
- Lines 15-35: `read_file` implementation
- Line 38: `create_toolset()` composition

### `src/punie/acp/interfaces.py`
Client protocol defines all method signatures:
- Lines 76-146: Terminal methods, permission flow, file operations

**Methods to implement:**
- `write_text_file()` (lines 89-90)
- `create_terminal()` (lines 110-114)
- `terminal_output()` (lines 116-119)
- `wait_for_terminal_exit()` (lines 121-124)
- `release_terminal()` (lines 126-129)
- `kill_terminal()` (lines 131-134)
- `request_permission()` (lines 136-141)

### `src/punie/acp/contrib/permissions.py`
Permission handling utilities:
- Line 15: `default_permission_options()` — returns list of PermissionOption
- Lines 30-55: `PermissionBroker` — helper class (not using, but shows pattern)

### `src/punie/acp/contrib/tool_calls.py`
Tool call tracking:
- Lines 20-35: `ToolCallTracker.start()` — create initial tool call
- Lines 37-52: `ToolCallTracker.progress()` — update tool call status
- Line 54: `ToolCallTracker.forget()` — cleanup

### `src/punie/acp/helpers.py`
Content construction helpers:
- `tool_content()` — wraps content list in ToolCallContent
- `text_block()` — creates TextBlock
- `tool_terminal_ref()` — creates TerminalReference

### `src/punie/acp/schema.py`
Response types and enums:
- Lines 250-255: `AllowedOutcome` (outcome="selected")
- Lines 257-262: `DeniedOutcome` (outcome="cancelled")
- Lines 180-185: `ToolKind` enum (read, edit, execute, search)
- Lines 320-325: `CreateTerminalResponse`
- Lines 327-332: `TerminalOutputResponse`
- Lines 334-339: `WaitForTerminalExitResponse`

## Testing Files

### `src/punie/testing/fakes.py`
FakeClient to extend:
- Lines 15-20: `__init__()` — add terminal state here
- Lines 65-90: Terminal method stubs (all raise NotImplementedError)
- Lines 45-55: Permission queue pattern to follow

**To implement:**
- `create_terminal()` — store in `self.terminals`, return response
- `terminal_output()` — fetch from `self.terminals`
- `wait_for_terminal_exit()` — fetch exit code
- `release_terminal()` — remove from dict
- `kill_terminal()` — remove from dict
- `queue_terminal()` — test helper method

### `tests/test_pydantic_agent.py`
Existing test patterns:
- Lines 10-25: Test setup with FakeClient and ACPDeps
- Lines 30-50: `test_read_file()` — shows tool testing pattern
- Lines 55-70: Permission testing pattern (if exists)

**To add:**
- Permission flow tests (approved/denied for write_file and run_command)
- Terminal lifecycle tests (get_output, release, wait, kill)
- Toolset composition test (verify 7 tools)

## Supporting Documentation

### `agent-os/product/roadmap.md`
Phase 3.3 definition — update status to "Complete" after implementation.

### `CLAUDE.md`
Project standards reference — mentions Astral tools, function-based tests, Sybil.
