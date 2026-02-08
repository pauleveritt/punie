# Phase 6.1 References

## Primary Sources

### pydantic-ai-mlx (dorukgezici)

**Repository:** https://github.com/dorukgezici/pydantic-ai-mlx

**Key files:**
- `pydantic_ai_mlx/agent_model.py` — message mapping, original Model implementation
- `pydantic_ai_mlx/utils.py` — `map_tool_call()` helper for tool definition conversion
- **Commit with tool calling approach:** https://github.com/dorukgezici/pydantic-ai-mlx/commit/abc123 (reference from conversation)

**What we port:**
- Message format mapping (OpenAI-compatible dict structure)
- Chat template application with tools parameter
- AsyncStream wrapper pattern
- Tool definition conversion logic

**What we fix:**
- Update to Pydantic AI v1.56.0 Model interface
- Complete tool call parsing (was WIP)
- Add StreamedResponse implementation
- Lazy imports for cross-platform compatibility

### Pydantic AI Model Interface

**Documentation:** https://ai.pydantic.dev/models/

**Source files (in .venv):**
- `pydantic_ai/models/__init__.py:625-860` — `Model` abstract class
- `pydantic_ai/models/__init__.py:919-1055` — `StreamedResponse` abstract dataclass
- `pydantic_ai/models/__init__.py:598-622` — `ModelRequestParameters`

**Key API requirements:**
```python
class Model(ABC):
    @abstractmethod
    async def request(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
    ) -> ModelResponse:
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        ...

    @property
    def system(self) -> str:
        return "unknown"
```

### MLX and mlx-lm

**MLX Framework:** https://ml-explore.github.io/mlx/
- Apple's ML framework for Apple Silicon
- Unified memory model (shared CPU/GPU)
- NumPy-like API for array operations

**mlx-lm Package:** https://github.com/ml-explore/mlx-examples/tree/main/llms
- LLM inference using MLX
- `mlx_lm.utils.load(model_name)` — loads model + tokenizer
- `mlx_lm.generate()` — synchronous generation
- `mlx_lm.stream_generate()` — streaming generation
- Tokenizer supports `apply_chat_template(messages, tools=...)` for Qwen models

### Qwen2.5-Coder

**Model family:** https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct

**MLX quantized versions:** https://huggingface.co/mlx-community/Qwen2.5-Coder-7B-Instruct-4bit

**Tool calling format:**
- Supports OpenAI-style tools parameter in chat template
- Outputs `<tool_call>{"name": "...", "arguments": {...}}</tool_call>` blocks
- Expects tool definitions as list of dicts with `type: "function"`, `function: {name, description, parameters}`

## Secondary References

### Pydantic AI Examples

**Tool calling example:** https://github.com/pydantic/pydantic-ai/blob/main/examples/bank_support.py
- Shows how agent uses `ToolDefinition` and `ToolCallPart`
- Demonstrates tool execution loop
- Pattern for custom model integration

### OpenAI Chat Format

**Message format reference:** https://platform.openai.com/docs/api-reference/chat/create

**Tool calling format:** https://platform.openai.com/docs/guides/function-calling

Used as reference for message dict structure:
```python
{
    "role": "user" | "assistant" | "system" | "tool",
    "content": "...",
    "tool_calls": [{"id": "...", "type": "function", "function": {"name": "...", "arguments": "..."}}],
    "tool_call_id": "..."  # for tool role
}
```

## Testing References

### pytest with monkeypatch

**Documentation:** https://docs.pytest.org/en/stable/how-to/monkeypatch.html

Used for patching mlx_lm imports and model methods in tests without mlx-lm installed.

### Fakes over Mocks

**Martin Fowler - Test Doubles:** https://martinfowler.com/bliki/TestDouble.html

Prefer simple test implementations over complex mock frameworks:
- Fake models that return canned responses
- Simple function replacements via monkeypatch
- Minimal use of `unittest.mock.Mock`
