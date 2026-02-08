# References: Pydantic AI Structure (Phase 3.2)

## ACP Protocol Interfaces

**File:** `src/punie/acp/interfaces.py`

**Key Definitions:**

- `Agent` protocol (14 methods) — PunieAgent must implement all of these
- `Client` protocol (12 methods) — ACPToolset calls these

**Critical Methods for Phase 3.2:**

### Agent Protocol Methods (PunieAgent implements)

```python
async def initialize(...) -> InitializeResponse:
    """Initialize agent connection."""

async def new_session(...) -> NewSessionResponse:
    """Create new session, return session_id."""

async def prompt(
    prompt: list[TextContentBlock | ImageContentBlock | ...],
    session_id: str,
    **kwargs: Any,
) -> PromptResponse:
    """Process prompt and return response."""
```

Plus 11 other methods (list_sessions, load_session, fork_session, etc.) — these return simple defaults in Phase 3.2.

### Client Protocol Methods (ACPToolset calls)

```python
async def read_text_file(
    path: str,
    session_id: str,
    limit: int | None = None,
    line: int | None = None,
    **kwargs: Any,
) -> ReadTextFileResponse:
    """Read file contents from IDE."""

async def session_update(
    session_id: str,
    update: UserMessageChunk | AgentMessageChunk | ToolCallStart | ...,
    **kwargs: Any,
) -> None:
    """Send agent message/tool call update to IDE."""
```

**Reference Implementation:** `tests/fixtures/minimal_agent.py` (shows all 14 methods)

## Research Documentation

**File:** `docs/research/pydantic-ai.md`

**Key Sections:**

### AbstractToolset API

```python
from pydantic_ai import AbstractToolset, RunContext

class MyToolset(AbstractToolset[DepsType]):
    async def get_tools(
        self,
        ctx: RunContext[DepsType],
    ) -> list[ToolDefinition]:
        """Return tool definitions for this context."""
        return [
            ToolDefinition(
                name="tool_name",
                description="Tool description for LLM",
                parameters_json_schema={...},  # JSON Schema
                function=self._tool_impl,
            ),
        ]

    async def _tool_impl(
        self,
        ctx: RunContext[DepsType],
        **kwargs: Any,
    ) -> Any:
        """Tool implementation."""
        pass
```

### ACPDeps Example

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class ACPDeps:
    client_conn: Client      # ACP Client protocol reference
    session_id: str           # Current ACP session ID
    tracker: ToolCallTracker  # Tool call lifecycle manager
```

### Agent Creation

```python
from pydantic_ai import Agent

agent = Agent[ACPDeps, str](
    "test",  # or "openai:gpt-4", "anthropic:claude-3-5-sonnet"
    deps_type=ACPDeps,
    system_prompt="You are Punie, an AI coding assistant.",
    toolsets=[ACPToolset()],
)

result = await agent.arun(
    "Read /foo/bar.py and summarize it",
    deps=ACPDeps(client_conn=..., session_id=..., tracker=...),
)
```

## Testing Fakes

**File:** `src/punie/testing/fakes.py`

**FakeClient:**

```python
class FakeClient:
    def __init__(
        self,
        files: dict[str, str] | None = None,
        default_file_content: str = "default content",
    ):
        self.files = files or {}
        self.notifications: list[SessionNotification] = []
        self.permission_outcomes: list[RequestPermissionResponse] = []

    async def read_text_file(self, path: str, session_id: str, ...) -> ReadTextFileResponse:
        content = self.files.get(path, self.default_file_content)
        return ReadTextFileResponse(content=content)

    async def session_update(self, session_id: str, update: ...) -> None:
        self.notifications.append(SessionNotification(session_id=session_id, update=update))
```

**Usage in Tests:**

```python
def test_something():
    fake_client = FakeClient(files={"/test.py": "print('hello')"})
    deps = ACPDeps(client_conn=fake_client, session_id="test-1", tracker=ToolCallTracker())

    # Call code that uses deps
    # ...

    # Assert on fake_client.notifications
    assert len(fake_client.notifications) > 0
