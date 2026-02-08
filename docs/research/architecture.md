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

## Session State Management (Phase 4.2)

**What:** Session-scoped caching of discovered tools and agent instances

**Why:** Eliminates redundant tool discovery and agent construction on every prompt

### SessionState Design

```python
@dataclass(frozen=True)
class SessionState:
    """Immutable session-scoped cached state."""
    catalog: ToolCatalog | None        # Discovered tools (None if fallback)
    agent: PydanticAgent[ACPDeps, str] # Configured agent instance
    discovery_tier: int                # 1=catalog, 2=capabilities, 3=default
```

**Key principles:**

- **Frozen dataclass:** Immutable for entire session lifetime
- **Agent encapsulation:** Toolset is encapsulated in the agent (not exposed separately)
- **Discovery tier:** For observability and logging

### Registration Flow

**Before Phase 4.2 (inefficient):**

```text
PyCharm                Punie (PunieAgent)              Pydantic AI
   │                          │                            │
   │  new_session()           │                            │
   │─────────────────────────>│                            │
   │  SessionID               │                            │
   │<─────────────────────────│                            │
   │                          │                            │
   │  prompt("task 1")        │                            │
   │─────────────────────────>│                            │
   │                          │  discover_tools()          │
   │                          │  create_toolset()          │
   │                          │  create_pydantic_agent()   │
   │                          │────────────────────────────>│
   │                          │                            │
   │  prompt("task 2")        │                            │
   │─────────────────────────>│                            │
   │                          │  discover_tools() [AGAIN]  │
   │                          │  create_toolset() [AGAIN]  │
   │                          │  create_pydantic_agent() [AGAIN]
   │                          │────────────────────────────>│
```

**After Phase 4.2 (efficient):**

```text
PyCharm                Punie (PunieAgent)              Pydantic AI
   │                          │                            │
   │  new_session()           │                            │
   │─────────────────────────>│                            │
   │                          │  discover_tools() [ONCE]   │
   │                          │  create_toolset()          │
   │                          │  create_pydantic_agent()   │
   │                          │  cache in _sessions dict   │
   │  SessionID               │                            │
   │<─────────────────────────│                            │
   │                          │                            │
   │  prompt("task 1")        │                            │
   │─────────────────────────>│                            │
   │                          │  get cached agent          │
   │                          │────────────────────────────>│
   │                          │                            │
   │  prompt("task 2")        │                            │
   │─────────────────────────>│                            │
   │                          │  get cached agent [NO RPC] │
   │                          │────────────────────────────>│
```

### Performance Impact

- **RPC calls reduced:** 1 `discover_tools()` call per session (not per prompt)
- **Agent construction:** Once per session (not per prompt)
- **Memory overhead:** One `SessionState` object per active session (~1KB)

### Backward Compatibility

**Lazy fallback:** Tests or clients calling `prompt()` without `new_session()` trigger on-demand discovery and cache the result. No breaking changes.

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

## Local Model Architecture (Phase 6.1)

### Overview

Punie supports fully local, offline AI development using MLX models on Apple Silicon. This enables zero-cost, privacy-preserving development without any API calls.

### MLX Model Integration

**What:** Custom Pydantic AI `Model` implementation using Apple's MLX framework for on-device inference.

**Why local models?**

- **Zero API costs** — No charges per token
- **Privacy** — Sensitive codebases never leave your machine
- **Offline development** — No internet required after initial model download
- **Fast responses** — No API latency (local inference ~50-200 tokens/sec)
- **Full tool calling** — Complete IDE integration works identically to cloud models

### Architecture Design

