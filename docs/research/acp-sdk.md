# ACP Python SDK Reference

This document provides a comprehensive reference for the Agent Communication Protocol (ACP) Python SDK, focusing on
areas critical for Punie's implementation.

## Overview

**What is ACP?**

ACP (Agent Communication Protocol) is a stdio-based JSON-RPC 2.0 protocol developed by Zed Industries. It enables
clients (editors, IDEs) to orchestrate AI agents through a standardized communication protocol.

**SDK Details:**

- Version: v0.7.1
- PyPI Package: `agent-client-protocol`
- Runtime dependency: `pydantic>=2.7`
- Local checkout: `~/PycharmProjects/python-acp-sdk/`

**Architecture:**

- Bidirectional JSON-RPC 2.0 over stdio
- Agent implements Agent Protocol (responds to client requests)
- Client implements Client Protocol (provides IDE operations)
- Both sides can make requests and send notifications

## Agent Protocol

The Agent Protocol defines methods that agents must implement to respond to client requests.

**All Methods from `acp.interfaces.Agent`:**

```text
async def initialize(
    protocol_version: int,
    client_capabilities: ClientCapabilities | None = None,
    client_info: Implementation | None = None,
    **kwargs: Any,
) -> InitializeResponse

async def new_session(
    cwd: str,
    mcp_servers: list[HttpMcpServer | SseMcpServer | McpServerStdio],
    **kwargs: Any,
) -> NewSessionResponse

async def load_session(
    cwd: str,
    mcp_servers: list[HttpMcpServer | SseMcpServer | McpServerStdio],
    session_id: str,
    **kwargs: Any,
) -> LoadSessionResponse | None

async def list_sessions(
    cursor: str | None = None,
    cwd: str | None = None,
    **kwargs: Any,
) -> ListSessionsResponse

async def set_session_mode(
    mode_id: str,
    session_id: str,
    **kwargs: Any,
) -> SetSessionModeResponse | None

async def set_session_model(
    model_id: str,
    session_id: str,
    **kwargs: Any,
) -> SetSessionModelResponse | None

async def authenticate(
    method_id: str,
    **kwargs: Any,
) -> AuthenticateResponse | None

async def prompt(
    prompt: list[
        TextContentBlock
        | ImageContentBlock
        | AudioContentBlock
        | ResourceContentBlock
        | EmbeddedResourceContentBlock
    ],
    session_id: str,
    **kwargs: Any,
) -> PromptResponse

async def fork_session(
    cwd: str,
    session_id: str,
    mcp_servers: list[HttpMcpServer | SseMcpServer | McpServerStdio] | None = None,
    **kwargs: Any,
) -> ForkSessionResponse

async def resume_session(
    cwd: str,
    session_id: str,
    mcp_servers: list[HttpMcpServer | SseMcpServer | McpServerStdio] | None = None,
    **kwargs: Any,
) -> ResumeSessionResponse

async def cancel(
    session_id: str,
    **kwargs: Any,
) -> None

async def ext_method(
    method: str,
    params: dict[str, Any],
) -> dict[str, Any]

async def ext_notification(
    method: str,
    params: dict[str, Any],
) -> None

def on_connect(
    conn: Client,
) -> None
```

## Client Protocol

The Client Protocol defines operations that the IDE/client provides to the agent.

**All Methods from `acp.interfaces.Client`:**

