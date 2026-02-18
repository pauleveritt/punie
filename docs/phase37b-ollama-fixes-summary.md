# Phase 37b: Ollama Tool Calling Compatibility Fixes

**Status:** ✅ IMPLEMENTED (awaiting validation with Ollama running)

## Summary

Fixed two root causes preventing Ollama models (especially Devstral) from successfully calling tools through PydanticAI.

## Changes Implemented

### 1. Created OllamaChatModel subclass (`src/punie/agent/ollama_model.py`)

**Problem:** PydanticAI's default `OpenAIChatModel` sets `content: null` when assistant messages contain only tool calls (no text). Ollama's Go parser rejects this:

```go
// Ollama rejects content:null unless tool_calls present
if msg.ToolCalls == nil {
    return nil, fmt.Errorf("invalid message content type: %T", content)
}
```

**Solution:** Override `_into_message_param()` to emit `content: ""` (empty string) instead of `content: null`:

```python
class OllamaChatModel(OpenAIChatModel):
    @dataclass
    class _MapModelResponseContext(OpenAIChatModel._MapModelResponseContext):
        def _into_message_param(self) -> chat.ChatCompletionAssistantMessageParam:
            message_param = chat.ChatCompletionAssistantMessageParam(role="assistant")

            # Always set content to a string (empty if no text)
            if self.texts:
                message_param["content"] = "\n\n".join(self.texts)
            else:
                message_param["content"] = ""  # Empty string, not null

            if self.tool_calls:
                message_param["tool_calls"] = self.tool_calls

            return message_param
```

### 2. Switched to OllamaProvider (`src/punie/agent/factory.py`)

**Problem:** Factory was using generic `OpenAIProvider` instead of PydanticAI's `OllamaProvider`, missing Ollama-specific model profiles (Mistral profile for Devstral, etc.).

**Solution:** Use `OllamaProvider` + `OllamaChatModel`:

```python
# Before (Phase 37)
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

provider = OpenAIProvider(base_url="http://localhost:11434/v1", api_key="ollama")
model = OpenAIChatModel(model_name, provider=provider)

# After (Phase 37b)
from pydantic_ai.providers.ollama import OllamaProvider
from punie.agent.ollama_model import OllamaChatModel

provider = OllamaProvider(base_url="http://localhost:11434/v1")
model = OllamaChatModel(model_name, provider=provider)
```

### 3. Added comprehensive tests

**File:** `tests/test_ollama_model.py` (8 tests)

Tests verify:
- Content is empty string (not null) when only tool calls present ✅
- Content contains text when both text and tool calls present ✅
- Content contains text when only text (no tool calls) ✅
- Multiple text segments joined with `\n\n` ✅
- Thinking fields added correctly ✅
- Empty context produces empty string content ✅

**File:** `tests/test_agent_config.py` (3 new integration tests)

Tests verify:
- `create_pydantic_agent("ollama:devstral")` creates `OllamaChatModel` ✅
- Ollama models have no stop_sequences in model_settings ✅
- `create_local_agent("ollama:devstral")` has no stop_sequences ✅

## Test Results

```
✅ 27/27 tests passing
✅ ruff check: All checks passed
✅ ty check: All checks passed
✅ Module imports successfully
```

## Expected Improvements (Pending Validation)

### Phase 37 Baseline (with bugs):
- **Direct answers:** 5/5 (100%) ✅
- **API errors:** 9/17 (53%) ❌ `"invalid message content type: <nil>"`
- **Tool calling:** 3/17 (17%) ❌ Most failed instantly

### Phase 37b Expected (with fixes):
- **Direct answers:** 5/5 (100%) — Should remain unchanged
- **API errors:** ~0/17 (0%) — Should drop to near zero
- **Tool calling:** Significant improvement expected — Models can now respond with tool-only messages

### Queries that should now work:
- ✅ "Run ruff" — Was failing (2.11s) with content:null error
- ✅ "Check git status" — Was failing (2.29s) with content:null error
- ✅ "Run pytest" — Was failing (2.18s) with content:null error
- ✅ "Check type errors" — Already worked (29.71s) but should be more reliable

## What This Does NOT Fix

1. **Code Mode (0%):** Devstral doesn't follow `execute_code()` stubs zero-shot. Would need fine-tuning (future phase).

2. **Multi-turn tool calling:** Devstral template bug (ollama/ollama#11296) strips tool definitions after first round-trip. Upstream fix needed.

3. **Performance (~30s/query):** Inherent to running 24B model via Ollama on this hardware. Not a bug.

## Files Modified

| File | Lines | Change Type |
|------|-------|-------------|
| `src/punie/agent/ollama_model.py` | +62 | NEW — OllamaChatModel subclass |
| `src/punie/agent/factory.py` | 4 | MODIFIED — Switch to OllamaProvider |
| `tests/test_ollama_model.py` | +111 | NEW — Unit tests |
| `tests/test_agent_config.py` | +17 | MODIFIED — Integration tests |

## Validation Command

When Ollama is running with Devstral loaded:

```bash
# Start Ollama if needed
ollama serve

# Load Devstral (if not already loaded)
ollama pull devstral

# Run validation
uv run python scripts/validate_zero_shot_code_mode.py --model devstral
```

## Next Steps

1. **Run validation** when Ollama is available to confirm improvements
2. **Document results** in `docs/phase37-devstral-zero-shot-results.md`
3. **Update MEMORY.md** with Phase 37b results
4. **Consider Phase 38** for fine-tuning Devstral on Code Mode (if zero-shot tool calling proves viable)
