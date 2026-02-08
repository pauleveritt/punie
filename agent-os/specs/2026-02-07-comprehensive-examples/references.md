# References: Comprehensive Examples

## Core Reference Files

### `examples/hello_world.py`

**Why:** Template convention for all examples.

Shows the required structure:
- Module docstring explaining the example
- `main()` function with assertions
- `if __name__ == "__main__":` guard

### `tests/test_examples.py`

**Why:** Auto-discovery mechanism for examples.

- Parametrized test that globs `examples/*.py`
- Handles both sync and async `main()` functions
- Uses `runpy.run_path()` for standalone execution
- Excludes `__init__.py` files

### `tests/acp_helpers.py`

**Why:** Provides `_Server`, `FakeAgent`, `FakeClient` for example 07.

- `_Server` — Async context manager for TCP loopback server
- `FakeAgent` — Agent-side fake with message handling
- `FakeClient` — Client-side fake with tool execution
- Used for full connection lifecycle without external dependencies

### `.venv/lib/python3.14/site-packages/acp/helpers.py`

**Why:** Factory functions for ACP schema construction.

Key functions:
- `text_block()` → TextContentBlock
- `start_tool_call()` → ToolCallStart
- `update_tool_call()` → ToolCallProgress
- `start_read_tool_call()` → ToolCallStart with Read kind
- `start_edit_tool_call()` → ToolCallStart with Edit kind
- `tool_diff_content()` → FileDiff content blocks
- `session_notification()` → SessionUpdateResponse wrapper
- `update_plan()` → PlanUpdate
- `plan_entry()` → PlanEntry
- `update_agent_message_text()` → AgentMessageChunk
- `update_user_message_text()` → UserMessageChunk

### `.venv/lib/python3.14/site-packages/acp/contrib/`

**Why:** High-level utilities for agent implementations.

Key modules:
- `session_accumulator.py` — `SessionAccumulator` class for aggregating session state
- `tool_call_tracker.py` — `ToolCallTracker` class for managing tool call lifecycle
- `permission_utils.py` — `default_permission_options()` factory

### `tests/test_acp_sdk.py`

**Why:** Reference patterns for ACP primitive usage.

Shows how to:
- Construct and validate schema models
- Use factory functions correctly
- Build tool calls with locations and raw_input
- Create session notifications
- Wire connections and handle protocol handshake

## ACP SDK Documentation

### Schema Models

Located in `.venv/lib/python3.14/site-packages/acp/schema.py`:
- `InitializeResponse` — Protocol handshake response
- `TextContentBlock`, `ImageContentBlock` — Content block types
- `ToolCallStart`, `ToolCallProgress`, `ToolCallUpdate` — Tool call lifecycle
- `AgentMessageChunk`, `UserMessageChunk` — Session update chunks
- `PlanEntry`, `PlanUpdate` — Plan management
- `PermissionOption` — Permission request options
- `ToolCallLocation` — File/line location info

### Connection Classes

Located in `.venv/lib/python3.14/site-packages/acp/core.py`:
- `AgentSideConnection` — Agent-side protocol handler
- `ClientSideConnection` — Client-side protocol handler
- Both handle JSON-RPC framing over async streams

## External Dependencies

- **Pydantic** — All schema models use Pydantic v2
- **asyncio** — Connection lifecycle and stream handling
- **typing_extensions** — TypedDict, Literal for schema definitions

## Aspirational References

### Example 08: Pydantic AI Integration

**Conceptual model:**
```python
from pydantic_ai import Agent
# Future: ACP tool adapter for Pydantic AI agents
# Allows Pydantic AI to delegate tool execution to PyCharm
```

Research: `agent-os/specs/2026-02-06-research-pydantic-ai-acp/`

### Example 09: Dynamic Tool Discovery

**Conceptual model:**
```python
# Future: Protocol extension for tool discovery
# IDE advertises available tools, agent queries at runtime
```

Tool kinds enumerated in `acp.schema.ToolKind`.
