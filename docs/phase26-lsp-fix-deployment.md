# Phase 26: LSP Navigation Fix - Deployment Summary

**Date:** February 15, 2026
**Status:** ✅ **DEPLOYED**
**Production Model:** `fused_model_qwen3_phase26_balanced_5bit/` (19.5 GB)

---

## Problem Solved

**Root Cause:** LSP training examples had different message structure than non-LSP examples, causing the model to use structural shortcuts instead of learning semantic tool selection.

| Feature | LSP Examples (Before) | Non-LSP Examples | LSP Examples (After) |
|---------|----------------------|------------------|---------------------|
| System message | **0%** | 100% | **100%** ✅ |
| Multi-turn format | **0%** | 52% | **37%** ✅ |
| Preambles | **0%** | ~33% | **~33%** ✅ |

**Result:** Model now learns tool selection from **query semantics**, not message structure artifacts.

---

## Implementation

### Task 1: Updated LSP Example Generator ✅

**File:** `scripts/generate_lsp_navigation_examples_expanded.py`

**Changes:**
1. Added `SYSTEM_MESSAGE` constant to all 400 LSP examples
2. Created `create_example_3msg()` and `create_example_5msg()` functions
3. Implemented alternating 3-message/5-message format (~37% multi-turn)
4. Added preambles to ~33% of tool calls ("I'll look up the definition.\n\n", etc.)
5. Generated helper functions for realistic tool_response strings:
   - `make_goto_def_response()` - GotoDefinitionResult repr
   - `make_find_refs_response()` - FindReferencesResult repr

**Generator Functions Updated:**
- `generate_discrimination_examples()` - 100 examples
- `generate_goto_def_field_access()` - 100 examples
- `generate_find_refs_field_access()` - 100 examples
- `generate_workflow_examples()` - 100 examples
- `generate_direct_answer_examples()` - 100 examples

### Task 2: Added System Message Audit Check ✅

**File:** `scripts/audit_training_data.py`

**Changes:**
1. Created `check_system_messages()` function
2. Integrated into audit pipeline (between Format Consistency and Shuffle Quality)
3. Warns if <90% of examples have system messages

### Task 3: Regenerate + Merge + Audit + Train ✅

**Data Pipeline:**
```bash
# 1. Regenerate LSP examples (400 examples, 100% system messages, 37% multi-turn)
uv run python scripts/generate_lsp_navigation_examples_expanded.py

# 2. Merge with non-LSP examples (800 total: 400 LSP + 400 non-LSP)
uv run python scripts/merge_phase26_balanced.py

# 3. Audit (all checks passed)
uv run python scripts/audit_training_data.py data/phase26_balanced/train.jsonl
```

**Audit Results:**
- ✅ Format Consistency: 100% Code Mode (539 examples)
- ✅ System Messages: 100% coverage (720/720)
- ✅ Shuffle Quality: Well distributed
- ✅ Tag Validity: All tags properly closed
- ⚠️ Balance: ruff_check (2.8%), pytest_run (3.8%) underrepresented (expected for LSP-focused phase)

**Training:**
```bash
uv run mlx_lm.lora \
  --model mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit \
  --train --data data/phase26_balanced \
  --adapter-path ./adapters_phase26_balanced \
  --iters 700 --steps-per-eval 50 --steps-per-report 10 \
  --batch-size 1 --learning-rate 1e-4 --num-layers 8
```

**Training Results:**
- Initial val loss: 3.480 → Final val loss: 0.250 (92.8% reduction)
- Final train loss: 0.508
- Total tokens trained: 100,443
- Trainable parameters: 0.231% (70.459M / 30.5B)
- Peak memory: 20.976 GB
- Training time: ~90 minutes

**Model Creation:**
```bash
# Fuse to float16
uv run mlx_lm.fuse \
  --model mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit \
  --adapter-path ./adapters_phase26_balanced \
  --save-path ./fused_model_qwen3_phase26_balanced_f16 \
  --dequantize

# Quantize to 5-bit (best performance from Phase 26.1)
uv run mlx_lm.convert \
  --hf-path ./fused_model_qwen3_phase26_balanced_f16 \
  --mlx-path ./fused_model_qwen3_phase26_balanced_5bit \
  --quantize --q-bits 5
```

**Quantization Result:** 5.501 bits per weight

### Task 4: Validation ✅

**LSP Navigation Validation:**
```bash
uv run python scripts/test_phase26_lsp_validation.py fused_model_qwen3_phase26_balanced_5bit
```

| Metric | Result | Target | Status |
|--------|--------|--------|--------|
| Overall accuracy | **92.0%** | ≥80% | ✅ PASS |
| Tool discrimination | **92.0%** | ≥90% | ✅ PASS |
| Field access | **90.0%** | ≥80% | ✅ PASS |

**By Category:**
- Direct answers: 5/5 (100%)
- Discrimination: 5/5 (100%)
- Find references + fields: 5/5 (100%)
- Goto definition + fields: 4/5 (80%)
- Workflows: 4/5 (80%)

**Improvement:** **+32 percentage points** from 60% baseline!

**Field Access Validation:**
```bash
uv run python scripts/test_phase26_validation.py fused_model_qwen3_phase26_balanced_5bit
```

