# Phase 33 Standards

## agent-verification

All new code must pass:
- `astral:ruff` (linting + formatting)
- `astral:ty` (type checking)
- `uv run pytest tests/` (no regressions)

## function-based-tests

Tests are always function-based, never class-based. See `tests/` for examples.

```python
# ✅ Correct
def test_lora_config_grad_accumulation():
    config = LoRAConfig(...)
    assert "--grad-accumulation-steps" in build_train_command(config)

# ❌ Wrong
class TestLoRAConfig:
    def test_grad_accumulation(self):
        ...
```

## frozen-dataclass-services

All configuration dataclasses use `@dataclass(frozen=True)`. This applies to:
- `LoRAConfig` in `src/punie/training/lora_config.py`
- `EvalPrompt`, `EvalSuite` in `src/punie/training/eval_prompts.py`
- New training configs in `configs/`

## prompt-format-consistency

Training examples must use the `{"messages": [...]}` format throughout:
```json
{"messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
]}
```

This matches what `mlx_lm.lora` expects. Never use a different format.

## tool-call-format

Tool calls in training examples must use the `execute_code` format:
```
<tool_call><function=execute_code>
<parameter=code>
# Python code here
result = some_tool(args)
print(result)
</parameter>
</function></tool_call>
```

This matches the tokenizer's chat template and what Punie validates.
