# Pydantic AI Reference

This document provides a reference for Pydantic AI, focusing on areas critical for Punie's integration with ACP.

## Overview

**What is Pydantic AI?**

Pydantic AI is a Python framework for building production-grade AI applications with a "FastAPI feeling" — type-safe,
model-agnostic, and designed for ease of use.

**Key Characteristics:**

- Type-safe agent framework with full static type checking
- Model-agnostic (OpenAI, Anthropic, Gemini, Ollama, etc.)
- Built on Pydantic for data validation and structured outputs
- Async-first design
- Dependency injection for testable, composable agents
- Local checkout: `~/PycharmProjects/pydantic-ai/`

**Design Philosophy:**

- "FastAPI feeling" — intuitive, decorator-based API
- Type safety throughout — catch errors at development time
- Testability — dependencies can be overridden for testing
- Composability — agents can delegate to other agents

## Agent Class

The core abstraction in Pydantic AI is the `Agent` class, which is generic over dependencies and output type.

**Type Signature:**

```text
class Agent[DepsType, OutputType]:
    def __init__(
        self,
        model: Model | KnownModelName,
        *,
        deps_type: type[DepsType] = NoneType,
        output_type: type[OutputType] = str,
        system_prompt: str | Sequence[str] = "",
        ...
    ) -> None:
        ...
```

**Generic Parameters:**

- `DepsType` — Type of dependencies (e.g., database connections, API clients)
- `OutputType` — Type of agent's structured output (e.g., Pydantic model, str, int)

**Five Run Modes:**

1. **`run(prompt, *, deps=None)`** — Synchronous, single turn
2. **`run_sync(prompt, *, deps=None)`** — Alias for run
3. **`run_stream(prompt, *, deps=None)`** — Synchronous streaming
4. **`arun(prompt, *, deps=None)`** — Async, single turn
5. **`arun_stream(prompt, *, deps=None)`** — Async streaming

All modes return `RunResult[OutputType]` or `StreamedRunResult[OutputType]`.

**Example:**

```text
from pydantic_ai import Agent

agent = Agent(
    'openai:gpt-4',
    system_prompt='You are a helpful assistant.',
)

result = agent.run_sync('What is 2+2?')
print(result.data)  # "4"
```

## Tools and Toolsets

Tools are the primary way agents interact with external systems. Pydantic AI provides two mechanisms for defining tools.

### Decorator-Based Tools

**`@agent.tool`** — Define a tool directly on an agent:

```text
@agent.tool
async def get_user(ctx: RunContext[DatabaseConn], user_id: int) -> User:
    """Fetch user from database.

    Args:
        ctx: Run context with dependencies
        user_id: User ID to fetch
    """
    return await ctx.deps.fetch_user(user_id)
```

**Key points:**

- First parameter must be `RunContext[DepsType]`
- Docstring becomes tool description for LLM
- Type hints provide parameter schema
- Return type is validated

**`@agent.tool_plain`** — Tool without context parameter:

```text
@agent.tool_plain
def calculate_sum(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b
```

### AbstractToolset API

**The critical integration point for ACP.** Toolsets allow defining reusable tool collections that can be shared across
agents.

**Base Class:**

```text
from pydantic_ai import AbstractToolset, RunContext

class MyToolset(AbstractToolset):
    async def get_tools(
        self,
        ctx: RunContext[Any],
    ) -> list[ToolDefinition]:
        """Return tool definitions for this context.

        Called once per agent run to discover available tools.
        """
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
        ctx: RunContext[Any],
        **kwargs: Any,
    ) -> Any:
        """Tool implementation."""
        pass
```

**Usage:**

```text
agent = Agent(
    'openai:gpt-4',
    deps_type=MyDeps,
    toolsets=[MyToolset()],
)
```

**Why AbstractToolset is critical for Punie:**

Punie needs to bridge Pydantic AI's tool model to ACP's Client Protocol methods. AbstractToolset is where this bridge
happens:

1. **Dynamic tool registration** — `get_tools()` is called per-run, allowing context-aware tool availability
2. **Access to RunContext** — Tools receive full context including dependencies and conversation state
3. **Async support** — Tool implementations can be async (required for ACP RPC calls)
4. **Type flexibility** — Return type is `Any`, allowing arbitrary responses

## Dependencies

Pydantic AI uses type-safe dependency injection, similar to FastAPI.

**RunContext:**