```

## Tool Call Tracking

**File:** `src/punie/acp/contrib/tool_calls.py`

**ToolCallTracker:**

```python
class ToolCallTracker:
    def start(
        self,
        external_id: str,
        *,
        title: str,
        kind: ToolKind | None = None,
        status: ToolCallStatus | None = "in_progress",
        content: Sequence[Any] | None = None,
        locations: Sequence[ToolCallLocation] | None = None,
        raw_input: Any = None,
        raw_output: Any = None,
    ) -> ToolCallStart:
        """Register a new tool call and return the tool_call notification."""

    def progress(
        self,
        external_id: str,
        *,
        title: Any = UNSET,
        status: Any = UNSET,
        content: Any = UNSET,
        ...
    ) -> ToolCallProgress:
        """Produce a tool_call_update message and merge it into the tracker."""

    def forget(self, external_id: str) -> None:
        """Remove a tracked tool call (e.g. after completion)."""
```

**Usage in ACPToolset:**

```python
async def read_file(self, ctx: RunContext[ACPDeps], path: str) -> str:
    # Start tracking
    start = ctx.deps.tracker.start(
        f"read_{path}",
        title=f"Reading {path}",
        kind="read",
    )
    await ctx.deps.client_conn.session_update(ctx.deps.session_id, start)

    # Do work
    response = await ctx.deps.client_conn.read_text_file(
        session_id=ctx.deps.session_id,
        path=path,
    )

    # Mark complete
    progress = ctx.deps.tracker.progress(f"read_{path}", status="completed")
    await ctx.deps.client_conn.session_update(ctx.deps.session_id, progress)

    return response.content
```

## ACP Schema Types

**File:** `src/punie/acp/schema.py`

**Key Types:**

- `ToolCallStart` — initial tool call notification
- `ToolCallProgress` — tool call update notification
- `AgentMessageChunk` — agent text message
- `ToolCallLocation` — file path + optional line/column
- `ToolKind` — "read", "edit", "write", "terminal", etc.
- `ToolCallStatus` — "in_progress", "completed", "failed"

**Usage:**

```python
from punie.acp.schema import ToolCallLocation, ToolCallStatus

location = ToolCallLocation(path="/foo/bar.py", line=42)
```

## Example Agent (MinimalAgent)

**File:** `tests/fixtures/minimal_agent.py`

**Purpose:** Template for PunieAgent implementation

**Key Points:**

- Shows all 14 Agent protocol methods
- `new_session()` uses sequential IDs (`"test-session-0"`, `"test-session-1"`)
- `prompt()` sends AgentMessageChunk via `session_update()`
- All other methods return minimal valid responses

**Copy from MinimalAgent:**

- Method signatures (exact parameter names/types)
- Default implementations for methods not needed in Phase 3.2
- Session ID generation pattern (adapt to `"punie-session-N"`)

## Roadmap Context

**File:** `agent-os/product/roadmap.md`

**Phase 3.2 Goals:**

- Perform minimal transition to Pydantic AI project structure
- Replace MinimalAgent with PunieAgent
- Prove end-to-end flow with one tool (read_file)
- Use TestModel (no real LLM)

**Phase 3.3 Goals (Deferred):**

- Add write_file tool with permission flow
- Add terminal tools
- Use permission_outcomes queue in FakeClient

**Phase 3.4 Goals (Deferred):**

- Convert to best-practices Pydantic AI project
- Configure real LLM models
- Production-ready agent configuration

## External Dependencies

**Pydantic AI:**

- Package: `pydantic-ai`
- Version: `>=0.1.0` (TBD during implementation)
- Docs: https://ai.pydantic.dev/
- Local checkout: `~/PycharmProjects/pydantic-ai/`

**Key APIs Needed:**

- `pydantic_ai.Agent[DepsType, OutputType]`
- `pydantic_ai.AbstractToolset[DepsType]`
- `pydantic_ai.RunContext[DepsType]`
- `pydantic_ai.ToolDefinition`
- Model name `"test"` for TestModel (no LLM)

## Testing Strategy

**Test File:** `tests/test_pydantic_agent.py` (to be created)

**Test Structure:**

1. Protocol satisfaction test (first)
2. ACPDeps tests (frozen, field access)
3. ACPToolset tests (get_tools, tool implementations)
4. PunieAgent tests (initialize, new_session, prompt)

**All tests use:**

- `FakeClient` (no mocks)
- `ToolCallTracker` (real instance)
- Function-based tests (no classes)
- Pytest fixtures for setup

**Integration Tests:**

Existing integration tests in `tests/test_stdio_integration.py` and `tests/test_dual_protocol.py` will verify PunieAgent works with stdio transport. No new integration tests needed for Phase 3.2.
