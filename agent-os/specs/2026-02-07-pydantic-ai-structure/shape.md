# Shape: Pydantic AI Structure (Phase 3.2)

## Scope Decision

**What's In:**
- Pydantic AI as internal agent engine (replaces hand-rolled MinimalAgent)
- Adapter pattern: PunieAgent satisfies ACP Agent protocol, delegates to Pydantic AI
- Single tool: `read_file` (wrapping `Client.read_text_file`)
- TestModel only (no real LLM configuration)
- Full test coverage with FakeClient

**What's Out:**
- `write_file` tool (requires permission flow — deferred to Phase 3.3)
- Terminal tools (deferred to Phase 3.3)
- Real LLM model configuration (deferred to Phase 3.4)
- Pydantic AI serving protocols (to_a2a, to_ag_ui) — HTTP app stays unchanged
- Changes to vendored ACP SDK

## Adapter Pattern Rationale

**Why PunieAgent as Adapter?**

Punie operates in two protocol universes:

1. **External Protocol:** ACP (Agent Communication Protocol) — PyCharm speaks this
2. **Internal Protocol:** Pydantic AI Agent API — LLM interaction happens here

The adapter pattern bridges these universes:

```
PyCharm (ACP Client)
    ↓ stdio/JSON-RPC
PunieAgent (ACP Agent Protocol)
    ↓ calls pydantic_agent.arun()
Pydantic AI Agent
    ↓ may call tools
ACPToolset
    ↓ calls ACP Client methods
PyCharm (ACP Client) — tool execution
```

**Why not implement Agent protocol in Pydantic AI directly?**

1. **Separation of concerns** — Pydantic AI is model-agnostic, ACP is IDE-specific
2. **Pydantic AI upstream** — ACP support was explicitly declined (not a standard protocol yet)
3. **Testability** — Adapter can be tested with FakeClient without Pydantic AI involvement
4. **Future flexibility** — Can swap Pydantic AI for another engine without changing ACP surface

**Why AbstractToolset?**

AbstractToolset is the official extension point in Pydantic AI for external tool providers:

1. **get_tools()** called per-run — dynamic tool availability
2. **RunContext[ACPDeps]** — tools access ACP client connection
3. **Async-first** — tool implementations can await ACP RPC calls
4. **Lifecycle control** — report tool calls via ToolCallTracker before/after execution

Alternative (FunctionToolset with decorators) is simpler but less flexible for complex tool lifecycle management.

## Data Flow

**Prompt Request:**

1. PyCharm sends `prompt` request over ACP stdio
2. `PunieAgent.prompt()` receives ACP `PromptRequest`
3. Extract text from ACP content blocks
4. Construct `ACPDeps(client_conn, session_id, tracker)`
5. Call `pydantic_agent.arun(prompt_text, deps=acp_deps)`
6. Pydantic AI runs LLM

**Tool Call (if LLM decides to use `read_file`):**

7. Pydantic AI calls `ACPToolset.read_file(ctx, path="/foo/bar.py")`
8. `ACPToolset.read_file()`:
   - `tracker.start("read_file", title="Reading /foo/bar.py")`
   - `client_conn.session_update(session_id, ToolCallStart(...))`
   - `response = await client_conn.read_text_file(session_id, path="/foo/bar.py")`
   - `tracker.progress("read_file", status="completed")`
   - `client_conn.session_update(session_id, ToolCallProgress(...))`
   - Return `response.content` to Pydantic AI
9. Pydantic AI continues with tool result

**Response:**

10. Pydantic AI completes, returns `RunResult[str]`
11. `PunieAgent.prompt()` sends `AgentMessageChunk` via `session_update()`
12. Return `PromptResponse(stop_reason="end_turn")` to PyCharm

## Type Safety

**Frozen Dataclass:**

`ACPDeps` is frozen per `frozen-dataclass-services` standard. References (`client_conn`, `tracker`) are immutable, but `tracker` is mutable internally (allows `start()` / `progress()` calls to update state).

**Protocol Satisfaction:**

`PunieAgent` must pass `isinstance(agent, Agent)` at runtime. All 14 methods from `src/punie/acp/interfaces.py` must be implemented with exact signatures (including type annotations).

**Pydantic AI Generics:**

- `Agent[ACPDeps, str]` — dependencies are `ACPDeps`, output is `str`
- `AbstractToolset[ACPDeps]` — tools receive `RunContext[ACPDeps]` in first parameter

## Testing Strategy

**FakeClient for Tool Testing:**

`FakeClient` already implements ACP Client protocol methods (`read_text_file`, `session_update`, etc.). Perfect for testing `ACPToolset` without real PyCharm:

```python
fake_client = FakeClient(files={"/test.py": "print('hello')"})
deps = ACPDeps(client_conn=fake_client, session_id="test-1", tracker=ToolCallTracker())

# Tool calls will record to fake_client.notifications
```

**TestModel for Agent Testing:**

Pydantic AI's `TestModel` (model="test") allows testing agent workflows without real LLM calls:

```python
agent = create_pydantic_agent(model="test")
result = await agent.arun("test prompt", deps=deps)
```

**Protocol Satisfaction Test:**

First test in `tests/test_pydantic_agent.py` must be:

```python
def test_punie_agent_satisfies_agent_protocol():
    agent = PunieAgent(...)
    assert isinstance(agent, Agent)
```

Per `protocol-satisfaction-test` standard.

## Migration Path

**Phase 3.2 (This Phase):**
- PunieAgent with `read_file` tool
- TestModel only
- Replace MinimalAgent in test fixtures

**Phase 3.3 (Next):**
- Add `write_file` tool with permission flow
- Add terminal tools
- Test with FakeClient permission queueing

**Phase 3.4 (Later):**
- Configure real LLM models (OpenAI, Anthropic)
- Production agent configuration
- Multi-agent patterns

## Open Questions

**Resolved:**

- ~~Which Pydantic AI version supports AbstractToolset?~~ → 0.1.0+ (check during implementation)
- ~~Should ACPToolset be a class or module-level functions?~~ → Class (AbstractToolset requires it)
- ~~How to test without real LLM?~~ → TestModel (model="test")

**Deferred:**

- Permission flow design → Phase 3.3
- Multi-agent orchestration → Phase 4+
- Pydantic AI serving (to_a2a, to_ag_ui) → TBD

## Success Criteria

1. `isinstance(PunieAgent(...), Agent)` passes
2. `tests/test_stdio_integration.py` passes with PunieAgent (no regressions)
3. New unit tests pass (7 tests in `tests/test_pydantic_agent.py`)
4. Type checking passes (`astral:ty`)
5. Linting passes (`astral:ruff`)
6. Coverage remains >80%
