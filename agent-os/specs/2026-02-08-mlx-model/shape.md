# Phase 6.1 Shape: Local MLX Model with Tool Calling

## Scope

**In scope:**
- Port pydantic-ai-mlx architecture to current Pydantic AI v1.56.0 `Model` interface
- Implement complete tool calling support for MLX models
- Lazy imports with TYPE_CHECKING guards for cross-platform compatibility
- Function-based tests that work without mlx-lm installed
- Optional dependency for macOS arm64 users only
- Integration with `create_pydantic_agent(model='local')`

**Out of scope:**
- Streaming tool call parsing (streaming yields text only)
- Native MLX function-calling API (doesn't exist)
- Automatic model downloads (user must have model locally)
- Model quantization (use pre-quantized models)
- Multi-turn tool calling optimization (Pydantic AI handles the loop)
- Non-Qwen models without tool-calling chat template support

## Key Decisions

### 1. Use plain dicts for chat format, not openai types

**Decision:** Pass plain Python dicts to `tokenizer.apply_chat_template()`.

**Rationale:** MLX tokenizer expects simple dicts like `{"role": "user", "content": "..."}`. The original pydantic-ai-mlx imported `openai.types.chat` for type hints only, then converted to dicts anyway. We skip the openai dependency entirely.

**Trade-off:** Lose type safety on message format, but gain zero dependencies beyond mlx-lm.

### 2. Lazy imports with TYPE_CHECKING guard

**Decision:** All mlx_lm imports are:
- Inside `TYPE_CHECKING` blocks for type hints
- Runtime imports in `__init__` and `_generate()`

**Rationale:** Module must be importable on Linux/Windows for tests and type checking, even though MLX only runs on macOS arm64.

**Trade-off:** More verbose import pattern, but enables CI to test without mlx-lm.

### 3. No streaming tool call parsing

**Decision:** `request_stream()` yields text only. Tool calls parsed only in `request()`.

**Rationale:** Regex parsing `<tool_call>...</tool_call>` requires complete output. Streaming would need buffering, partial parse states, and complexity not justified by use case.

**Trade-off:** Streaming responses can't execute tools until complete. Acceptable because local models are fast.

### 4. Dependency injection for testability

**Decision:** Use constructor dependency injection + factory method pattern.

```python
# Constructor accepts optional pre-loaded components (for testing)
def __init__(self, model_name, *, model_data=None, tokenizer=None, ...):
    self._model_name = model_name
    self.model_data = model_data
    self.tokenizer = tokenizer

# Factory method loads from mlx-lm (for production)
@classmethod
def from_pretrained(cls, model_name, ...):
    from mlx_lm.utils import load as mlx_load
    model_data, tokenizer = mlx_load(model_name)
    return cls(model_name, model_data=model_data, tokenizer=tokenizer, ...)
```

**Rationale:** Enables testing without monkeypatching. Tests inject mock dependencies directly via constructor. Production code uses `from_pretrained()` to load from mlx-lm.

**Trade-off:** Slightly more complex API (two ways to create), but dramatically cleaner tests with no monkeypatching.

**Test example:**
```python
# No monkeypatching needed!
model = MLXModel("test", model_data=MagicMock(), tokenizer=MagicMock())
model._generate = lambda *args: "mocked response"
```

### 5. Default model: Qwen2.5-Coder-7B-Instruct-4bit

**Decision:** `mlx-community/Qwen2.5-Coder-7B-Instruct-4bit` is the default for `model='local'`.

**Rationale:**
- 4-bit quantization fits in 8GB unified memory
- Qwen2.5-Coder has tool-calling chat template
- 7B size balances quality and speed
- mlx-community models are well-tested

**Trade-off:** Assumes user has downloaded this model. Document in error message if missing.

## Context

### Why now?

Phase 6 focuses on local, offline development:
- 6.0: Mock Model for deterministic testing ✅
- 6.1: **MLX Model for offline development** ← current
- 6.2: Test IDE provider for better test coverage

Local AI enables:
- Zero-cost experimentation during development
- Privacy-sensitive codebases
- Offline coding sessions
- Fast iteration (no API latency)

### What changed since pydantic-ai-mlx?

Pydantic AI v1.56.0 removed/changed:
1. `AgentModel` abstract class → now just `Model`
2. `Model.agent_model()` method → removed
3. `request()` signature → `model_request_parameters` arg added
4. `StreamedResponse` → 4 new abstract properties
5. `Usage` dataclass → `RequestUsage`
6. Tool definitions → now in `ModelRequestParameters.function_tools`

All 6 breaking changes require full rewrite, not a patch.

### Prior art

The pydantic-ai-mlx project by dorukgezici provided:
- Message format mapping (OpenAI-compatible dicts)
- Chat template application with tools
- Async streaming wrapper
- Basic tool calling structure (incomplete)

We port the good ideas (message mapping, chat template approach) and complete the missing parts (tool call parsing, current API compliance).

## Success Criteria

1. ✅ `from punie.models.mlx import MLXModel` works on any platform
2. ✅ `create_pydantic_agent(model='local')` raises ImportError without mlx-lm
3. ✅ With mlx-lm installed, `model='local'` creates working agent
4. ✅ Tool calls parsed from `<tool_call>` tags correctly
5. ✅ All tests pass without mlx-lm installed
6. ✅ Types check with `astral:ty`
7. ✅ Lint passes with `astral:ruff`
8. ✅ Example demonstrates local model usage
