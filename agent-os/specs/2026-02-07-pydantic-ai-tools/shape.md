# Shape: Pydantic AI Tool Implementation

## Scope

**In Scope:**

- All 6 remaining ACP Client methods as Pydantic AI tools
- Permission flow for `write_file` and `run_command`
- FakeClient terminal method implementations for testing
- Comprehensive test coverage for all new tools

**Out of Scope:**

- PermissionBroker abstraction (use direct `Client.request_permission()` calls)
- Advanced terminal features (resize, input streaming)
- Batch operations (write multiple files, run multiple commands)
- Tool result caching or memoization

## Permission Flow Design

### Request Flow

```
Tool invoked
  ↓
tracker.start() → ToolCallStart notification
  ↓
Client.request_permission()
  ↓
Permission response received
  ↓
If outcome == "selected":
  Execute operation
  tracker.progress(status="completed") → ToolCallProgress notification
  tracker.forget()
  Return success message
Else:
  tracker.forget()
  Return denial message
```

### Permission Options

Use `default_permission_options()` which provides:

- "Allow" (outcome: AllowedOutcome)
- "Deny" (outcome: DeniedOutcome)

### Outcome Types

- `AllowedOutcome.outcome == "selected"` → proceed
- `DeniedOutcome.outcome == "cancelled"` → abort
- Any other outcome type → treat as denial

## Terminal Lifecycle

### FakeTerminal Structure

```python
@dataclass
class FakeTerminal:
    command: str
    args: list[str]
    output: str
    exit_code: int
```

### FakeClient Terminal State

- `terminals: dict[str, FakeTerminal]` — active terminals
- `_next_terminal_id: int` — counter for unique IDs
- `queue_terminal(command, output, exit_code)` — test helper

### Terminal ID Format

`term-{counter}` (e.g., `term-0`, `term-1`)

## Tool Signatures

### Permission-Required Tools

```python
async def write_file(ctx: RunContext[ACPDeps], path: str, content: str) -> str


    async def run_command(ctx: RunContext[ACPDeps], command: str,
                          args: list[str] | None = None, cwd: str | None = None) -> str
```

### Terminal Lifecycle Tools

```python
async def get_terminal_output(ctx: RunContext[ACPDeps], terminal_id: str) -> str


    async def release_terminal(ctx: RunContext[ACPDeps], terminal_id: str) -> str


    async def wait_for_terminal_exit(ctx: RunContext[ACPDeps], terminal_id: str) -> str


    async def kill_terminal(ctx: RunContext[ACPDeps], terminal_id: str) -> str
```

## Test Strategy

### Permission Tests

- Test approved flow: verify operation executes, lifecycle notifications sent
- Test denied flow: verify operation skips, denial message returned
- Use `FakeClient.queue_permission_selected()` / `queue_permission_cancelled()`

### Terminal Tests

- Test each lifecycle tool independently with pre-configured FakeTerminal
- Test `run_command` compound flow end-to-end
- Verify terminal state management (create, output, release)

### Coverage Goals

- All 6 new tools covered
- Both permission outcomes (allowed/denied) covered
- Terminal lifecycle state transitions covered
- Toolset composition verified (7 tools total)
