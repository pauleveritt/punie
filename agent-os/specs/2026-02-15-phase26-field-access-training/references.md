# Phase 26: Train Structured Field Access Patterns - References

## Critical Files

### Training Infrastructure
- `src/punie/training/dataset.py` — `TrainingDataset`, `TrainingExample`, `ChatMessage` dataclasses
- `src/punie/training/dataset_io.py` — Read/write JSONL utilities
- `src/punie/training/dataset_validation.py` — `validate_dataset()` structural checks
- `src/punie/training/checks.py` — Pre/post-training validation checks (14 functions)
- `src/punie/training/tool_call_parser.py` — Production parser (`parse_tool_calls()`)
- `src/punie/training/hyperparam.py` — Loss curve parsing

### Typed Tools
- `src/punie/agent/typed_tools.py` — Pydantic models for typecheck, ruff_check, pytest_run
  - `TypeCheckResult`: success, error_count, warning_count, errors[], parse_error
  - `RuffResult`: success, violation_count, fixable_count, violations[], parse_error
  - `TestResult`: success, passed, failed, errors, skipped, duration, tests[], parse_error

### Existing Training Data
- `data/phase22_code_format/` — 707 examples, text format with execute_code pattern
- `data/ty_training/ty_examples.jsonl` — 50 ty examples, messages format (no system)
- `data/ruff_training/ruff_examples.jsonl` — 50 ruff examples, Format B
- `data/pytest_training/pytest_examples.jsonl` — 50 pytest examples, Format B
- `data/phase23_merged/` — 757 examples, text format (Phase 22 + ty merged)

### Example Generation Scripts
- `scripts/generate_ty_training_data.py` — Pattern for generating typed tool examples
- `scripts/generate_code_workflows.py` — Multi-step workflow patterns
- `scripts/convert_to_code_format.py` — XML → Python code conversion

### Pipeline Scripts
- `scripts/train_phase23.sh` — Baseline training configuration (500 iters)
- `scripts/fuse_phase23.sh` — Fusion with dequantize flag
- `scripts/quantize_6bit.sh` — 6-bit quantization (proven optimal)

### Validation Scripts
- `scripts/test_phase23_task11.py` — Phase 23 validation suite (baseline 0% field access)
- `scripts/test_single_model.py` — Single model tester

## Prior Phases

### Phase 22: Code Mode (Feb 14, 2026)
**Innovation:** Model generates Python code instead of XML/JSON tool calls

**Format:**
```xml
<tool_call><function=execute_code>
<parameter=code>
result = read_file("config.py")
print(result)
</parameter>
</function></tool_call>
```

**Training:** 707 examples, perplexity 1.826, 100% discrimination
**Known gap:** No field access patterns

### Phase 23: ty Integration (Feb 14, 2026)
**Innovation:** First typed tool (typecheck) with structured output

**Training:** 757 examples (707 Phase 22 + 50 ty)
**Results:** Val loss 0.610 (84% reduction), 100% tool calling accuracy
**Gap identified:** 0% field access rate — model never uses result.error_count, result.errors, etc.

**Validation breakdown:**
- Single-tool discrimination: 100% (5/5) ✅
- Multi-step workflows: 20% (1/5) ❌
- Structured field access: 0% (0/4) ❌ **← Critical gap**

**Root cause:** Only ~4.5% of training examples show field access

### Phase 24: ruff + pytest (Feb 14, 2026)
**Innovation:** Added 2 more typed tools (ruff_check, pytest_run)

**Training data:** 857 examples total (707 Phase 22 + 50 ty + 100 ruff/pytest)
**Status:** Data generated and merged but **never trained** — Phase 23 model is production

**Key observation:** Phase 24 ruff/pytest examples DO show field access (~30% of 100 examples)

### Phase 25: 7B Experiment (Feb 15, 2026)
**Goal:** Test if Qwen2.5-Coder-7B can match Qwen3-30B-A3B

**Result:** INCONCLUSIVE — experiment had 5 critical setup flaws
**Decision:** Stick with Qwen3-30B-A3B (proven 100% accuracy, 1.94s avg)

## Format Evolution

### Text Format (Phases 1-23)
```json
{
  "text": "<|im_start|>system\nYou are Punie...<|im_end|>\n<|im_start|>user\nQuery<|im_end|>\n<|im_start|>assistant\nResponse<|im_end|>"
}
```

**Usage:** mlx_lm training expects this format
**Issue:** Hard to manipulate programmatically

### Messages Format (Phase 24+)
```json
{
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ]
}
```

**Usage:** OpenAI-style chat completion format
**Benefit:** Easy to manipulate with `TrainingExample` / `ChatMessage`
**Conversion:** `convert_messages_to_text()` in merge scripts

### Format A vs Format B

**Format B (Phase 24 ruff/pytest):**
```xml
<tool_call>
result = ruff_check("src/")
print(f"Violations: {result.violation_count}")
</tool_call>
```

**Format A (Phase 26 target):**
```xml
<tool_call><function=execute_code>
<parameter=code>
result = ruff_check("src/")
print(f"Violations: {result.violation_count}")
</parameter>
</function></tool_call>
```

**Difference:** Format A adds XML wrapper (`<function=execute_code><parameter=code>`)

## Validation Checks Reference

