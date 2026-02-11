# Shape: LM Studio Integration

## Scope

**In Scope:**
- Replace MLX direct loading with OpenAI-compatible API
- Simplify local model spec to 3 formats
- Delete MLX model implementation and tests (~2,400 lines)
- Update CLI to remove download-model command
- Document LM Studio / mlx-lm.server setup

**Out of Scope:**
- Changing remote model behavior (Anthropic, OpenAI)
- Adding new model providers beyond OpenAI-compatible
- Auto-starting local model servers
- Model selection UI

## Key Decisions

1. **Use Pydantic AI's OpenAI provider** - First-class support, well-tested
2. **Support 3 spec formats** - Default, model-only, full URL
3. **Remove all MLX code** - Clean break, no backwards compatibility
4. **Require external server** - Don't bundle model serving in agent

## Data Structures

### LocalModelSpec

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class LocalModelSpec:
    """Parsed local model specification."""
    base_url: str
    model_name: str
```

### Constants

```python
DEFAULT_LOCAL_BASE_URL = "http://localhost:1234/v1"
DEFAULT_LOCAL_MODEL = "default"
```

## Function Signature

### _parse_local_spec()

```python
def _parse_local_spec(spec: str = "") -> LocalModelSpec:
    """Parse local model specification string.

    Supports three formats:
    1. "" (empty) → default URL + default model
    2. "model-name" → default URL + given model
    3. "http://host:port/v1/model" → custom URL + model

    Args:
        spec: Model specification string

    Returns:
        LocalModelSpec with base_url and model_name

    Examples:
        >>> _parse_local_spec("")
        LocalModelSpec(base_url='http://localhost:1234/v1', model_name='default')

        >>> _parse_local_spec("my-model")
        LocalModelSpec(base_url='http://localhost:1234/v1', model_name='my-model')

        >>> _parse_local_spec("http://localhost:8080/v1/custom-model")
        LocalModelSpec(base_url='http://localhost:8080/v1', model_name='custom-model')
    """
```

## Test Cases

1. Empty string → default URL + default model
2. Model name only → default URL + given model
3. Full URL with model → parsed URL + model
4. URL without trailing slash → normalized
5. URL with port → preserved
6. Localhost variations (127.0.0.1, localhost)
7. HTTPS URLs → supported

## File Changes

### Modified
- `src/punie/agent/factory.py` - Add parsing, replace model creation
- `src/punie/agent/config.py` - Remove MLX fields
- `src/punie/agent/adapter.py` - Update error handling
- `src/punie/cli.py` - Remove download command
- `pyproject.toml` - Swap dependencies

### Created
- `tests/test_local_model_spec.py` - Parsing tests
- `tests/test_local_server_fallback.py` - Connection error tests
- `examples/15_local_model_server.py` - LM Studio demo
- `agent-os/specs/2026-02-09-lm-studio-integration/` - Spec docs

### Deleted
- `src/punie/models/` - Entire directory (3 files, ~1,137 lines)
- `examples/15_mlx_local_model.py` - Old example
- `tests/test_mlx_model.py` - MLX tests (~784 lines)
- `tests/test_mlx_fallback.py` - Import error tests
- `tests/test_memory.py` - Memory tests
- `tests/test_cli_download.py` - Download command tests (~188 lines)
- `agent-os/specs/2026-02-08-mlx-model/` - Old spec
- `agent-os/specs/2026-02-08-model-download/` - Old spec

## Protocol Satisfaction

The implementation satisfies the OpenAI-compatible protocol:
- POST /v1/chat/completions for messages
- Streaming via SSE
- Tool calling via function definitions
- Standard request/response format

Both LM Studio and mlx-lm.server implement this protocol.
