# Ollama Integration Summary

**Date:** 2026-02-17
**Goal:** Add Ollama backend support and validate Code Mode zero-shot performance

## What Changed

### 1. New File: `src/punie/training/ollama.py`

Created `OllamaProcess` class for managing Ollama subprocess lifecycle:
- Similar to `ServerProcess` but for Ollama's API
- Default port: 11434
- Health endpoint: `/api/tags`
- Model pulling: `ollama pull <model>` (idempotent)
- Context manager support for clean lifecycle

**Key features:**
- Automatic model pulling before server start
- Health checking with timeout
- Graceful shutdown (SIGTERM → SIGKILL)
- Environment variable `OLLAMA_HOST` to control port

### 2. Modified: `src/punie/agent/factory.py`

Added `ollama:` model prefix support:
- `create_pydantic_agent(model="ollama:devstral")` now supported
- Uses OpenAI-compatible API at `http://localhost:11434/v1`
- Pattern: `ollama:<model-name>` (e.g., `ollama:devstral`, `ollama:qwen3:30b-a3b`)

### 3. Modified: `src/punie/agent/stubs.py`

Removed Qwen3-specific XML format from Code Mode example:
- **Before:** `<tool_call><function=execute_code>...</function></tool_call>`
- **After:** ` ```python ... ``` ` (plain Python code block)

**Why:** With native API tool calling, the model never generates XML. The XML was Qwen3-specific. This makes the example cleaner and more universal.

### 4. Modified: `src/punie/agent/config.py`

Added `default_stop_sequences(model: str)` helper:
- Returns Qwen-specific stop sequences for Qwen models
- Returns `None` for Ollama/other backends (let server decide)
- Pattern matching: checks if "qwen" in model name or model == "local"

### 5. Modified: `src/punie/cli.py`

Updated documentation:
- `--model` option help text mentions `ollama:devstral`, `ollama:qwen3:30b-a3b`
- `punie serve` docstring documents supported model types (local, ollama:, test)

### 6. New File: `scripts/validate_zero_shot_code_mode.py`

Zero-shot validation script (20-query suite):
- Tests 4 categories: direct answers, single tool, multi-step, field access
- Target: ≥50% accuracy (vs 100% fine-tuned baseline)
- Usage: `python scripts/validate_zero_shot_code_mode.py --model devstral`
- Checks if ollama server is running before starting

**Test categories:**
1. Direct answers (5) - should NOT call tools
2. Single tool calls (5) - should call tools
3. Multi-step Code Mode (5) - should call execute_code
4. Field access (5) - should access structured results

### 7. New File: `tests/test_training_ollama.py`

Unit tests for `OllamaProcess`:
- 8 tests covering base_url, ports, hosts, is_running, health checks
- All tests passing ✅

## How to Use

### Option 1: Start server with ollama model

```bash
# Start ollama (in separate terminal)
ollama serve

# Pull model (first time only)
ollama pull devstral

# Start punie server with ollama model
punie serve --model ollama:devstral

# Connect clients
punie ask "Check for type errors in src/"
```

### Option 2: Test with local agent

```python
from punie.agent.factory import create_local_agent

# Create agent with ollama model
agent, client = create_local_agent(
    model="ollama:devstral",
    workspace=Path.cwd()
)
```

### Option 3: Validate zero-shot performance

```bash
# Ensure ollama is running
ollama serve  # in separate terminal

# Run validation
python scripts/validate_zero_shot_code_mode.py --model devstral
```

## Supported Models

### Local (MLX)
- `local` - mlx_lm.server at http://localhost:1234/v1
- `local:model-name` - custom model name
- `local:http://host:port/v1/model` - custom server

### Ollama
- `ollama:devstral` - Devstral (24B code model)
- `ollama:qwen3:30b-a3b` - Qwen3 via ollama
- `ollama:<any-model>` - Any ollama model

### Test
- `test` - Enhanced test model (no actual LLM)

## Quality Checks

### Tests
```bash
uv run pytest tests/test_training_ollama.py  # 8/8 passed ✅
uv run pytest tests/test_agent_config.py     # 17/17 passed ✅
```

