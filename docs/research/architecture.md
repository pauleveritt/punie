# Punie Architecture Overview

This document explains how Punie bridges Pydantic AI (internal agent engine), ACP (external protocol for IDE
communication), and HTTP API (web-based access).

## Vision

**Punie is the bridge between three worlds:**

1. **Pydantic AI** — Type-safe, model-agnostic agent framework for building AI applications
2. **ACP** — Stdio-based JSON-RPC protocol for IDEs to orchestrate AI agents
3. **HTTP API** — Web-based access to the agent with a custom web UI

**Why all three?**

- **Pydantic AI** provides the internal agent architecture: tools, dependencies, structured output, multi-agent patterns
- **ACP** provides the IDE communication protocol: PyCharm (or other IDEs) can control and monitor Punie via stdio
- **HTTP API** provides web-based access: Custom web UI or API clients can interact with Punie over HTTP
- **Punie** translates between them: Pydantic AI tools become ACP operations or HTTP endpoints, with appropriate protocol adapters for each interface

## Component Roles

### Pydantic AI (Internal Engine)

**Role:** Agent framework and runtime

**Responsibilities:**

- Manage conversation with LLM (Anthropic Claude)
- Dispatch tool calls based on LLM decisions
- Validate structured outputs (Pydantic models)
- Handle dependencies (database, APIs, ACP client)
- Support multi-agent delegation

**What it knows about:**

- Tools (functions the agent can call)
- Dependencies (resources passed to tools)
- Conversation history
- LLM prompts and responses

**What it doesn't know about:**

- PyCharm or IDEs
- ACP protocol
- Tool call reporting/permissions

### ACP (External Protocol)

**Role:** Communication protocol with IDE

**Responsibilities:**

- Stdio-based JSON-RPC 2.0 transport
- Agent Protocol (Punie implements)
- Client Protocol (PyCharm implements)
- Tool call notifications (ToolCallStart, ToolCallProgress)
- Permission requests (request_permission RPC)
- File operations (read_text_file, write_text_file)
- Terminal operations (create_terminal, etc.)

**What it knows about:**

- Session management
- Tool call lifecycle (pending, in_progress, completed, failed)
- Permission options (allow_once, allow_always, reject_once, reject_always)
- File and terminal operations

**What it doesn't know about:**

- LLMs or agent frameworks
- How tools are implemented internally
- Pydantic validation

### Punie (The Bridge)

**Role:** Translate between Pydantic AI and ACP

**Responsibilities:**

- Implement ACP Agent Protocol (respond to PyCharm requests)
- Expose ACP Client operations as Pydantic AI tools (via AbstractToolset)
- Report tool execution to PyCharm (ToolCallStart/Progress)
- Request permissions before destructive operations
- Stream progress updates to IDE

**Bridge mechanisms:**

1. **ACPToolset (AbstractToolset)** — Makes ACP Client methods available as Pydantic AI tools
2. **ToolCallTracker** — Manages tool call reporting state
3. **ACPDeps** — Passes ACP client connection and tracker as dependencies

## Data Flow

Here's how a typical operation flows through the system:

```
┌──────────┐          ┌───────────┐          ┌──────────────┐          ┌─────┐
│ PyCharm  │          │   Punie   │          │  Pydantic AI │          │ LLM │
│ (Client) │          │ (Bridge)  │          │   (Engine)   │          │     │
└────┬─────┘          └─────┬─────┘          └──────┬───────┘          └──┬──┘
     │                      │                       │                      │
     │  1. prompt() RPC     │                       │                      │
     │─────────────────────>│                       │                      │
     │                      │                       │                      │
     │                      │  2. agent.arun()      │                      │
     │                      │──────────────────────>│                      │
     │                      │                       │                      │
     │                      │                       │  3. LLM request      │
     │                      │                       │─────────────────────>│
     │                      │                       │                      │
     │                      │                       │  4. Tool call request│
     │                      │                       │<─────────────────────│
     │                      │                       │                      │
     │                      │  5. Call ACPToolset   │                      │
     │                      │<──────────────────────│                      │
     │                      │                       │                      │
     │  6. ToolCallStart    │                       │                      │
     │<─────────────────────│                       │                      │
     │                      │                       │                      │
     │  7. request_permission│                      │                      │
     │<─────────────────────│                       │                      │
     │                      │                       │                      │
     │  8. User approval    │                       │                      │
     │─────────────────────>│                       │                      │
     │                      │                       │                      │
     │  9. read_text_file   │                       │                      │
     │<─────────────────────│                       │                      │
     │                      │                       │                      │
     │ 10. File contents    │                       │                      │
     │─────────────────────>│                       │                      │
     │                      │                       │                      │
     │ 11. ToolCallProgress │                       │                      │
     │<─────────────────────│                       │                      │
     │                      │                       │                      │
     │                      │ 12. Return result     │                      │
     │                      │──────────────────────>│                      │
     │                      │                       │                      │
     │                      │                       │ 13. Send to LLM      │
     │                      │                       │─────────────────────>│
     │                      │                       │                      │
     │                      │                       │ 14. Final response   │
     │                      │                       │<─────────────────────│
     │                      │                       │                      │
     │                      │ 15. RunResult         │                      │
     │                      │<──────────────────────│                      │
     │                      │                       │                      │
     │ 16. PromptResponse   │                       │                      │
     │<─────────────────────│                       │                      │
     │                      │                       │                      │
```