```text
class RunContext[DepsType]:
    deps: DepsType           # User dependencies
    messages: list[Message]  # Conversation history
    usage: Usage             # Token usage tracking
    model: Model             # Current model instance
```

**Defining Dependencies:**

```text
from dataclasses import dataclass

@dataclass
class MyDeps:
    db: DatabaseConnection
    api_key: str

agent = Agent[MyDeps, str](
    'openai:gpt-4',
    deps_type=MyDeps,
)

result = agent.run_sync(
    'Query the database',
    deps=MyDeps(db=my_db, api_key='...'),
)
```

**Override for Testing:**

```text
@dataclass
class MockDeps:
    db: FakeDatabaseConnection
    api_key: str = "fake_key"

test_result = agent.run_sync(
    'Test query',
    deps=MockDeps(db=fake_db),
)
```

**Key Points:**

- Dependencies are immutable during a run
- Type checked at development time
- Can be overridden per-run for testing
- Passed to all tools via `RunContext`

## Structured Output

Pydantic AI validates agent output against Pydantic models, ensuring type-safe results.

**Define Output Schema:**

```text
from pydantic import BaseModel

class UserInfo(BaseModel):
    name: str
    age: int
    email: str

agent = Agent[NoneType, UserInfo](
    'openai:gpt-4',
    output_type=UserInfo,
)

result = agent.run_sync('Get user info for john@example.com')
user: UserInfo = result.data  # Type-checked!
```

**How it Works:**

1. Agent's `output_type` is converted to JSON Schema
2. Schema is sent to LLM via tool/function calling
3. LLM returns structured JSON
4. Pydantic validates and parses into Python object
5. Result is type-safe `UserInfo` instance

**Benefits:**

- No manual parsing of LLM responses
- Validation errors are caught immediately
- Type safety throughout the application
- Supports complex nested models

## Multi-Agent Patterns

Pydantic AI supports several patterns for composing multiple agents.

### Delegation

One agent calls another agent's tools:

```text
specialist_agent = Agent('openai:gpt-4', system_prompt='You are a math specialist.')

@specialist_agent.tool
def solve_equation(ctx: RunContext[Any], equation: str) -> str:
    # Specialized math solving
    pass

@main_agent.tool
def delegate_to_specialist(ctx: RunContext[Any], problem: str) -> str:
    result = specialist_agent.run_sync(problem, deps=ctx.deps)
    return result.data
```

### Hand-off

Agent explicitly transfers control to another agent:

```text
if need_specialist:
    return specialist_agent.run_sync(prompt, deps=current_deps)
```

### Graph-Based Orchestration

Use a state machine or graph to route between agents:

```text
class AgentGraph:
    def __init__(self):
        self.agents = {
            'general': general_agent,
            'specialist': specialist_agent,
            'validator': validator_agent,
        }

    async def run(self, prompt: str, deps: Any):
        current = 'general'
        result = None

        while current:
            agent = self.agents[current]
            result = await agent.arun(prompt, deps=deps)
            current = self._next_agent(result)

        return result

    def _next_agent(self, result: RunResult) -> str | None:
        # Decision logic for next agent
        pass
```

## Protocol Support

Pydantic AI has built-in support for external tool protocols:

**Model Context Protocol (MCP):**

- Native support for MCP servers
- Can consume tools from MCP-compliant services
- Example: `agent = Agent('openai:gpt-4', mcp_servers=[...])`

**Agent-to-Agent (A2A):**

- Protocol for agents to communicate with each other
- Supports delegation and hand-off patterns

**ACP (Agent Communication Protocol):**

- **Not natively supported** (as of January 2025)
- Issue #1742 was opened requesting ACP support
- Request was declined because ACP is not yet a standard protocol
- Punie must implement ACP bridge via AbstractToolset

## Relevance to Punie

**Punie uses Pydantic AI as its internal agent engine** but communicates externally via ACP (not Pydantic AI's native
protocols).

**Integration Strategy:**

1. **AbstractToolset is the Bridge**
    - Create `ACPToolset(AbstractToolset)` that wraps ACP Client Protocol methods
    - Each ACP Client method (read_text_file, write_text_file, create_terminal) becomes a Pydantic AI tool
    - Tool implementations call the ACP Client and return results to Pydantic AI

2. **Dependencies Hold ACP Connection**
    - Define `ACPDeps` with `client_conn: Client` and `session_id: str`
    - Pass ACP client connection as dependency to Pydantic AI agent
    - Tools access ACP client via `ctx.deps.client_conn`

