# Phase 27 Audit Fixes: Quick Start Guide

## Summary

Fixed 3 critical issues:
1. ✅ **Validation script** - Now checks if correct tool was used (not just "did it produce output?")
2. ✅ **Tool response examples** - Generated 60 multi-turn examples showing what tools return
3. ✅ **Parser tests** - Added 20 comprehensive tests for 6 new parsers (all passing)

## Quick Commands

### 1. Run Semantic Validation (measure real accuracy)

```bash
uv run python scripts/test_phase27_semantic_validation.py fused_model_qwen3_phase27_5bit/
```

**Expected Before Retraining:**
- Overall: ~60% (24/40)
- Direct answers: 100% ✓
- Existing tools: 100% ✓
- New LSP tools: 40% ✗
- Git tools: 60% ✗

### 2. Verify Parser Tests Pass

```bash
uv run pytest tests/test_typed_tools.py -v -k "hover or document_symbols or workspace_symbols or git_status or git_diff or git_log"
```

**Expected:** 20/20 tests pass ✅

### 3. Merge Training Data (for retraining)

```bash
# Create augmented dataset directory
mkdir -p data/phase27_augmented

# Merge all data sources
cat data/phase26_merged/train.jsonl \
    data/phase27_lsp/train.jsonl \
    data/phase27_git/train.jsonl \
    data/phase27_rebalance/train.jsonl \
    data/phase27_direct_answers/train.jsonl \
    data/phase27_tool_responses/train.jsonl \
    | shuf > data/phase27_augmented/train.jsonl

# Same for validation set
cat data/phase26_merged/valid.jsonl \
    data/phase27_lsp/valid.jsonl \
    data/phase27_git/valid.jsonl \
    data/phase27_rebalance/valid.jsonl \
    data/phase27_direct_answers/valid.jsonl \
    | shuf > data/phase27_augmented/valid.jsonl

# Count examples
echo "Training examples: $(wc -l < data/phase27_augmented/train.jsonl)"
echo "Validation examples: $(wc -l < data/phase27_augmented/valid.jsonl)"
```

**Expected:** ~1100 training, ~120 validation examples

### 4. Retrain Model (optional - only if you want to improve from 60% to ~82%)

```bash
# Train from Phase 27 model (warm start)
uv run python -m mlx_lm.lora \
  --model fused_model_qwen3_phase27_5bit/ \
  --data data/phase27_augmented \
  --train \
  --iters 600 \
  --batch-size 1 \
  --learning-rate 1e-4 \
  --adapter-file adapters_phase27_augmented \
  --layers 8
```

**Expected:** Training loss drops from ~2.5 to ~0.5 over 600 iters

### 5. Fuse and Quantize (after retraining)

```bash
# Fuse to float16
uv run python -m mlx_lm.fuse \
  --model fused_model_qwen3_phase27_5bit/ \
  --adapter-path adapters_phase27_augmented \
  --save-path fused_model_qwen3_phase27_augmented_f16 \
  --dequantize

# Quantize to 5-bit (proven optimal in Phase 26)
uv run python -m mlx_lm.convert \
  --hf-path fused_model_qwen3_phase27_augmented_f16 \
  --mlx-path fused_model_qwen3_phase27_augmented_5bit \
  --quantize \
  --q-bits 5 \
  --q-group-size 64
```

### 6. Validate Improved Model

```bash
uv run python scripts/test_phase27_semantic_validation.py fused_model_qwen3_phase27_augmented_5bit/
```

**Expected After Retraining:**
- Overall: ~82% (33/40) ✓
- New LSP tools: 80% ✓
- Git tools: 80% ✓
- Field access: 80% ✓

---

## What Each Fix Does

### Fix 1: Semantic Validation
- **File:** `scripts/test_phase27_semantic_validation.py`
- **What it does:** Checks if model called the correct tool (e.g., `hover()` for hover queries)
- **Why it matters:** Old validation checked `len(response) > 10` - meaningless!

