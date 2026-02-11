# References: LM Studio Integration

## Pydantic AI

### OpenAIProvider
- **Source**: `pydantic_ai.providers.openai.OpenAIProvider`
- **Purpose**: Configure OpenAI API client with custom base URL
- **Key Feature**: Auto-sets `api_key='api-key-not-set'` when base_url provided and no OPENAI_API_KEY env var
- **Usage**:
  ```python
  provider = OpenAIProvider(base_url="http://localhost:1234/v1")
  ```

### OpenAIChatModel
- **Source**: `pydantic_ai.models.openai.OpenAIChatModel`
- **Purpose**: Chat model using OpenAI-compatible API
- **Usage**:
  ```python
  model = OpenAIChatModel("model-name", provider=provider)
  ```

## LM Studio

- **Website**: https://lmstudio.ai/
- **API**: OpenAI-compatible at `http://localhost:1234/v1`
- **Features**:
  - Load any GGUF model
  - Tool calling support
  - Streaming responses
  - Model management UI

## mlx-lm.server

- **Source**: `mlx-lm` package
- **Command**: `mlx-lm.server --model <model-name>`
- **API**: OpenAI-compatible at `http://localhost:8080/v1` (default)
- **Features**:
  - Apple Silicon optimized
  - Tool calling support
  - Streaming responses

## Existing Patterns

### Factory Pattern (factory.py)

Current pattern for model creation:
```python
def _create_anthropic_model(spec: str = "claude-4.6-sonnet") -> AnthropicModel:
    # Parse spec and return model
    ...

def create_pydantic_agent(...) -> Agent:
    if model_spec.startswith("local:"):
        model = _create_local_model(model_spec[6:])
    elif model_spec.startswith("openai:"):
        model = _create_openai_model(model_spec[7:])
    else:
        model = _create_anthropic_model(model_spec)
```

### Error Handling Pattern

From adapter.py (lines 259-298), current MLX import error handling:
```python
try:
    from punie.models.mlx import MLXModel
except ImportError as e:
    # Provide helpful error message
    raise RuntimeError("MLX support requires...") from e
```

New pattern will catch connection errors instead:
```python
try:
    # Attempt to use local model
    ...
except ConnectionError as e:
    raise RuntimeError(
        "Local model server not available. "
        "Start LM Studio or mlx-lm.server first."
    ) from e
```

## OpenAI API Compatibility

### Endpoints Used
- `POST /v1/chat/completions` - Send messages, get responses
- Streaming via Server-Sent Events (SSE)
- Tool calling via function definitions in request

### Request Format
```json
{
  "model": "model-name",
  "messages": [...],
  "tools": [...],
  "stream": true
}
```

### Response Format
```json
{
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "...",
        "tool_calls": [...]
      }
    }
  ]
}
```

## Migration Notes

### Before (MLX Direct)
```python
from punie.models.mlx import MLXModel

model = MLXModel(
    model_name="mlx-community/Llama-3.2-3B-Instruct-4bit",
    max_kv_size=8192,
    repetition_penalty=1.1
)
```

### After (LM Studio)
```python
# Start LM Studio or mlx-lm.server first
# Load model in UI or via: mlx-lm.server --model <model-name>

# Then in Punie:
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

provider = OpenAIProvider(base_url="http://localhost:1234/v1")
model = OpenAIChatModel("model-name", provider=provider)
```

### CLI Changes
```bash
# Before
punie download-model mlx-community/Llama-3.2-3B-Instruct-4bit
punie ask "query" --model local: --max-kv-size 8192

# After
# Start LM Studio first, load model in UI
punie ask "query" --model local:
```
