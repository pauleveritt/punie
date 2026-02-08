# Plan: Convert to Best-Practices Pydantic AI Project (Phase 3.4)

## Context

Phase 3.3 completed the full toolset (7 tools covering all ACP Client methods). The agent works but uses pre-v1 patterns: `system_prompt=` instead of `instructions=`, no model settings, no output validation, no error handling in tools, and no retry configuration. Phase 3.4 adopts Pydantic AI v1 idioms to make this a properly structured project.

**Goal:** Adopt Pydantic AI v1 idioms — `instructions=`, `ModelSettings`, output validation, `ModelRetry` error handling in tools, and error handling in the adapter — while keeping `str` output type.

## Architecture

### Agent Configuration (factory.py)

**Current (pre-v1):**
```python
agent = Agent[ACPDeps, str](
    model,
    deps_type=ACPDeps,
    system_prompt="You are Punie...",
    toolsets=[create_toolset()],
)
```

**Target (v1):**
```python
PUNIE_INSTRUCTIONS = """
You are Punie, an AI coding assistant that works inside PyCharm.
[Full guidelines...]
"""

agent = Agent[ACPDeps, str](
    model,
    deps_type=ACPDeps,
    instructions=PUNIE_INSTRUCTIONS,
    model_settings=ModelSettings(temperature=0.0, max_tokens=4096),
    retries=3,
    output_retries=2,
    toolsets=[create_toolset()],
)

@agent.output_validator
def validate_response(ctx: RunContext[ACPDeps], output: str) -> str:
    if not output or not output.strip():
        raise ModelRetry("Response was empty, please provide a substantive answer.")
    return output
```

### Tool Error Handling (toolset.py)

**Current:** No error handling, ACP exceptions propagate uncaught.

**Target:** All tools raise `ModelRetry` on errors:

**Tracked tools** (read_file, write_file, run_command):
```python
async def read_file(ctx: RunContext[ACPDeps], path: str) -> str:
    tool_call_id = f"read_{path}"
    start = ctx.deps.tracker.start(...)
    await ctx.deps.client_conn.session_update(ctx.deps.session_id, start)
    try:
        response = await ctx.deps.client_conn.read_text_file(...)
        progress = ctx.deps.tracker.progress(...)
        await ctx.deps.client_conn.session_update(ctx.deps.session_id, progress)
        return response.content
    except Exception as exc:
        raise ModelRetry(f"Failed to read {path}: {exc}") from exc
    finally:
        ctx.deps.tracker.forget(tool_call_id)
```

**Simple tools** (terminal lifecycle):
```python
async def get_terminal_output(ctx: RunContext[ACPDeps], terminal_id: str) -> str:
    try:
        response = await ctx.deps.client_conn.terminal_output(...)
        return response.output
    except Exception as exc:
        raise ModelRetry(f"Failed to get output for terminal {terminal_id}: {exc}") from exc
```

### Adapter Error Handling (adapter.py)

**Current:** `agent.run()` called directly, errors propagate.

**Target:** Wrap `agent.run()` in try/except:

```python
try:
    result = await self._pydantic_agent.run(
        user_prompt=message_param["content"],
        deps=deps,
        usage_limits=self._usage_limits,
    )
except UsageLimitExceeded as exc:
    await client.session_update(
        session_id, text_block(f"Usage limit exceeded: {exc}")
    )
    return PromptResponse(stop_reason="end_turn")
except Exception as exc:
    logger.exception("Agent run failed")
    await client.session_update(
        session_id, text_block(f"Agent error: {exc}")
    )
    return PromptResponse(stop_reason="end_turn")
```

## Tasks

See implementation tracking in roadmap.md Phase 3.4.

## Files Summary

| Action | Files |
|--------|-------|
| **Create (spec)** | `agent-os/specs/2026-02-08-pydantic-ai-best-practices/{plan,shape,standards,references}.md` |
| **Modify** | `src/punie/agent/factory.py` — instructions, model_settings, retries, output_validator |
| **Modify** | `src/punie/agent/toolset.py` — try/except/finally + ModelRetry in all 7 tools |
| **Modify** | `src/punie/agent/adapter.py` — error handling in prompt(), usage_limits param, logging |
| **Modify** | `tests/test_pydantic_agent.py` — 8 new tests |
| **Modify** | `agent-os/product/roadmap.md` — mark 3.4 complete |

## Design Decisions

1. **`instructions=` over `system_prompt=`** — v1 idiom. Instructions are not retained in message history and are re-evaluated per run. Static constant is fine since we don't need RunContext access.

2. **Keep `str` output type** — The ACP adapter sends text via `session_update`. Structured output adds complexity without clear benefit at this stage.

3. **`ModelRetry` over return strings for errors** — When a tool fails (ACP error, file not found), raise `ModelRetry` so the LLM retries with different parameters. Permission denials still return strings (the LLM should know about denied permissions, not retry blindly).

4. **`finally` for tracker cleanup** — Move `tracker.forget()` to `finally` blocks so it runs on both success and error paths, preventing leaked tracked tool calls.

5. **Adapter catches all exceptions** — `prompt()` wraps `agent.run()` in try/except to prevent ACP protocol-level crashes. Errors are communicated to the IDE via session_update text.

6. **Deterministic model settings** — `temperature=0.0` for consistent coding behavior, `max_tokens=4096` to allow full responses.

7. **Conservative retry counts** — `retries=3` for tool errors, `output_retries=2` for validation. Balances reliability with responsiveness.