**Step-by-Step:**

1. **PyCharm sends prompt** — User types a request in IDE, PyCharm calls `prompt()` RPC
2. **Punie starts Pydantic AI run** — Calls `agent.arun(prompt, deps=ACPDeps(...))`
3. **Pydantic AI queries LLM** — Sends conversation + available tools to Claude
4. **LLM requests tool** — Claude decides to use `read_file` tool
5. **Pydantic AI calls ACPToolset** — Dispatches to `ACPToolset.read_file()`
6. **Punie reports intent** — Sends `ToolCallStart` notification to PyCharm via `session_update()`
7. **Punie requests permission** — (Optional, for write operations) Calls `request_permission()` RPC, blocks until user
   responds
8. **User approves** — PyCharm shows permission dialog, user clicks "Allow"
9. **Punie calls ACP Client** — Calls `client_conn.read_text_file()` RPC
10. **PyCharm returns contents** — Reads file from disk, returns via RPC response
11. **Punie reports completion** — Sends `ToolCallProgress(status="completed")` notification
12. **Punie returns to Pydantic AI** — Tool function returns file contents string
13. **Pydantic AI sends to LLM** — Includes tool result in next LLM request
14. **LLM generates response** — Claude formulates final answer
15. **Pydantic AI returns** — `RunResult` with final response
16. **Punie responds to PyCharm** — `PromptResponse` completes the RPC request

## The Tool Bridge

**This is the critical integration pattern.** The Tool Bridge connects Pydantic AI's tool model to ACP's Client
Protocol.

### Pydantic AI Side: AbstractToolset

**What:** Custom `ACPToolset(AbstractToolset)` exposes IDE operations as Pydantic AI tools

**How:**

```text
class ACPToolset(AbstractToolset):
    async def get_tools(self, ctx: RunContext[ACPDeps]) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="read_file",
                description="Read contents of a file",
                parameters_json_schema={"type": "object", "properties": {...}},
                function=self.read_file,
            ),
            ToolDefinition(
                name="write_file",
                description="Write contents to a file",
                parameters_json_schema={"type": "object", "properties": {...}},
                function=self.write_file,
            ),
            ToolDefinition(
                name="run_command",
                description="Execute a shell command",
                parameters_json_schema={"type": "object", "properties": {...}},
                function=self.run_command,
            ),
        ]
```

**Key points:**

- `get_tools()` is called once per agent run
- Returns list of tool definitions with JSON schemas
- Each tool maps to an ACP Client Protocol method
- LLM sees these as available actions

### ACP Side: Client Protocol Translation

**What:** When Pydantic AI calls a tool, the toolset translates to ACP Client RPC calls

**How:**

```text
class ACPToolset(AbstractToolset):
    async def read_file(self, ctx: RunContext[ACPDeps], path: str) -> str:
        # 1. Report tool call intent (ACP notification)
        start = ctx.deps.tracker.start(
            f"read_{path}",
            title=f"Reading {path}",
            kind="read",
            locations=[ToolCallLocation(path=path)],
        )
        await ctx.deps.client_conn.session_update(ctx.deps.session_id, start)

        # 2. Perform ACP Client RPC call
        response = await ctx.deps.client_conn.read_text_file(
            session_id=ctx.deps.session_id,
            path=path,
        )

        # 3. Report completion (ACP notification)
        done = ctx.deps.tracker.progress(
            f"read_{path}",
            status="completed",
            raw_output={"bytes": len(response.content)},
        )
        await ctx.deps.client_conn.session_update(ctx.deps.session_id, done)

        # 4. Return result to Pydantic AI
        return response.content
```

