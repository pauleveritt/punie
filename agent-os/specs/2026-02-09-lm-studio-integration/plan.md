# Plan: LM Studio Integration (Phase 11)

## Context

Punie currently loads MLX models directly in-process via a custom 981-line `MLXModel` implementation. This is fragile (chat template issues, quantization failures, XML/JSON format parsing) and couples model serving to agent logic. Pydantic AI has first-class support for OpenAI-compatible APIs via `OpenAIChatModel` + `OpenAIProvider(base_url=...)`. LM Studio and mlx-lm.server both expose this interface. Switching to it eliminates ~2,400 lines of code (source + tests) and replaces them with ~5 lines of factory logic.

## Objectives

1. Replace MLX direct loading with OpenAI-compatible API client
2. Simplify local model configuration to 3 formats
3. Remove ~2,400 lines of brittle model code
4. Eliminate download-model CLI command
5. Document LM Studio / mlx-lm.server setup

## Architecture Change

### Before
```python
from punie.models.mlx import MLXModel

model = MLXModel(
    model_name="mlx-community/Llama-3.2-3B-Instruct-4bit",
    max_kv_size=8192,
    repetition_penalty=1.1
)
```

### After
```python
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

provider = OpenAIProvider(base_url="http://localhost:1234/v1")
model = OpenAIChatModel("model-name", provider=provider)
```

## Implementation Tasks

1. **Save spec documentation** - Document decisions and standards
2. **Add `_parse_local_spec()` function** - Pure parsing logic with tests
3. **Replace `_create_local_model()`** - Swap MLX for OpenAI provider
4. **Simplify AgentConfig** - Remove MLX-specific fields
5. **Update adapter.py** - Replace import errors with connection errors
6. **Update CLI** - Remove download-model command
7. **Delete MLX files** - Remove ~2,400 lines
8. **Update pyproject.toml** - Swap dependencies
9. **Update documentation** - README and roadmap
10. **Create replacement example** - LM Studio demo
11. **Final verification** - Type check, lint, test

## Local Spec Format

Three supported formats:

1. `""` → `http://localhost:1234/v1` + `"default"`
2. `"model-name"` → `http://localhost:1234/v1` + `"model-name"`
3. `"http://host:port/v1/model"` → custom URL + extracted model

## Benefits

- **Simplicity**: ~2,400 lines deleted, ~5 lines of factory logic added
- **Reliability**: Let LM Studio handle model loading, chat templates, tool calling
- **Flexibility**: Any OpenAI-compatible server works (LM Studio, mlx-lm.server, Ollama)
- **Maintainability**: No custom model implementation to maintain

## Risks & Mitigations

- **Local server must be running**: Document setup clearly, provide helpful error messages
- **API compatibility**: LM Studio and mlx-lm.server are both OpenAI-compatible
- **Migration path**: Document how to switch from old MLX approach

## Success Criteria

- All tests pass with ~80 fewer tests (MLX tests removed)
- Type checking passes
- Linting passes
- Documentation updated
- Example works with LM Studio