```text
async def request_permission(
    options: list[PermissionOption],
    session_id: str,
    tool_call: ToolCallUpdate,
    **kwargs: Any,
) -> RequestPermissionResponse

async def session_update(
    session_id: str,
    update: UserMessageChunk
        | AgentMessageChunk
        | AgentThoughtChunk
        | ToolCallStart
        | ToolCallProgress
        | AgentPlanUpdate
        | AvailableCommandsUpdate
        | CurrentModeUpdate
        | ConfigOptionUpdate
        | SessionInfoUpdate,
    **kwargs: Any,
) -> None

async def write_text_file(
    content: str,
    path: str,
    session_id: str,
    **kwargs: Any,
) -> WriteTextFileResponse | None

async def read_text_file(
    path: str,
    session_id: str,
    limit: int | None = None,
    line: int | None = None,
    **kwargs: Any,
) -> ReadTextFileResponse

async def create_terminal(
    command: str,
    session_id: str,
    args: list[str] | None = None,
    cwd: str | None = None,
    env: list[EnvVariable] | None = None,
    output_byte_limit: int | None = None,
    **kwargs: Any,
) -> CreateTerminalResponse

async def terminal_output(
    session_id: str,
    terminal_id: str,
    **kwargs: Any,
) -> TerminalOutputResponse

async def release_terminal(
    session_id: str,
    terminal_id: str,
    **kwargs: Any,
) -> ReleaseTerminalResponse | None

async def wait_for_terminal_exit(
    session_id: str,
    terminal_id: str,
    **kwargs: Any,
) -> WaitForTerminalExitResponse

async def kill_terminal(
    session_id: str,
    terminal_id: str,
    **kwargs: Any,
) -> KillTerminalCommandResponse | None

async def ext_method(
    method: str,
    params: dict[str, Any],
) -> dict[str, Any]

async def ext_notification(
    method: str,
    params: dict[str, Any],
) -> None

def on_connect(
    conn: Agent,
) -> None
```

## Tool Implementation (Deep Dive)

**This is the critical section for Punie's implementation.** ACP's tool model is fundamentally different from MCP and
Pydantic AI.

### 1. Conceptual Model

**ACP tools are NOT pre-registered callable functions.** Unlike MCP (Model Context Protocol) or Pydantic AI, where tools
are defined upfront with schemas, ACP tools are **ephemeral actions** that the agent reports to the client via session
update notifications.

Key differences:

- **No tool registry** — The agent doesn't register tools at initialization
- **Dynamic reporting** — Tools are announced when the agent decides to use them
- **Agent-defined** — The agent controls what qualifies as a "tool" and how to report it
- **Notification-based** — Tool execution is communicated through `session_update()` notifications

### 2. Complete Type Hierarchy

**ToolKind (Literal Type):**

```text
ToolKind = Literal[
    "read",          # Reading files or data
    "edit",          # Editing or writing files
    "delete",        # Deleting files or data
    "move",          # Moving or renaming files
    "search",        # Searching for information
    "execute",       # Running commands or processes
    "think",         # Internal reasoning or planning
    "fetch",         # Fetching remote data
    "switch_mode",   # Changing agent mode
    "other"          # Other operations
]
```

**ToolCallStatus (Literal Type):**

```text
ToolCallStatus = Literal[
    "pending",       # Tool call announced, awaiting execution
    "in_progress",   # Tool is currently executing
    "completed",     # Tool finished successfully
    "failed"         # Tool execution failed
]
```

**ToolCallLocation:**

```text
class ToolCallLocation(BaseModel):
    path: str                    # File path being accessed/modified
    line: Optional[int] = None   # Optional line number (>= 0)
    field_meta: Optional[Dict[str, Any]] = None  # Extensibility
```

**ToolCall (Base Model):**

```text
class ToolCall(BaseModel):
    tool_call_id: str                                # Unique identifier
    title: str                                       # Human-readable description
    kind: Optional[ToolKind] = None                  # Category of operation
    status: Optional[ToolCallStatus] = None          # Execution status
    content: Optional[List[ToolCallContentVariant]]  # Results/progress
    locations: Optional[List[ToolCallLocation]]      # Affected files
    raw_input: Any = None                            # Original parameters
    raw_output: Any = None                           # Final result
    field_meta: Optional[Dict[str, Any]] = None      # Extensibility
```

**ToolCallUpdate (All Optional Fields):**

```text
class ToolCallUpdate(BaseModel):
    tool_call_id: str                                # Required: identifies the call
    title: Optional[str] = None                      # Update title
    kind: Optional[ToolKind] = None                  # Update kind
    status: Optional[ToolCallStatus] = None          # Update status
    content: Optional[List[ToolCallContentVariant]]  # Update content
    locations: Optional[List[ToolCallLocation]]      # Update locations
    raw_input: Any = None                            # Update input
    raw_output: Any = None                           # Update output
    field_meta: Optional[Dict[str, Any]] = None      # Extensibility
```