3. **Structured Output for Tool Results**
    - Use Pydantic models for tool return types
    - Ensures type-safe data flow from ACP to Pydantic AI to LLM

4. **Multi-Agent for Complex Workflows**
    - Use Pydantic AI's delegation patterns for complex tasks
    - Each sub-agent can have specialized toolsets

**Conceptual Example:**

```text
from pydantic_ai import Agent, AbstractToolset, RunContext
from dataclasses import dataclass

@dataclass
class ACPDeps:
    client_conn: Client  # ACP client connection
    session_id: str
    tracker: ToolCallTracker  # For reporting tool calls

class ACPToolset(AbstractToolset):
    async def get_tools(
        self,
        ctx: RunContext[ACPDeps],
    ) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="read_file",
                description="Read contents of a file",
                parameters_json_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"}
                    },
                    "required": ["path"],
                },
                function=self.read_file,
            ),
            ToolDefinition(
                name="write_file",
                description="Write contents to a file",
                parameters_json_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["path", "content"],
                },
                function=self.write_file,
            ),
        ]

    async def read_file(
        self,
        ctx: RunContext[ACPDeps],
        path: str,
    ) -> str:
        # Report tool call to PyCharm via ACP
        start = ctx.deps.tracker.start(
            f"read_{path}",
            title=f"Reading {path}",
            kind="read",
            locations=[ToolCallLocation(path=path)],
        )
        await ctx.deps.client_conn.session_update(
            ctx.deps.session_id,
            start,
        )

        # Perform ACP file read
        response = await ctx.deps.client_conn.read_text_file(
            session_id=ctx.deps.session_id,
            path=path,
        )

        # Report completion
        done = ctx.deps.tracker.progress(
            f"read_{path}",
            status="completed",
        )
        await ctx.deps.client_conn.session_update(
            ctx.deps.session_id,
            done,
        )

        return response.content

    async def write_file(
        self,
        ctx: RunContext[ACPDeps],
        path: str,
        content: str,
    ) -> bool:
        # Report and request permission
        start = ctx.deps.tracker.start(
            f"write_{path}",
            title=f"Writing {path}",
            kind="edit",
            locations=[ToolCallLocation(path=path)],
        )
        await ctx.deps.client_conn.session_update(
            ctx.deps.session_id,
            start,
        )

        outcome = await ctx.deps.client_conn.request_permission(
            session_id=ctx.deps.session_id,
            tool_call=ctx.deps.tracker.tool_call_model(f"write_{path}"),
            options=default_permission_options(),
        )

        if not isinstance(outcome.outcome, AllowedOutcome):
            return False

        # Perform write
        await ctx.deps.client_conn.write_text_file(
            session_id=ctx.deps.session_id,
            path=path,
            content=content,
        )

        # Report completion
        done = ctx.deps.tracker.progress(
            f"write_{path}",
            status="completed",
        )
        await ctx.deps.client_conn.session_update(
            ctx.deps.session_id,
            done,
        )

        return True

# Create agent with ACP toolset
punie_agent = Agent[ACPDeps, str](
    'anthropic:claude-3-5-sonnet-20241022',
    deps_type=ACPDeps,
    system_prompt='You are Punie, an AI coding assistant.',
    toolsets=[ACPToolset()],
)

# Run with ACP dependencies
result = await punie_agent.arun(
    'Read the config.json file and modify the debug setting',
    deps=ACPDeps(
        client_conn=acp_client,
        session_id='sess_123',
        tracker=ToolCallTracker(),
    ),
)
```

**Key Integration Points:**

1. **Pydantic AI → ACP (Tool Execution)**
    - Pydantic AI calls tool in ACPToolset
    - Tool makes ACP Client RPC call (read_text_file, write_text_file, etc.)
    - Result flows back to Pydantic AI

2. **ACP → Pydantic AI (Tool Reporting)**
    - Before/after ACP Client calls, send ToolCallStart/ToolCallProgress via session_update()
    - PyCharm sees tool activity in IDE UI

3. **Permission Flow**
    - Pydantic AI tool implementation calls request_permission()
    - Blocks until user approves/rejects in PyCharm
    - Tool returns based on permission outcome

4. **Shared Foundation**
    - Both use Pydantic for data validation
    - Both are async-first
    - Compatible dependency injection patterns
