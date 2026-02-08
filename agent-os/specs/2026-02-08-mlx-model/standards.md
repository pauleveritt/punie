# Phase 6.1 Standards

This phase adheres to the following Punie and Agent OS standards:

## agent-verification

All code passes:
- `astral:ruff` — linting and formatting
- `astral:ty` — type checking
- `uv run pytest tests/test_mlx_model.py -v` — unit tests
- `uv run pytest tests/` — integration with existing tests

## testing/function-based-tests

All tests in `tests/test_mlx_model.py` are function-based:

```python
def test_parse_single_tool_call():
    """Parse a single tool call from model output."""
    text = 'Some text<tool_call>{"name": "read", "arguments": {"path": "foo.py"}}</tool_call>'
    content, calls = parse_tool_calls(text)
    assert content == "Some text"
    assert len(calls) == 1
    assert calls[0]["name"] == "read"
```

No test classes. Clean, focused test functions.

## testing/fakes-over-mocks

Prefer dependency injection and simple test doubles over monkeypatching:

```python
def test_request_with_text_response():
    """MLXModel.request() returns text response correctly."""
    # Use dependency injection to create testable model (no mlx-lm needed!)
    model = MLXModel("test", model_data=MagicMock(), tokenizer=MagicMock())

    # Override _generate with simple lambda returning test data
    model._generate = lambda *args, **kwargs: "Hello from MLX"

    response = model.request(messages=[...], ...)
    assert len(response.parts) == 1
    assert response.parts[0].content == "Hello from MLX"
```

**Key principle:** Design for testability via dependency injection, not monkeypatching.

## lazy-imports

Critical for cross-platform compatibility:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mlx_lm.utils import load as mlx_load
    from mlx_lm import generate, stream_generate

class MLXModel(Model):
    def __init__(self, model_name: str, *, settings: dict[str, Any] | None = None):
        try:
            from mlx_lm.utils import load as mlx_load
        except ImportError as e:
            raise ImportError(
                "mlx-lm is required for local model support. "
                "Install with: uv pip install 'punie[local]'"
            ) from e

        self._model_name = model_name
        self.model_data, self.tokenizer = mlx_load(model_name)
```

## pure-functions-first

`parse_tool_calls()` is a pure function, easy to test:

```python
def parse_tool_calls(text: str) -> tuple[str, list[dict[str, Any]]]:
    """Extract tool calls from model output.

    Args:
        text: Model output possibly containing <tool_call>...</tool_call> blocks

    Returns:
        Tuple of (remaining_text, list of tool call dicts)
    """
    import json
    import re

    pattern = r'<tool_call>(.*?)</tool_call>'
    matches = re.findall(pattern, text, re.DOTALL)

    calls = []
    for match in matches:
        try:
            call = json.loads(match.strip())
            if "name" in call:
                calls.append(call)
        except json.JSONDecodeError:
            continue

    # Remove tool call tags from text
    clean_text = re.sub(pattern, '', text, flags=re.DOTALL).strip()

    return clean_text, calls
```

No side effects, no state, deterministic output.