### Fix 2: Tool Response Examples
- **File:** `scripts/generate_tool_response_examples.py`
- **What it does:** Creates 60 multi-turn examples showing what `hover()`, `git_status()`, etc. actually return
- **Why it matters:** Original training had ZERO examples showing tool outputs - model never saw what tools return!

### Fix 3: Parser Tests
- **File:** `tests/test_typed_tools.py` (added 20 tests)
- **What it does:** Comprehensive tests for all 6 new parsers
- **Why it matters:** Original tests covered old tools but not new ones - no confidence in parser correctness

---

## Key Findings from Audit

| Issue | Severity | Status |
|-------|----------|--------|
| Validation uses `len(response) > 10` | CRITICAL | ✅ Fixed |
| Zero tool response examples | CRITICAL | ✅ Fixed |
| Missing parser tests | SERIOUS | ✅ Fixed |
| Only 3-4 patterns per tool | SERIOUS | ⚠️ Mitigated (tool responses add diversity) |
| Train/valid data leakage | SERIOUS | ⏸️ Not fixed yet |
| 111 duplicate examples | MODERATE | ⏸️ Not fixed yet |
| git_log missing author/date | LOW | ⏸️ Not fixed yet |

---

## Decision Points

### Do I Need to Retrain?

**If current accuracy is acceptable (~60%):**
- ❌ No need to retrain
- Use semantic validation to understand real performance
- Fix will be there when you need higher accuracy

**If you need better accuracy (target: ~82%):**
- ✅ Retrain with augmented data
- Adds 60 tool response examples
- Expected improvement: 60% → 82%

### Which Model to Deploy?

**For development/testing:**
- Use `fused_model_qwen3_phase27_5bit/` (current)
- Run semantic validation to see real gaps
- Iterate on training data

**For production:**
- Retrain with `data/phase27_augmented/`
- Deploy `fused_model_qwen3_phase27_augmented_5bit/`
- Validate reaches ≥75% target

---

## Troubleshooting

### Semantic validation shows 60% - is that bad?

**No!** That's the **real** accuracy. The reported 100% was meaningless because validation checked `len(response) > 10`.

60% means:
- ✅ Direct answers: 100%
- ✅ Existing tools (ruff, pytest, typecheck): 100%
- ✗ New tools need more training (especially tool responses)

### Parser tests fail?

Check imports in `tests/test_typed_tools.py`:
```python
from punie.agent.typed_tools import (
    parse_hover_response,
    parse_document_symbols_response,
    parse_workspace_symbols_response,
    parse_git_status_output,
    parse_git_diff_output,
    parse_git_log_output,
    # ... etc
)
```

All parsers are defined in `src/punie/agent/typed_tools.py`.

### Retraining doesn't improve accuracy?

Check:
1. Did you merge all data sources? (should have ~1100 examples)
2. Did you shuffle the data? (`shuf`)
3. Did you train from the right base model? (`fused_model_qwen3_phase27_5bit/`)
4. Did you use the right learning rate? (1e-4 for warm start)

---

## Next Steps After Fixes

1. **Run semantic validation** to measure real baseline (~60%)
2. **Decide if retraining is needed** (depends on accuracy requirements)
3. **If retraining:**
   - Merge data with tool responses
   - Train from Phase 27 model (600 iters)
   - Validate improved model (~82%)
4. **Deploy** the model that meets your accuracy target

---

## Files Reference

| File | Purpose |
|------|---------|
| `scripts/test_phase27_semantic_validation.py` | Semantic validation (correct tool checking) |
| `scripts/generate_tool_response_examples.py` | Tool response example generator |
| `data/phase27_tool_responses/train.jsonl` | 60 multi-turn examples with tool outputs |
| `tests/test_typed_tools.py` | Parser tests (70 total, 20 new) |
| `docs/phase27-audit-fixes.md` | Detailed fix documentation |
| `docs/phase27-audit-quickstart.md` | This file |

---

## Help

For issues or questions:
1. Check `docs/phase27-audit-fixes.md` for detailed explanations
2. Run tests: `uv run pytest tests/test_typed_tools.py -v`
3. Run validation: `uv run python scripts/test_phase27_semantic_validation.py <model_path>`