**ToolCallStart (Session Update Notification):**

```text
class ToolCallStart(ToolCall):
    session_update: Literal["tool_call"]  # Discriminator for session updates
    # Inherits all ToolCall fields
```

**ToolCallProgress (Session Update Notification):**

```text
class ToolCallProgress(ToolCallUpdate):
    session_update: Literal["tool_call_update"]  # Discriminator
    # Inherits all ToolCallUpdate fields (all optional except tool_call_id)
```

### 3. Tool Call Content Variants

Tool calls can produce three types of content:

**ContentToolCallContent (type="content"):**

Wraps standard content blocks (text, images, audio, resources).

```text
class ContentToolCallContent(Content):
    type: Literal["content"]
    content: TextContentBlock
           | ImageContentBlock
           | AudioContentBlock
           | ResourceContentBlock
           | EmbeddedResourceContentBlock
```

**FileEditToolCallContent (type="diff"):**

Represents file modifications with old/new content.

```text
class FileEditToolCallContent(Diff):
    type: Literal["diff"]
    path: str                     # File being modified
    new_text: str                 # Content after modification
    old_text: Optional[str] = None  # Original content (None for new files)
```

**TerminalToolCallContent (type="terminal"):**

References a terminal process.

```text
class TerminalToolCallContent(Terminal):
    type: Literal["terminal"]
    terminal_id: str  # ID from create_terminal response
```

### 4. Complete Tool Call Lifecycle

The lifecycle has four distinct phases. This example is based on `tests/test_rpc.py` `_ExampleAgent`:

#### Phase 1: Announce Intent (ToolCallStart)

The agent announces it will perform a tool call via `session_update()`:

```text
await client_conn.session_update(
    session_id,
    ToolCallStart(
        session_update="tool_call",
        tool_call_id="call_1",
        title="Modifying configuration",
        kind="edit",
        status="pending",
        locations=[ToolCallLocation(path="/project/config.json")],
        raw_input={"path": "/project/config.json"},
    ),
)
```

**Key points:**

- `session_update="tool_call"` discriminator identifies this as a ToolCallStart
- `tool_call_id` uniquely identifies this tool call for future updates
- `title` is shown to the user in the IDE
- `status="pending"` indicates the tool hasn't started yet
- `locations` shows which files will be affected
- `raw_input` captures the parameters (useful for permission UI)

#### Phase 2: Request Permission (Blocking RPC)

The agent sends a **blocking RPC request** to get user approval:

```text
response = await client_conn.request_permission(
    session_id=session_id,
    tool_call=ToolCallUpdate(
        tool_call_id="call_1",
        title="Modifying configuration",
        kind="edit",
        status="pending",
        locations=[ToolCallLocation(path="/project/config.json")],
        raw_input={"path": "/project/config.json"},
    ),
    options=[
        PermissionOption(
            kind="allow_once",
            name="Allow",
            option_id="allow"
        ),
        PermissionOption(
            kind="reject_once",
            name="Reject",
            option_id="reject"
        ),
    ],
)
```

**Response handling:**

```text
if isinstance(response.outcome, AllowedOutcome):
    # User approved, proceed with tool execution
    selected_option_id = response.outcome.option_id
elif isinstance(response.outcome, DeniedOutcome):
    # User rejected, skip tool execution
    pass
```

**PermissionOption kinds:**

- `allow_once` — Allow this specific operation
- `allow_always` — Allow this operation for the entire session
- `reject_once` — Reject this specific operation
- `reject_always` — Never allow this operation in this session

#### Phase 3: Report Progress (ToolCallProgress)

The agent can send multiple progress updates (optional, repeatable):

```text
await client_conn.session_update(
    session_id,
    ToolCallProgress(
        session_update="tool_call_update",
        tool_call_id="call_1",
        status="in_progress",
        content=[
            ContentToolCallContent(
                type="content",
                content=TextContentBlock(
                    type="text",
                    text="Reading configuration file..."
                )
            )
        ],
    ),
)
```

**Key points:**