**Translation layers:**

1. **Tool definition** — Pydantic AI tool → ACP Client method
2. **Tool reporting** — Before/after execution → ToolCallStart/ToolCallProgress notifications
3. **Permission flow** — For writes → `request_permission()` RPC (blocks until user response)
4. **Result flow** — ACP response → Pydantic AI return value → LLM context

### Tool Call Reporting

**What:** Punie uses ToolCallStart/ToolCallProgress to stream tool status back to PyCharm

**Why:** PyCharm needs visibility into what Punie is doing, even when tool execution is internal to Pydantic AI

**Pattern:**

```text
# Phase 1: Announce (ToolCallStart)
await client_conn.session_update(session_id, ToolCallStart(...))

# Phase 2: Request permission (for destructive ops)
outcome = await client_conn.request_permission(...)

# Phase 3: Execute ACP Client call
result = await client_conn.read_text_file(...)

# Phase 4: Report completion (ToolCallProgress)
await client_conn.session_update(session_id, ToolCallProgress(status="completed"))
```

**Visibility benefits:**

- PyCharm shows progress indicators
- User sees which files are being read/written
- Permission dialogs show context (file path, operation type)
- IDE can log all operations for debugging

### Permission Flow

**What:** Pydantic AI's human-in-the-loop maps to ACP's `request_permission()`

**When:** Before destructive operations (write, delete, execute)

**Pattern:**

```text
async def write_file(self, ctx: RunContext[ACPDeps], path: str, content: str) -> bool:
    # 1. Announce intent
    start = ctx.deps.tracker.start(f"write_{path}", title=f"Writing {path}", kind="edit")
    await ctx.deps.client_conn.session_update(ctx.deps.session_id, start)

    # 2. Request permission (BLOCKS until user responds)
    outcome = await ctx.deps.client_conn.request_permission(
        session_id=ctx.deps.session_id,
        tool_call=ctx.deps.tracker.tool_call_model(f"write_{path}"),
        options=default_permission_options(),
    )

    # 3. Check outcome
    if not isinstance(outcome.outcome, AllowedOutcome):
        # User rejected, report failure
        failed = ctx.deps.tracker.progress(f"write_{path}", status="failed")
        await ctx.deps.client_conn.session_update(ctx.deps.session_id, failed)
        return False

    # 4. Perform write
    await ctx.deps.client_conn.write_text_file(
        session_id=ctx.deps.session_id,
        path=path,
        content=content,
    )

    # 5. Report completion
    done = ctx.deps.tracker.progress(f"write_{path}", status="completed")
    await ctx.deps.client_conn.session_update(ctx.deps.session_id, done)
    return True
```

**Permission options:**

- `allow_once` — Approve this specific operation
- `allow_always` — Approve all similar operations in this session
- `reject_once` — Reject this operation
- `reject_always` — Reject all similar operations in this session

### Tool Mapping Table

| **Pydantic AI Tool** | **ACP Client Method**      | **IDE Action**              |
|----------------------|----------------------------|-----------------------------|
| `read_file`          | `read_text_file()`         | Read file from disk         |
| `write_file`         | `write_text_file()`        | Write file to disk          |
| `list_files`         | (Custom implementation)    | List directory contents     |
| `search_files`       | (Custom implementation)    | Search files by pattern     |
| `run_command`        | `create_terminal()`        | Execute shell command       |
| `get_command_output` | `terminal_output()`        | Read terminal output        |
| `wait_for_command`   | `wait_for_terminal_exit()` | Wait for process completion |
| `kill_command`       | `kill_terminal()`          | Terminate running process   |

**Notes:**

- Some Pydantic AI tools map 1:1 to ACP methods
- Others combine multiple ACP calls (e.g., `list_files` might use multiple file reads)
- All tools report progress via ToolCallStart/ToolCallProgress

## Shared Foundation

Pydantic AI and ACP share compatible foundations that make integration natural:

### Both Use Pydantic

- **ACP SDK:** Auto-generated Pydantic models from schema.json (`acp.schema`)
- **Pydantic AI:** Built entirely on Pydantic for validation and structured output
- **Benefit:** Type-safe data flow throughout the stack

### Both Are Async-First

- **ACP:** All protocol methods are `async def`
- **Pydantic AI:** Async tools, async agent runs
- **Benefit:** No impedance mismatch, natural async/await patterns

### Compatible Dependency Injection

- **Pydantic AI:** `RunContext[DepsType]` with type-safe dependencies
- **ACP:** Client connection and session state naturally fit as dependencies
- **Pattern:**

