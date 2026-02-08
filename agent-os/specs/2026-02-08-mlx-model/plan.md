# Phase 6.1: Port pydantic-ai-mlx into Punie with Tool Calling

## Context

Enable fully local, offline AI-assisted development on Apple Silicon. The existing `pydantic-ai-mlx` project (by dorukgezici) provides MLX model support for Pydantic AI, but:

1. **Completely broken** with Pydantic AI v1.56.0 — the `AgentModel` class it extends was removed, `Model.agent_model()` was removed, `request()` signature changed, `StreamedResponse` has 4+ new abstract properties. At least 10 fatal incompatibilities.
2. **Tool calling was WIP** — the commit linked by the user shows the approach (map ToolDefinition to OpenAI chat format, include in chat template), but response parsing of tool calls was never implemented.

We will port the sound architectural ideas from pydantic-ai-mlx into Punie, rewritten against the current Pydantic AI `Model` interface, with tool calling completed.

**End result:** `PUNIE_MODEL=local punie` gives PyCharm a fully local AI agent that can read/write files via ACP — no API calls.

## Architecture

### New Pydantic AI Model interface (v1.56.0)

`Model` (abstract class) requires:
- `request(messages, model_settings, model_request_parameters) -> ModelResponse`
- `model_name` property, `system` property
- Tools passed per-request via `ModelRequestParameters.function_tools`

`StreamedResponse` (abstract dataclass) requires:
- `model_request_parameters` init field
- `_get_event_iterator()` abstract method
- `model_name`, `provider_name`, `provider_url`, `timestamp` abstract properties
- `_usage: RequestUsage` (not `Usage`)

### Tool calling approach

MLX models don't have a native function-calling API. Instead:
1. Pass tool definitions to `tokenizer.apply_chat_template(tools=...)` — Qwen2.5-Coder supports this
2. Model outputs `<tool_call>{"name": "...", "arguments": {...}}</tool_call>` blocks
3. Parse these with regex in `request()`, return as `ToolCallPart` in `ModelResponse`
4. Pydantic AI handles the tool execution loop automatically

### Key design decisions

- **No `openai` dependency** — use plain dicts for chat message format (tokenizer expects dicts, not typed objects)
- **Lazy `mlx_lm` imports** — runtime imports in `__init__` and `_generate()`, `TYPE_CHECKING` guard for type hints. Module importable on any platform.
- **Streaming does NOT parse tool calls** — tool calls need full output to detect closing tags. `request()` handles parsing; streaming yields text.
- **`[project.optional-dependencies] local`** — macOS arm64 only, doesn't affect other platforms

## Tasks

### Task 1: Save spec documentation

Create `agent-os/specs/2026-02-08-mlx-model/` with:
- `plan.md` — this plan
- `shape.md` — scope, decisions, context
- `standards.md` — agent-verification, testing/function-based-tests, testing/fakes-over-mocks
- `references.md` — links to pydantic-ai-mlx, Pydantic AI Model interface, MLX, Qwen2.5-Coder

### Task 2: Add optional dependency to pyproject.toml

**Modify:** `pyproject.toml`

Add `[project.optional-dependencies]`:
```toml
[project.optional-dependencies]
local = ["mlx-lm>=0.22.0"]
```

### Task 3: Create `src/punie/models/` package

**Create:** `src/punie/models/__init__.py` — thin package, no unconditional MLX import

### Task 4: Create `src/punie/models/mlx.py` — the core implementation

The main file, containing:

**Pure functions:**
- `parse_tool_calls(text) -> tuple[str, list[dict]]` — regex-based extraction of `<tool_call>...</tool_call>` blocks

**Helper class:**
- `AsyncStream` — wraps sync mlx_lm iterator in async interface (ported from original)

**StreamedResponse subclass:**
- `MLXStreamedResponse(StreamedResponse)` — implements all 4 abstract properties + `_get_event_iterator()`