- Only `tool_call_id` is required — all other fields are optional
- Non-None fields **replace** the corresponding fields from ToolCallStart
- This is not a merge — None fields are ignored, non-None fields overwrite

#### Phase 4: Report Completion (Final ToolCallProgress)

The agent sends a final update with `status="completed"` or `status="failed"`:

```text
await client_conn.session_update(
    session_id,
    ToolCallProgress(
        session_update="tool_call_update",
        tool_call_id="call_1",
        status="completed",
        raw_output={"success": True},
        content=[
            FileEditToolCallContent(
                type="diff",
                path="/project/config.json",
                old_text='{"debug": false}',
                new_text='{"debug": true}',
            )
        ],
    ),
)
```

**Key points:**

- `status="completed"` signals successful execution
- `raw_output` captures the final result (for logging, debugging)
- `content` can show diffs, terminal output, or text results

### 5. Wire Format Examples

These JSON examples are from `tests/golden/` test fixtures:

**ToolCallStart (session_update_tool_call_read.json):**

```
{
  "jsonrpc": "2.0",
  "method": "acp/notification/session_update",
  "params": {
    "sessionId": "sess_123",
    "update": {
      "sessionUpdate": "tool_call",
      "toolCallId": "read_001",
      "title": "Reading file",
      "kind": "read",
      "status": "pending",
      "locations": [{"path": "/src/main.py"}],
      "rawInput": {"path": "/src/main.py"}
    }
  }
}
```

**ToolCallProgress with Content (session_update_tool_call_update_content.json):**

```
{
  "jsonrpc": "2.0",
  "method": "acp/notification/session_update",
  "params": {
    "sessionId": "sess_123",
    "update": {
      "sessionUpdate": "tool_call_update",
      "toolCallId": "read_001",
      "status": "in_progress",
      "content": [
        {
          "type": "content",
          "content": {
            "type": "text",
            "text": "File contents: ..."
          }
        }
      ]
    }
  }
}
```

**ToolCallProgress with Completion (session_update_tool_call_update_more_fields.json):**

```
{
  "jsonrpc": "2.0",
  "method": "acp/notification/session_update",
  "params": {
    "sessionId": "sess_123",
    "update": {
      "sessionUpdate": "tool_call_update",
      "toolCallId": "read_001",
      "status": "completed",
      "rawOutput": {"lines": 42, "bytes": 1024}
    }
  }
}
```

### 6. Helper Functions

The `acp.helpers` module provides builder functions for common patterns:

**start_tool_call:**

```text
def start_tool_call(
    tool_call_id: str,
    title: str,
    *,
    kind: ToolKind | None = None,
    status: ToolCallStatus | None = None,
    content: Sequence[ToolCallContentVariant] | None = None,
    locations: Sequence[ToolCallLocation] | None = None,
    raw_input: Any | None = None,
    raw_output: Any | None = None,
) -> ToolCallStart
```

**start_read_tool_call:**

Auto-sets `kind="read"`, `status="pending"`, and populates `locations` and `raw_input`:

```text
def start_read_tool_call(
    tool_call_id: str,
    title: str,
    path: str,
    *,
    extra_options: Sequence[ToolCallContentVariant] | None = None,
) -> ToolCallStart
```

**start_edit_tool_call:**

Auto-sets `kind="edit"`, `status="pending"`, and populates `locations` and `raw_input`:

```text
def start_edit_tool_call(
    tool_call_id: str,
    title: str,
    path: str,
    content: Any,
    *,
    extra_options: Sequence[ToolCallContentVariant] | None = None,
) -> ToolCallStart
```

**update_tool_call:**

```text
def update_tool_call(
    tool_call_id: str,
    *,
    title: str | None = None,
    kind: ToolKind | None = None,
    status: ToolCallStatus | None = None,
    content: Sequence[ToolCallContentVariant] | None = None,
    locations: Sequence[ToolCallLocation] | None = None,
    raw_input: Any | None = None,
    raw_output: Any | None = None,
) -> ToolCallProgress
```

**tool_content:**

Wraps a content block in ContentToolCallContent:

```text
def tool_content(
    block: ContentBlock
) -> ContentToolCallContent
```

**tool_diff_content:**

Creates a FileEditToolCallContent:

```text
def tool_diff_content(
    path: str,
    new_text: str,
    old_text: str | None = None
) -> FileEditToolCallContent
```

**tool_terminal_ref:**

Creates a TerminalToolCallContent:

```text
def tool_terminal_ref(
    terminal_id: str
) -> TerminalToolCallContent
```

### 7. ToolCallTracker (Contrib)

Server-side utility for managing tool call state across multiple concurrent operations.

**Purpose:** Track multiple tool calls in progress, generate IDs, accumulate streaming content.

**Key Methods:**

```text
class ToolCallTracker:
    def __init__(
        self,
        *,
        id_factory: Callable[[], str] | None = None
    ) -> None:
        # Default id_factory: lambda: uuid.uuid4().hex
        pass

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
        """Register new tool call, auto-generate ACP tool_call_id.

        Args:
            external_id: Your internal identifier (e.g., "read_config")
            title: Display name for the user

        Returns:
            ToolCallStart ready to send via session_update()
        """
        pass

    def progress(
        self,
        external_id: str,
        *,
        title: Any = UNSET,
        kind: Any = UNSET,
        status: Any = UNSET,
        content: Any = UNSET,
        locations: Any = UNSET,
        raw_input: Any = UNSET,
        raw_output: Any = UNSET,
    ) -> ToolCallProgress:
        """Update tracked state and return ToolCallProgress notification.

        Only non-UNSET fields are included in the update.
        """
        pass

    def append_stream_text(
        self,
        external_id: str,
        text: str,
        *,
        title: Any = UNSET,
        status: Any = UNSET,
    ) -> ToolCallProgress:
        """Accumulate streaming text into ContentToolCallContent.

        Maintains internal buffer, replaces content field on each call.
        """
        pass

    def forget(
        self,
        external_id: str
    ) -> None:
        """Remove tracked state (e.g., after completion)."""
        pass

    def view(
        self,
        external_id: str
    ) -> TrackedToolCallView:
        """Return immutable snapshot of current state."""
        pass

    def tool_call_model(
        self,
        external_id: str
    ) -> ToolCallUpdate:
        """Return deep copy suitable for permission requests."""
        pass
```

**Usage Pattern:**

```text
tracker = ToolCallTracker()

# Start
start_notification = tracker.start(
    "my_read_1",
    title="Reading configuration",
    kind="read",
    locations=[ToolCallLocation(path="/app/config.json")],
)
await client_conn.session_update(session_id, start_notification)

# Progress
progress_notification = tracker.progress(
    "my_read_1",
    status="in_progress",
)
await client_conn.session_update(session_id, progress_notification)

# Stream text
for chunk in stream:
    update = tracker.append_stream_text("my_read_1", chunk)
    await client_conn.session_update(session_id, update)

# Complete
final = tracker.progress(
    "my_read_1",
    status="completed",
    raw_output={"bytes": 1024},
)
await client_conn.session_update(session_id, final)

tracker.forget("my_read_1")
```

### 8. PermissionBroker (Contrib)

Coordinates permission requests with tracked tool calls.

**Purpose:** Simplify requesting permission by auto-populating tool_call from ToolCallTracker.

**Constructor:**

```text
class PermissionBroker:
    def __init__(
        self,
        session_id: str,
        requester: Callable[[RequestPermissionRequest], Awaitable[RequestPermissionResponse]],
        *,
        tracker: ToolCallTracker | None = None,
        default_options: Sequence[PermissionOption] | None = None,
    ) -> None:
        pass
```

**Key Method:**

```text
async def request_for(
    self,
    external_id: str,
    *,
    description: str | None = None,
    options: Sequence[PermissionOption] | None = None,
    content: Sequence[Any] | None = None,
    tool_call: ToolCallUpdate | None = None,
) -> RequestPermissionResponse:
    """Request permission for a tracked tool call.

    Args:
        external_id: ToolCallTracker external ID
        description: Optional description appended as text content
        options: Override default permission options
        content: Additional content blocks
        tool_call: Explicit ToolCallUpdate (skips tracker lookup)

    Returns:
        AllowedOutcome or DeniedOutcome
    """
    pass
```