| Metric | Result | Target | Status |
|--------|--------|--------|--------|
| Overall accuracy | **100%** | ≥80% | ✅ PASS |
| Field access rate | **100%** | ≥80% | ✅ PASS |
| Discrimination | **100%** | 100% | ✅ PASS |

**By Category:**
- A_discrimination: 5/5 (100%)
- B_conditional: 5/5 (100%)
- C_field_access: 5/5 (100%)
- D_iteration: 5/5 (100%)
- E_multistep: 5/5 (100%)

**No regression from 92% baseline!**

### Task 5: Cleanup ✅

**Artifacts Removed:**
1. `fused_model_qwen3_phase26_contrastive_5bit/` (20 GB)
2. `fused_model_qwen3_phase26_contrastive_f16/` (57 GB)
3. `adapters_phase26_contrastive/` (2.1 GB)
4. `fused_model_qwen3_phase26_balanced_f16/` (57 GB)
5. Reverted system prompt hint changes in `src/punie/agent/stubs.py`

**Total Space Reclaimed:** 136.1 GB

---

## Final Results

### Performance Metrics

| Test Suite | Before | After | Improvement |
|------------|--------|-------|-------------|
| LSP Navigation | 60% | **92%** | **+32 points** |
| Field Access | 92% | **100%** | **+8 points** |
| Overall | 76% | **96%** | **+20 points** |

**Speed:** Average generation time: 2.60s

**Size:** 19.5 GB (5-bit quantization)

### Production Model

**Location:** `fused_model_qwen3_phase26_balanced_5bit/`

**Configuration:**
- Base model: Qwen3-Coder-30B-A3B-Instruct-4bit
- Quantization: 5-bit (5.501 bits per weight)
- Training data: 800 examples (400 LSP + 400 non-LSP)
- LoRA parameters: 70.459M (0.231% of total)

**Validation:**
- ✅ LSP navigation: 92% (target: ≥80%)
- ✅ Field access: 100% (target: ≥90%)
- ✅ Tool discrimination: 92% (target: ≥90%)
- ✅ No regressions from Phase 26 baseline

---

## Key Learnings

1. **Structural Consistency is Critical:** Training data format must be uniform across all example types. Message structure differences create spurious shortcuts that override semantic learning.

2. **System Message Coverage:** 100% system message coverage is essential. Even small inconsistencies (0% vs 100%) can cause the model to use presence/absence as a discriminating signal.

3. **Multi-turn Format Matters:** Including realistic multi-turn examples (~37-52%) helps the model learn to use tool results in follow-up reasoning.

4. **5-bit Quantization is Optimal:** Phase 26.1 proved that 5-bit (32 levels) is sufficient to preserve LoRA fine-tuning signal while offering best speed/size/quality balance.

5. **Structural Normalization > Contrastive Training:** Fixing the root cause (structural inconsistency) was more effective than trying to guide the model with prompt hints.

---

## Files Created

### Training Data
- `data/phase26_lsp_expanded/examples.jsonl` - 400 LSP examples (regenerated)
- `data/phase26_balanced/train.jsonl` - 720 training examples
- `data/phase26_balanced/valid.jsonl` - 80 validation examples
- `data/phase26_balanced/metadata.json` - Dataset metadata

### Scripts
- `scripts/generate_lsp_navigation_examples_expanded.py` - Updated LSP generator
- `scripts/merge_phase26_balanced.py` - Balanced dataset merger
- `scripts/audit_training_data.py` - Updated audit with system message check

### Models
- `adapters_phase26_balanced/` - Trained LoRA adapters
- `fused_model_qwen3_phase26_balanced_5bit/` - **Production model** (19.5 GB)

### Validation Results
- `logs/phase26_lsp_validation_fused_model_qwen3_phase26_balanced_5bit.json` - LSP validation results
- `logs/phase26_validation_fused_model_qwen3_phase26_balanced_5bit.json` - Field access validation results

---

## Deployment Checklist

- [x] Updated LSP example generator with system messages and multi-turn format
- [x] Added system message audit check
- [x] Regenerated LSP examples (400, 100% system messages, 37% multi-turn)
- [x] Merged balanced dataset (800 examples: 400 LSP + 400 non-LSP)
- [x] Audited training data (all critical checks passed)
- [x] Trained Phase 26 balanced model (700 iterations)
- [x] Fused adapters to float16
- [x] Quantized to 5-bit (5.501 bits per weight)
- [x] Validated LSP navigation (92% ✅, target: ≥80%)
- [x] Validated field access (100% ✅, target: ≥90%)
- [x] Cleaned up failed experiments (136.1 GB reclaimed)
- [x] Reverted ineffective system prompt hints
- [x] Created deployment summary

---

## Next Steps

**Immediate:**
- Monitor production usage for any edge cases
- Consider expanding non-LSP examples to balance ruff/pytest coverage

**Future Phases:**
- Phase 27: Consider adding more LSP features (hover, completion, etc.)
- Explore additional typed tools with structured output
- Investigate streaming support for long-running tools

---

## References

- **Plan:** `agent-os/specs/2026-02-15-lsp-and-domain-tools-strategy/`
- **Phase 26 Contrastive Attempt:** Failed (48% LSP navigation)
- **Phase 26 Balanced Model:** Success (92% LSP navigation)
- **Phase 26.1:** 5-bit quantization validation
- **Related Docs:** `docs/diary/2026-02-15-phase26-*.md`
