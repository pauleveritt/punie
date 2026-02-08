# Phase 6.3: Local Tools - Shape

## Core Type: LocalClient

```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

@dataclass
class LocalClient:
    """Client protocol implementation using local filesystem and subprocess."""
    workspace: Path  # Root directory for file operations
    _terminals: dict[str, asyncio.subprocess.Process] = field(default_factory=dict, init=False)
    _agent: Any | None = field(default=None, init=False)  # Agent reference from on_connect
```

**Why not frozen:** Must track mutable subprocess state in `_terminals`.

## Protocol Implementation Map

| Client Method | LocalClient Implementation |
|--------------|---------------------------|
| `read_text_file` | `Path(workspace / path).read_text()` |
| `write_text_file` | `Path(workspace / path).write_text(content)` |
| `request_permission` | Auto-approve (return first option as selected) |
| `session_update` | No-op (or log for debugging) |
| `create_terminal` | `asyncio.create_subprocess_exec()` |
| `terminal_output` | Read from stored process stdout |
| `release_terminal` | Clean up process reference |
| `wait_for_terminal_exit` | `process.wait()` |
| `kill_terminal` | `process.kill()` |
| `discover_tools` | Return empty dict (no IDE discovery) |
| `ext_method` | Raise NotImplementedError |
| `ext_notification` | No-op |
| `on_connect` | Store agent reference |

## Terminal State Management

```python
_terminals: dict[str, asyncio.subprocess.Process]
```

Each terminal_id maps to a subprocess.Process. The process is:
1. Created in `create_terminal`
2. Queried in `terminal_output`
3. Awaited in `wait_for_terminal_exit`
4. Killed in `kill_terminal`
5. Removed in `release_terminal`

## File Path Resolution

All file operations resolve paths relative to `workspace`:

```python
def _resolve_path(self, path: str) -> Path:
    """Resolve path relative to workspace."""
    full_path = self.workspace / path
    # Phase 6.5 will add safety check: full_path.is_relative_to(workspace)
    return full_path
```

## Permission Handling

Since there's no IDE to prompt the user, `request_permission` auto-approves:

```python
async def request_permission(
    self,
    options: list[PermissionOption],
    session_id: str,
    tool_call: ToolCallUpdate,
    **kwargs: Any,
) -> RequestPermissionResponse:
    """Auto-approve by selecting first option."""
    return RequestPermissionResponse(
        selected_option_indices=[0] if options else []
    )
```

## Session Updates

`session_update` is called by `ToolCallTracker` to send notifications. LocalClient makes this a no-op since there's no IDE to receive notifications:

```python
async def session_update(
    self,
    session_id: str,
    update: UserMessageChunk | AgentMessageChunk | ...,
    **kwargs: Any,
) -> None:
    """No-op: no IDE to receive notifications."""
    pass
```

## Factory Integration

```python
def create_local_agent(
    model: KnownModelName | Model = "local",
    workspace: Path | None = None,
) -> tuple[Agent[ACPDeps, str], LocalClient]:
    """Create a Pydantic AI agent with local filesystem tools.

    Returns:
        (agent, client) tuple so callers can construct ACPDeps per prompt.
    """
    workspace = workspace or Path.cwd()
    client = LocalClient(workspace=workspace)
    agent = create_pydantic_agent(model=model)
    # Register tools happen in create_pydantic_agent
    return agent, client
```

## CLI Integration

When `punie serve --model local` is run without ACP stdio:
1. Create LocalClient with cwd as workspace
2. Create agent via `create_local_agent`
3. Run agent with ACPDeps(client, session_id, tracker)

No waiting for ACP connection needed.