```text
┌─────────────────────────────────────────────────────────────┐
│                      Punie Agent                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Pydantic AI Agent                       │  │
│  │  ┌────────────────────────────────────────────────┐ │  │
│  │  │            Model (Abstract)                    │ │  │
│  │  │  ┌──────────────┐    ┌──────────────────────┐ │ │  │
│  │  │  │ Cloud Models │    │   MLXModel (Local)   │ │ │  │
│  │  │  │ - OpenAI     │    │  - Dependency inject │ │ │  │
│  │  │  │ - Anthropic  │    │  - Tool calling      │ │ │  │
│  │  │  │ - Gemini     │    │  - Chat templates    │ │ │  │
│  │  │  └──────────────┘    └──────────────────────┘ │ │  │
│  │  └────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              ACPToolset (Tools)                      │  │
│  │  - read_file()                                       │  │
│  │  - write_file()                                      │  │
│  │  - run_command()                                     │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
         │                                    │
         │ Cloud API                          │ Local inference
         ↓                                    ↓
┌──────────────────┐              ┌──────────────────────┐
│  OpenAI/Claude   │              │   MLX Framework      │
│  (API calls)     │              │   (Apple Silicon)    │
└──────────────────┘              └──────────────────────┘
```

### MLXModel Implementation

**Core class:** `src/punie/models/mlx.py::MLXModel`

**Key design principles:**

1. **Dependency injection for testability**
   ```python
   # Constructor accepts pre-loaded components (for testing)
   model = MLXModel(
       "model-name",
       model_data=mock_data,
       tokenizer=mock_tokenizer
   )

   # Factory method loads from disk (for production)
   model = MLXModel.from_pretrained("mlx-community/Qwen2.5-Coder-7B-Instruct-4bit")
   ```

2. **Cross-platform compatibility**
   - TYPE_CHECKING guards for mlx-lm imports
   - Module importable on any platform (Linux, Windows, macOS)
   - Runtime ImportError with helpful message on non-Apple Silicon

3. **Tool calling without native API**
   - MLX models lack native function-calling API
   - Uses chat templates + regex parsing
   - Model outputs: `<tool_call>{"name": "...", "arguments": {...}}</tool_call>`
   - Parsed into `ToolCallPart` for Pydantic AI

### Tool Calling Flow (Local)

```text
User Request
    │
    ↓
┌─────────────────────────────────────────────────────────┐
│ Pydantic AI Agent                                       │
│                                                         │
│  1. Build messages + tool definitions                   │
│     ┌──────────────────────────────────────┐          │
│     │ messages = [                          │          │
│     │   {"role": "system", "content": ...}, │          │
│     │   {"role": "user", "content": ...}    │          │
│     │ ]                                     │          │
│     │ tools = [                             │          │
│     │   {"type": "function", "function": {  │          │
│     │     "name": "read_file",              │          │
│     │     "description": "...",             │          │
│     │     "parameters": {...}               │          │
│     │   }}                                  │          │
│     │ ]                                     │          │
│     └──────────────────────────────────────┘          │
│                                                         │
│  2. MLXModel.request()                                  │
│     ├─> Apply chat template with tools                 │
│     │   (tokenizer.apply_chat_template)                │
│     ├─> Generate tokens (mlx_lm.generate)              │
│     └─> Parse tool calls from output                   │
│         (regex: <tool_call>...</tool_call>)            │
│                                                         │
│  3. Return ModelResponse                                │
│     ┌──────────────────────────────────────┐          │
│     │ parts = [                             │          │
│     │   TextPart("Let me read that file"),  │          │
│     │   ToolCallPart(                       │          │
│     │     tool_name="read_file",            │          │
│     │     args={"path": "config.py"}        │          │
│     │   )                                   │          │
│     │ ]                                     │          │
│     └──────────────────────────────────────┘          │
│                                                         │
│  4. Execute tool via ACPToolset                         │
│     └─> ACPToolset.read_file()                         │
│         └─> Client.read_text_file() [ACP RPC]          │
│                                                         │
│  5. Add result to messages, loop until done             │
└─────────────────────────────────────────────────────────┘
```

### Message Format Mapping

**MLXModel translates between Pydantic AI and OpenAI-compatible format:**