```text
@dataclass
class ACPDeps:
    client_conn: Client        # ACP client connection
    session_id: str            # Current session ID
    tracker: ToolCallTracker   # Tool call state manager

agent = Agent[ACPDeps, str](
    'anthropic:claude-3-5-sonnet-20241022',
    deps_type=ACPDeps,
    toolsets=[ACPToolset()],
)

result = await agent.arun(
    prompt='Read and modify config.json',
    deps=ACPDeps(
        client_conn=acp_client,
        session_id='sess_123',
        tracker=ToolCallTracker(),
    ),
)
```

## Roadmap Phase Mapping

How this architecture unfolds across Punie's roadmap:

### Phase 1: Baseline (Complete)

- Basic project structure
- Testing infrastructure
- Proof of concept

### Phase 2: Agent OS (Current — 1.3 Documentation)

- **This document** captures the architecture for future phases
- Agent OS infrastructure (standards, skills, commands)
- Documentation with deep research

### Phase 3: Pydantic AI Migration

**Focus:** Build the Pydantic AI internal engine

**Tasks:**

- Create Pydantic AI agent with system prompts
- Define `ACPDeps` dataclass
- Implement basic tools using `@agent.tool` decorator
- Test agent runs with mock dependencies
- Structured output with Pydantic models

**Architecture deliverable:** Working Pydantic AI agent (standalone, no ACP yet)

### Phase 4: ACP Integration

**Focus:** Build the Tool Bridge

**Tasks:**

- Create `ACPToolset(AbstractToolset)` class
- Implement ACP Agent Protocol (`acp.interfaces.Agent`)
- Translate ACP Client methods to Pydantic AI tools
- Implement ToolCallStart/ToolCallProgress reporting
- Add permission flow for destructive operations
- Use ToolCallTracker for state management
- Connect to PyCharm via stdio/JSON-RPC

**Architecture deliverable:** Full Punie agent that PyCharm can control

### Phase 5: IDE Features (Future)

- Code navigation
- Refactoring operations
- Test generation
- Error diagnosis
- Documentation generation

**Architecture impact:** Additional tools in ACPToolset, more complex permission flows

### Phase 6: Multi-Agent (Future)

- Specialist agents for different tasks (testing, refactoring, debugging)
- Agent delegation and hand-off patterns
- Graph-based orchestration

**Architecture impact:** Multiple Pydantic AI agents, routing logic in Punie bridge

## Critical Design Decisions

### Decision 1: Pydantic AI Internal, ACP External

**Rationale:**

- Pydantic AI provides excellent agent framework (tools, structured output, testing)
- ACP provides standard IDE protocol (PyCharm compatibility)
- Punie bridges them, getting benefits of both

**Alternative considered:**

- Direct ACP implementation without Pydantic AI — Would lose type safety, tool abstraction, testing benefits

### Decision 2: AbstractToolset as Bridge Point

**Rationale:**

- AbstractToolset is Pydantic AI's extension point for custom tool sources
- Allows dynamic tool registration (per-run)
- Provides RunContext with dependencies and conversation state
- Async support for ACP RPC calls

**Alternative considered:**

- `@agent.tool` decorators — Would hardcode ACP client, lose flexibility, make testing harder

### Decision 3: ToolCallTracker for State Management

**Rationale:**

- ACP tool calls are stateful (start → progress → completion)
- Multiple concurrent tool calls need independent tracking
- ToolCallTracker provides clean API for managing this state

**Alternative considered:**

- Manual state management — Error-prone, boilerplate-heavy, hard to maintain

### Decision 4: Dependencies for ACP Client

**Rationale:**

- Pydantic AI's dependency injection makes ACP client accessible to all tools
- Easy to override for testing (pass mock client)
- Type-safe access via `ctx.deps.client_conn`

**Alternative considered:**

- Global client connection — Breaks testability, creates coupling

## Success Criteria

This architecture succeeds if:

1. **Pydantic AI tools are clean** — No ACP-specific code leaking into tool logic
2. **ACP compliance** — PyCharm can control Punie via standard protocol
3. **Type safety** — No `Any` types in critical paths, full static type checking
4. **Testability** — Can test Pydantic AI agent with mock ACP dependencies
5. **Progress visibility** — PyCharm always knows what Punie is doing (via tool call notifications)
6. **Permission control** — User approves destructive operations before execution
7. **Performance** — No unnecessary round-trips, efficient streaming
8. **Extensibility** — Easy to add new tools, new agents, new IDE features