**Default Options:**

```text
def default_permission_options() -> tuple[
    PermissionOption,
    PermissionOption,
    PermissionOption,
]:
    return (
        PermissionOption(option_id="approve", name="Approve", kind="allow_once"),
        PermissionOption(option_id="approve_for_session", name="Approve for session", kind="allow_always"),
        PermissionOption(option_id="reject", name="Reject", kind="reject_once"),
    )
```

**Usage Pattern:**

```text
tracker = ToolCallTracker()
broker = PermissionBroker(
    session_id="sess_1",
    requester=client_conn.request_permission,
    tracker=tracker,
)

# Start tool call
start = tracker.start("edit_1", title="Edit config", kind="edit")
await client_conn.session_update(session_id, start)

# Request permission (auto-populates from tracker)
outcome = await broker.request_for(
    "edit_1",
    description="This will modify the main configuration file.",
)

if isinstance(outcome.outcome, AllowedOutcome):
    # Proceed with edit
    pass
```

### 9. SessionAccumulator (Contrib)

Client-side utility for merging session update notifications into a coherent state snapshot.

**Purpose:** Track all tool calls, plan entries, messages as they arrive via `session_update()` notifications.

**Key Behavior:**

- **ToolCallStart** → Creates `_MutableToolCallState`
- **ToolCallProgress** → Merges non-None fields into existing state
- **AgentPlanUpdate** → Replaces plan entries list
- **CurrentModeUpdate** → Updates current mode ID
- **AvailableCommandsUpdate** → Replaces commands list
- **Message chunks** → Appends to chronological message lists

**Key Methods:**

```text
class SessionAccumulator:
    def __init__(
        self,
        *,
        auto_reset_on_session_change: bool = True
    ) -> None:
        pass

    def apply(
        self,
        notification: SessionNotification
    ) -> SessionSnapshot:
        """Merge notification into state, return new snapshot."""
        pass

    def snapshot(self) -> SessionSnapshot:
        """Return immutable snapshot of current state."""
        pass

    def subscribe(
        self,
        callback: Callable[[SessionSnapshot, SessionNotification], None]
    ) -> Callable[[], None]:
        """Register callback for every new snapshot.

        Returns unsubscribe function.
        """
        pass

    def reset(self) -> None:
        """Clear all accumulated state."""
        pass
```

**SessionSnapshot:**

```text
class SessionSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    session_id: str
    tool_calls: dict[str, ToolCallView]       # Merged tool call states
    plan_entries: tuple[PlanEntry, ...]       # Current plan
    current_mode_id: str | None               # Agent mode
    available_commands: tuple[AvailableCommand, ...]
    user_messages: tuple[UserMessageChunk, ...]      # Chronological
    agent_messages: tuple[AgentMessageChunk, ...]    # Chronological
    agent_thoughts: tuple[AgentThoughtChunk, ...]    # Chronological
```

**ToolCallView:**

```text
class ToolCallView(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_call_id: str
    title: str | None
    kind: ToolKind | None
    status: ToolCallStatus | None
    content: tuple[Any, ...] | None
    locations: tuple[ToolCallLocation, ...] | None
    raw_input: Any
    raw_output: Any
```

**Usage Pattern:**

```text
accumulator = SessionAccumulator()

# Subscribe to updates
def on_update(snapshot: SessionSnapshot, notification: SessionNotification):
    print(f"Tool calls: {len(snapshot.tool_calls)}")
    print(f"Messages: {len(snapshot.agent_messages)}")

unsubscribe = accumulator.subscribe(on_update)

# Apply notifications as they arrive
for notification in notifications:
    snapshot = accumulator.apply(notification)

    # Access merged state
    for tool_call_id, tool_call in snapshot.tool_calls.items():
        print(f"{tool_call_id}: {tool_call.status}")
```

## SDK Package Structure

