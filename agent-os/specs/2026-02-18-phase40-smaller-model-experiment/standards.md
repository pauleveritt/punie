# Phase 40 Standards

## agent-verification

All new code must pass:
- `astral:ruff` (linting + formatting)
- `astral:ty` (type checking)
- `uv run pytest tests/` (no regressions)

## function-based-tests

Tests are always function-based, never class-based. See `tests/` for examples.

```python
# ✅ Correct
def test_tokenizer_check_passes():
    result = run_tokenizer_check("mlx-community/Qwen3-8B-4bit")
    assert result.special_tokens_match is True

# ❌ Wrong
class TestTokenizerCheck:
    def test_passes(self):
        ...
```

## prompt-format-consistency

**CRITICAL:** All prompt formatting must use `punie.agent.prompt_utils.format_prompt()`.
Never use manual string formatting. This is the Phase 26.1 lesson — wrong format = 60-point
accuracy drop.

```python
# ✅ CORRECT
from punie.agent.prompt_utils import format_prompt
prompt = format_prompt("Check types in src/", model_path)

# ❌ WRONG
prompt = f"User: {query}\nAssistant:"
```

## tokenizer-preflight-gate

The tokenizer preflight check (`scripts/phase40_tokenizer_check.py`) is a **hard gate**:
if any special token ID differs between Qwen3-8B and Qwen3-30B, the script exits with code 1
and the pipeline script must not continue.

Expected IDs (must match exactly):
- `<tool_call>` → 151657
- `</tool_call>` → 151658
- `<tool_response>` → 151665
- `</tool_response>` → 151666
- `<|im_start|>` → 151644
- `<|im_end|>` → 151645

## training-data-unchanged

Phase 40 uses `data/phase33_merged` unchanged. Do not regenerate, reshuffle, or modify the
training data. The goal is to isolate model size as the only variable vs Phase 33b.

## eval-script-reuse

The eval script `scripts/run_phase33_direct_eval.py` is reused for Phase 40 eval. The model
ID detection fix (Task 5) ensures it works with any model name, not just "phase33" models.