### Linting
```bash
uv run ruff check src/punie/training/ollama.py  # All checks passed! ✅
uv run ruff check src/punie/agent/factory.py    # All checks passed! ✅
uv run ruff check src/punie/agent/stubs.py      # All checks passed! ✅
uv run ruff check src/punie/agent/config.py     # All checks passed! ✅
uv run ruff check scripts/validate_zero_shot_code_mode.py  # All checks passed! ✅
```

## What Does NOT Change

| Component | Why |
|-----------|-----|
| `toolset.py` | `execute_code` is already a PydanticAI tool - works with any backend |
| `monty_runner.py` | Sandbox runs Python from any source - model-agnostic |
| `typed_tools.py` | Pydantic models + parsers are backend-agnostic |
| `lsp_client.py` | LSP client is backend-agnostic |
| `adapter.py` | PunieAgent delegates to PydanticAI - already abstracted |
| Training pipeline | Stays as optional optimization |
| Phase 28-29 WebSocket/Toad | Untouched |

## Files Summary

| File | Action | Size | Tests |
|------|--------|------|-------|
| `src/punie/training/ollama.py` | **New** | 180 lines | ✅ 8/8 |
| `src/punie/agent/factory.py` | **Modified** | +13 lines | ✅ |
| `src/punie/agent/stubs.py` | **Modified** | -10 lines | ✅ |
| `src/punie/agent/config.py` | **Modified** | +25 lines | ✅ 17/17 |
| `src/punie/cli.py` | **Modified** | +5 lines | ✅ |
| `scripts/validate_zero_shot_code_mode.py` | **New** | 285 lines | Manual |
| `tests/test_training_ollama.py` | **New** | 60 lines | ✅ 8/8 |

## Next Steps

### 1. Validation Testing
```bash
# Start ollama
ollama serve

# Pull model
ollama pull devstral

# Run zero-shot validation
python scripts/validate_zero_shot_code_mode.py --model devstral

# Expected: 50-70% accuracy (zero-shot)
# Baseline: 100% (Phase 27 fine-tuned)
```

### 2. If Accuracy is Good (≥70%)
- **Use zero-shot** - no fine-tuning needed!
- Consider adding few-shot examples to system prompt

### 3. If Accuracy is Low (<50%)
- **Option A:** Add fine-tuning (Phase 27 approach)
- **Option B:** Promote typed tools to individual PydanticAI tools
- **Option C:** Try larger model (70B instead of 24B)

### 4. Future Enhancements
- Auto-manage ollama subprocess in `punie serve`
- Add `--backend ollama|mlx` flag for explicit backend selection
- Add ollama health check to `punie serve` startup
- Support GGUF fine-tuning for ollama models

## Compatibility

This change is **additive and non-blocking** for all planned research directions:
- ✅ Monty (Rust sandbox) - backend-agnostic
- ✅ Code Mode evolution - output format, not backend
- ✅ Domain Mode - generates tools, backend irrelevant
- ✅ LSP structure integration - talks to language servers
- ✅ Self-improving flywheel - any backend feeds the flywheel
- ✅ Punie server + subinterpreters - model selection is per-worker config

## Key Learnings

1. **PydanticAI abstraction works perfectly** - adding ollama was just 13 lines in factory.py
2. **Code Mode is backend-agnostic** - model generates Python, sandbox executes it
3. **Stop sequences are model-specific** - ollama handles internally, Qwen needs explicit
4. **XML format was Qwen3-specific** - removed from examples for universality
5. **Zero-shot testing reveals if fine-tuning is needed** - measure first, optimize later

## Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|-----------|
| Devstral can't follow Code Mode stubs zero-shot | Medium | Fallback to individual native tools |
| Ollama subprocess management complexity | Low | Follow proven `ServerProcess` pattern ✅ |
| Qwen3 via ollama behaves differently than mlx_lm | Low | Both expose OpenAI-compatible API |
| Ollama model pulling takes too long | Low | First-time only; show progress to user ✅ |
| 14 tools overwhelm model context | Medium | Test with fewer tools first; monitor |

## Documentation

- [Ollama API Reference](https://github.com/ollama/ollama/blob/main/docs/api.md)
- [PydanticAI Models](https://ai.pydantic.dev/models/)
- [OpenAI-Compatible API](https://platform.openai.com/docs/api-reference)