```
acp/
├── schema.py              # Auto-generated Pydantic models from schema.json
├── interfaces.py          # Agent and Client Protocol classes
├── core.py                # run_agent(), connect_to_agent()
├── connection.py          # JSON-RPC 2.0 connection handling
├── helpers.py             # Builder functions (start_tool_call, etc.)
├── utils.py               # Internal utilities
├── stdio.py               # stdio_streams(), spawn_agent_process(), spawn_client_process()
├── agent/                 # Agent-side connection and routing
│   ├── connection.py
│   └── router.py
├── client/                # Client-side connection and routing
│   ├── connection.py
│   └── router.py
└── contrib/               # Optional utilities
    ├── tool_calls.py      # ToolCallTracker
    ├── permissions.py     # PermissionBroker
    └── session_state.py   # SessionAccumulator
```

## Relevance to Punie

**Punie implements the ACP Agent Protocol** — PyCharm (or other IDE) is the ACP Client.

**Critical Integration Points:**

1. **Tool Calls Are How Punie Reports IDE Operations**
    - When Punie needs to read a file, it calls `client_conn.read_text_file()`
    - But it ALSO reports this as a tool call via `session_update(ToolCallStart(...))`
    - PyCharm sees both: the file read request AND the tool call notification
    - The tool call notification provides context for the IDE UI

2. **Permission Flow**
    - Before executing destructive operations (edit, delete), Punie sends `ToolCallStart`
    - Then calls `client_conn.request_permission()` (blocking RPC)
    - User approves/rejects in PyCharm UI
    - Punie proceeds or aborts based on response

3. **Progress Streaming**
    - Long-running operations report progress via `ToolCallProgress`
    - PyCharm can show progress bars, status updates, streaming output
    - Uses `ToolCallTracker.append_stream_text()` for streaming text

4. **State Management**
    - **Agent side (Punie):** Use `ToolCallTracker` to manage concurrent tool calls
    - **Client side (PyCharm):** Use `SessionAccumulator` to merge notifications into UI state

**Recommended Pattern for Punie:**

```text
class PunieAgent(Agent):
    def __init__(self):
        self.tracker = ToolCallTracker()
        self.broker = None  # Set after on_connect
        self.client_conn = None

    def on_connect(self, conn: Client):
        self.client_conn = conn
        self.broker = PermissionBroker(
            session_id=self.session_id,
            requester=conn.request_permission,
            tracker=self.tracker,
        )

    async def read_file_tool(self, path: str):
        # Announce intent
        start = self.tracker.start(
            f"read_{path}",
            title=f"Reading {path}",
            kind="read",
            locations=[ToolCallLocation(path=path)],
        )
        await self.client_conn.session_update(self.session_id, start)

        # Perform read (no permission needed for reads)
        response = await self.client_conn.read_text_file(
            session_id=self.session_id,
            path=path,
        )

        # Report completion
        done = self.tracker.progress(
            f"read_{path}",
            status="completed",
            raw_output={"bytes": len(response.content)},
        )
        await self.client_conn.session_update(self.session_id, done)

        return response.content

    async def edit_file_tool(self, path: str, new_content: str):
        # Announce intent
        start = self.tracker.start(
            f"edit_{path}",
            title=f"Editing {path}",
            kind="edit",
            locations=[ToolCallLocation(path=path)],
        )
        await self.client_conn.session_update(self.session_id, start)

        # Request permission
        outcome = await self.broker.request_for(f"edit_{path}")

        if not isinstance(outcome.outcome, AllowedOutcome):
            # User rejected
            failed = self.tracker.progress(
                f"edit_{path}",
                status="failed",
            )
            await self.client_conn.session_update(self.session_id, failed)
            return False

        # Perform write
        await self.client_conn.write_text_file(
            session_id=self.session_id,
            path=path,
            content=new_content,
        )

        # Report completion
        done = self.tracker.progress(
            f"edit_{path}",
            status="completed",
            raw_output={"success": True},
        )
        await self.client_conn.session_update(self.session_id, done)

        return True
```

This pattern ensures:

- Every IDE operation is reported as a tool call for UI visibility
- Permissions are requested before destructive operations
- Progress is tracked and streamed back to the IDE
- State is managed cleanly across concurrent operations