### Pre-Training Checks
- `check_format_consistency()` — All examples use same top-level format (messages vs text)
- `check_training_data_distribution()` — Tool vs direct-answer balance (10-80% tools)
- `check_training_data_content()` — No empty or placeholder tool results
- `check_training_data_coverage()` — Expected patterns present (NEW: field access patterns)
- `check_system_prompt_consistency()` — All examples use same system prompt
- `check_dataset_structural_validation()` — Wraps `validate_dataset()` from dataset_validation.py

### Post-Training Checks
- `check_training_loss()` — Loss decreased and final < 2.0
- `check_adapter_files()` — Adapter directory has required files (adapters.safetensors, adapter_config.json)

### Post-Fusion Checks
- `check_fused_model_config()` — Config has correct eos_token_id (151645 for Qwen3)

### Post-Quantization Checks
- `check_quantized_model_config()` — Config shows correct bit level (6-bit target)
- `check_quantized_model_smoke_test()` — Model output contains expected patterns

### Runtime Checks
- `check_eval_parser_matches_training_format()` — Parser can extract tool calls from training format

## Command Reference

### Training
```bash
uv run python -m mlx_lm.lora \
  --model mlx-community/Qwen3-30B-A3B-Instruct-4bit \
  --data data/phase26_merged \
  --train \
  --iters 500 \
  --batch-size 1 \
  --learning-rate 1e-4 \
  --lora-layers 8 \
  --adapter-path ./adapters_phase26
```

### Fusion (dequantize to float16)
```bash
uv run python -m mlx_lm.fuse \
  --model mlx-community/Qwen3-30B-A3B-Instruct-4bit \
  --adapter-path ./adapters_phase26 \
  --save-path ./fused_model_qwen3_phase26_f16 \
  --dequantize
```

### Quantization (6-bit)
```bash
uv run python -m mlx_lm.convert \
  --hf-path ./fused_model_qwen3_phase26_f16 \
  --mlx-path ./fused_model_qwen3_phase26_6bit \
  --quantize \
  --q-bits 6
```

### Run Pre-Training Checks
```python
from pathlib import Path
from punie.training.checks import run_pre_training_checks, summarize_checks

results = run_pre_training_checks(
    data_directory=Path("data/phase26_merged"),
    expected_format="messages",
    expected_patterns=(
        "result.errors", "result.error_count", "result.success",
        "result.violations", "result.violation_count", "result.fixable_count",
        "result.tests", "result.passed", "result.failed",
    ),
)

print(summarize_checks(results))
```

### Test Model
```bash
uv run python scripts/test_phase26_validation.py fused_model_qwen3_phase26_6bit
```

## Expected Outcomes

### Training Metrics
- **Initial val loss:** ~3.5-4.0 (typical for Qwen3-30B cold start)
- **Final val loss:** <1.0 (Phase 23 achieved 0.610)
- **Loss reduction:** ≥70% from initial to final
- **Final train loss:** <0.5 (indicates convergence)
- **Iterations:** 500 (proven sufficient)
- **Time:** ~2-3 hours on M2 Max 96GB

### Model Artifacts
- **Adapter:** `adapters_phase26/` (~300 MB)
- **Fused float16:** `fused_model_qwen3_phase26_f16/` (~57 GB)
- **Quantized 6-bit:** `fused_model_qwen3_phase26_6bit/` (~23 GB) **← Deploy this**

### Validation Results
- **Overall accuracy:** ≥80% (20/25 queries)
- **Field access rate:** ≥80% (vs 0% Phase 23 baseline)
- **Single-tool discrimination:** 100% (5/5, no regression)
- **Conditional logic:** 80% (4/5)
- **Field access queries:** 80% (4/5)
- **Iteration queries:** 80% (4/5)
- **Multi-step workflows:** 60% (3/5)

## Key Learnings from Prior Phases

### Phase 5c: Dequantization is Critical
**Problem:** 4-bit re-quantization during fusion destroys LoRA signal (only 16 discrete values)
**Solution:** Dequantize to float16, then re-quantize to 6/8-bit (64/256 levels preserve deltas)

### Phase 8: 6-bit is Optimal
**Finding:** 6-bit (64 levels) preserves LoRA signal with 23% size reduction vs 8-bit
**Impact:** 23 GB models instead of 30 GB, same 100% accuracy

### Phase 21: Format Must Match Server
**Problem:** Training data format mismatch with server expectations (JSON vs XML)
**Solution:** Training data format MUST match what server parses at runtime

### Phase 22-23: Infrastructure Prevents Regressions
**Innovation:** Code Mode format is cleaner than XML/JSON
**Success:** 100% tool calling accuracy, excellent loss convergence
**Gap:** No field access patterns in training data

### Phase 23 Task 11: Eval Can Mask Production Failures
**Finding:** Model can score 100% on discrimination but 0% on actual field access
**Lesson:** Need validation that tests the ACTUAL desired behavior, not just proxies

## Related Documentation

- `docs/diary/2026-02-15-phase23-task11-validation.md` — Phase 23 gap analysis (0% field access)
- `docs/diary/2026-02-15-phase25-7b-experiment-failed.md` — Why 7B experiment was inconclusive
- `MODEL_PERFORMANCE_TRACKER.md` — Performance benchmarks across phases
- `agent-os/product/roadmap.md` — Overall project roadmap and priorities