**Model class:**
- `MLXModel(Model)` — the main implementation:
  - `__init__(model_name, *, settings, profile)` — loads model via `mlx_lm.utils.load()`
  - `model_name` property, `system` property (returns `"mlx"`)
  - `request()` — generates text, parses tool calls, returns `ModelResponse` with `TextPart`/`ToolCallPart`
  - `request_stream()` — streaming text generation
  - `_build_tools(params)` — converts `ToolDefinition` list to OpenAI-format dicts for chat template
  - `_generate(messages, tools, settings, stream)` — applies chat template, calls `mlx_lm.generate()`/`stream_generate()`
  - `_map_message()`, `_map_request()`, `_map_response()` — message format conversion

**Critical files to reference:**
- `.venv/.../pydantic_ai/models/__init__.py` lines 625-860 — `Model` base class
- `.venv/.../pydantic_ai/models/__init__.py` lines 919-1055 — `StreamedResponse` base class
- `.venv/.../pydantic_ai/models/__init__.py` lines 598-622 — `ModelRequestParameters`
- pydantic-ai-mlx `agent_model.py` — message mapping logic to port
- pydantic-ai-mlx `utils.py` — `map_tool_call()` helper to port

### Task 5: Wire into `src/punie/agent/factory.py`

**Modify:** `src/punie/agent/factory.py`

Add `_create_local_model(model_name=None)` helper with conditional import:
```python
if model == "local":
    model = _create_local_model()
elif isinstance(model, str) and model.startswith("local:"):
    model = _create_local_model(model.split(":", 1)[1])
```

Default model: `mlx-community/Qwen2.5-Coder-7B-Instruct-4bit`

### Task 6: Write tests in `tests/test_mlx_model.py`

All tests work WITHOUT `mlx-lm` installed. Groups:

**Pure function tests (~5):** `parse_tool_calls` — single call, multiple calls, no calls, invalid JSON, missing name

**Message mapping tests (~5):** `_map_request` with UserPromptPart, ToolReturnPart, instructions; `_map_response` with TextPart, ToolCallPart. Uses patched `mlx_lm.utils.load`.

**Model property tests (~4):** `model_name`, `system`, `_build_tools` conversion, `_build_tools` empty returns None

**Request integration tests (~3):** `request()` with text response, with tool calls, with mixed text+tools. Mock `_generate()` to return canned text.

**Factory tests (~2):** `model='local'` raises ImportError without mlx-lm; `'local:model-name'` parses correctly

**Total: ~19 tests**, all function-based, fakes over mocks.

### Task 7: Create `examples/15_mlx_local_model.py`

Demonstrates:
1. Creating MLXModel directly
2. Using `create_pydantic_agent(model='local')`
3. Platform guard for non-macOS

### Task 8: Update roadmap and evolution docs

- Mark 6.1 in-progress/complete in `agent-os/product/roadmap.md`
- Add Phase 6.1 narrative to `docs/research/evolution.md`

## Files Summary

| Action | File | Description |
|--------|------|-------------|
| Create | `src/punie/models/__init__.py` | Thin package init |
| Create | `src/punie/models/mlx.py` | MLXModel, MLXStreamedResponse, parse_tool_calls, AsyncStream |
| Modify | `src/punie/agent/factory.py` | Add model='local' and 'local:...' handling |
| Modify | `pyproject.toml` | Add [project.optional-dependencies] local |
| Create | `tests/test_mlx_model.py` | ~19 function-based tests |
| Create | `examples/15_mlx_local_model.py` | Local model demo |
| Create | `agent-os/specs/2026-02-08-mlx-model/` | 4 spec docs |
| Modify | `agent-os/product/roadmap.md` | Mark 6.1 status |
| Modify | `docs/research/evolution.md` | Add 6.1 narrative |

## Verification

1. Use `astral:ruff` skill to check `src/punie/models/ tests/test_mlx_model.py`
2. Use `astral:ty` skill to check `src/punie/models/mlx.py`
3. `uv run pytest tests/test_mlx_model.py -v` — all new tests pass
4. `uv run pytest tests/` — all existing tests still pass
5. Verify `from punie.models.mlx import MLXModel, parse_tool_calls` works without mlx-lm (TYPE_CHECKING guard)
6. Verify `create_pydantic_agent(model='local')` raises clear ImportError without mlx-lm