```python
# Pydantic AI → OpenAI chat format
ModelRequest([
    SystemPromptPart(content="You are an assistant"),
    UserPromptPart(content="Read config.py"),
])
→
[
    {"role": "system", "content": "You are an assistant"},
    {"role": "user", "content": "Read config.py"}
]

# ModelResponse → OpenAI format (for next turn)
ModelResponse([
    TextPart("Here's the file"),
    ToolCallPart(tool_name="read", args={...})
])
→
{
    "role": "assistant",
    "content": "Here's the file",
    "tool_calls": [{
        "id": "call_123",
        "type": "function",
        "function": {"name": "read", "arguments": "{...}"}
    }]
}

# ToolReturnPart → OpenAI format
ToolReturnPart(content="file contents", tool_call_id="call_123")
→
{
    "role": "tool",
    "content": "file contents",
    "tool_call_id": "call_123"
}
```

### Model Selection

**Factory integration:** `create_pydantic_agent(model='local')`

```python
# Default local model (Qwen 7B 4-bit)
agent = create_pydantic_agent(model='local')

# Custom model
agent = create_pydantic_agent(
    model='local:mlx-community/Qwen2.5-Coder-3B-Instruct-4bit'
)

# Environment variable
PUNIE_MODEL=local punie serve
```

**Model recommendations:**

| Model | Size | Memory | Use Case |
|-------|------|--------|----------|
| Qwen2.5-Coder-3B-Instruct-4bit | ~2GB | 6GB+ | Fast, simple tasks |
| Qwen2.5-Coder-7B-Instruct-4bit (default) | ~4GB | 8GB+ | Balanced quality/speed |
| Qwen2.5-Coder-14B-Instruct-4bit | ~8GB | 16GB+ | Best quality |

### Performance Characteristics

**Local vs Cloud comparison:**

| Aspect | Cloud (OpenAI/Claude) | Local (MLX 7B) |
|--------|-----------------------|----------------|
| Cost | ~$0.01-0.10 per request | $0 (one-time hardware) |
| Latency | 200-2000ms | 50-500ms |
| Throughput | High (datacenter) | 50-200 tokens/sec |
| Privacy | Data sent to API | Never leaves device |
| Offline | Requires internet | Works offline |
| Model quality | Excellent (GPT-4, Claude) | Good (Qwen 7B) |

**When to use local models:**

- **Development/testing** — Fast iteration without API costs
- **Privacy-sensitive codebases** — No data leaves your machine
- **Offline environments** — No internet connectivity
- **High-volume experimentation** — Unlimited local inference

**When to use cloud models:**

- **Production deployments** — Best quality for critical tasks
- **Complex reasoning** — GPT-4/Claude superior for difficult problems
- **Limited local resources** — <8GB RAM or older hardware

### Testing Strategy

**All tests work without mlx-lm installed:**

```python
# Dependency injection eliminates need for monkeypatching
def test_mlx_request():
    # Create model with mock components (no mlx-lm needed!)
    model = MLXModel("test", model_data=MagicMock(), tokenizer=MagicMock())

    # Override generation for testing
    model._generate = lambda *args: "mocked response"

    # Test model behavior
    response = await model.request(messages=[...], ...)
    assert response.parts[0].content == "mocked response"
```

**22 tests covering:**
- Pure function tests (tool call parsing)
- Message format mapping
- Model properties and tool building
- Request integration
- Factory integration

### Security Considerations

**Local model benefits:**
- No API keys to manage or leak
- No data transmitted over network
- No third-party data retention

**Local model risks:**
- Model files on disk (~4GB unencrypted)
- Generated code executed locally (same as cloud)
- User must verify model source (use official mlx-community models)

### Future Enhancements

**Phase 6.2+ possibilities:**
- Model quantization tuning (2-bit, 3-bit)
- Fine-tuning on project-specific code
- Multi-model ensembles (local + cloud fallback)
- Speculative decoding for faster generation
- Custom tool-calling formats (beyond Qwen templates)

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
9. **Local model parity** — Local MLX models work identically to cloud models for tool calling
