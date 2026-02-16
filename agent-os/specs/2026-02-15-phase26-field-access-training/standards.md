# Phase 26: Train Structured Field Access Patterns - Standards

## Code Standards

### Use punie.training Infrastructure

All data generation MUST use the validated infrastructure:

```python
from punie.training.dataset import TrainingDataset, TrainingExample, ChatMessage
from punie.training.dataset_io import write_training_dataset
from punie.training.checks import run_pre_training_checks
```

**Rationale:** Ensures structural consistency and enables automated validation

### Format A Compliance

All training examples MUST follow Format A:

**Required structure:**
1. Messages format (list of dicts with role/content)
2. System message as first message
3. XML wrapper: `<tool_call><function=execute_code><parameter=code>`
4. Clean Python code (no `<|im_start|>` tokens)

**Example:**
```python
TrainingExample(
    messages=(
        ChatMessage(
            role="system",
            content="You are Punie, an AI coding assistant that helps with Python development via PyCharm."
        ),
        ChatMessage(
            role="user",
            content="Check types in src/"
        ),
        ChatMessage(
            role="assistant",
            content="<tool_call><function=execute_code><parameter=code>\nresult = typecheck(\"src/\")\nif result.error_count > 0:\n    print(f\"Found {result.error_count} errors\")\n</parameter></function></tool_call>"
        ),
    )
)
```

### Field Access Pattern Standards

Every field access example MUST:

1. **Call the tool first:** `result = tool_function(...)`
2. **Access at least one field:** `result.error_count`, `result.violations[0].code`, etc.
3. **Use natural Python:** Idiomatic loops, conditionals, string formatting
4. **Be realistic:** Mirror actual coding assistant queries

**Bad (Phase 23 pattern):**
```python
result = typecheck("src/")
print(result)  # Treats result as opaque
```

**Good (Phase 26 pattern):**
```python
result = typecheck("src/")
if result.error_count > 0:  # Accesses structured field
    print(f"Found {result.error_count} errors")
```

### System Prompt Consistency

All examples MUST use the exact same system prompt:

```
You are Punie, an AI coding assistant that helps with Python development via PyCharm.
```

**Rationale:** `check_system_prompt_consistency()` will fail if variants exist

### Validation Requirements

Before training, ALL checks must pass:

**Pre-training checks:**
```python
results = run_pre_training_checks(
    data_directory=Path("data/phase26_merged"),
    expected_format="messages",
    expected_patterns=(
        "result.errors", "result.error_count", "result.success",
        "result.violations", "result.violation_count", "result.fixable_count",
        "result.tests", "result.passed", "result.failed",
    ),
)
```

**Parser compatibility check:**
```python
# Sample assistant content from training data
check_eval_parser_matches_training_format(sample_content)
```

**Pass criteria:** All checks return `passed=True`, no critical warnings

## Script Standards

### Generation Scripts

File: `scripts/generate_field_access_examples.py`

**Requirements:**
1. Use `TrainingExample` and `ChatMessage` dataclasses
2. Generate exactly 120 examples (4 patterns × 3 tools × 10)
3. Vary user queries (no repetition)
4. Cover all fields from all 3 Pydantic models
5. Output to `data/phase26_field_access/field_access_examples.jsonl`
6. Include docstring explaining each pattern category

### Conversion Scripts

File: `scripts/convert_phase24_format.py`

**Requirements:**
1. Read from `data/ruff_training/` and `data/pytest_training/`
2. Convert Format B → Format A (add system message + XML wrapper)
3. Preserve original Python code exactly
4. Output to `data/phase24_format_a/`
5. Validate output with `check_format_consistency()`

### Merge Scripts

File: `scripts/merge_phase26_data.py`

**Requirements:**
1. Convert text format → messages format for Phase 22/23 data
2. Use `TrainingDataset` for structured output
3. Shuffle with `random.seed(42)` for reproducibility
4. Split 80/10/10 (train/valid/test)
5. Output to `data/phase26_merged/`
6. Print summary statistics

### Pipeline Scripts

**Training:** `scripts/train_phase26.sh`
```bash
mlx_lm.lora \
  --model mlx-community/Qwen3-30B-A3B-Instruct-4bit \
  --data data/phase26_merged \
  --train \
  --iters 500 \
  --batch-size 1 \
  --learning-rate 1e-4 \
  --lora-layers 8 \
  --adapter-path ./adapters_phase26
```

**Fusion:** `scripts/fuse_phase26.sh`
```bash
mlx_lm.fuse \
  --model mlx-community/Qwen3-30B-A3B-Instruct-4bit \
  --adapter-path ./adapters_phase26 \
  --save-path ./fused_model_qwen3_phase26_f16 \
  --dequantize
```

**Quantization:** `scripts/quantize_phase26.sh`
```bash
mlx_lm.convert \
  --hf-path ./fused_model_qwen3_phase26_f16 \
  --mlx-path ./fused_model_qwen3_phase26_6bit \
  --quantize \
  --q-bits 6
```

**Full pipeline:** `scripts/run_phase26.sh`
- Run pre-training checks (fail fast if data issues)
- Run training → check loss convergence
- Run fusion → check eos_token_id
- Run quantization → check 6-bit config
- Print summary at each stage

## Testing Standards

### Validation Suite

File: `scripts/test_phase26_validation.py`

**Requirements:**
1. 25 queries across 5 categories (5 each)
2. Automated scoring with clear pass/fail criteria
3. Compare with Phase 23 baseline (0% field access)
4. Output JSON results for analysis
5. Print human-readable summary

**Query categories:**
- **A. Single-tool discrimination:** "What is DI?" → direct answer (no field access)
- **B. Conditional logic:** "Check types and report if errors found" → if result.error_count > 0:
- **C. Field access:** "How many violations in src/?" → result.violation_count
- **D. Iteration:** "List all type errors" → for error in result.errors:
- **E. Multi-step:** "Fix first type error" → check → access → read_file

**Scoring:**
- A: 100% required (5/5) — no regression on discrimination
- B-D: 80% target (4/5 each) — core field access patterns
- E: 60% target (3/5) — complex multi-step is harder
- Overall: 80% target (20/25)
- **Critical:** Field access rate ≥80% across B-E (vs 0% baseline)

## Documentation Standards

### Diary Entry

Create: `docs/diary/2026-02-15-phase26-validation.md`

**Required sections:**
1. **Goal:** Train field access patterns
2. **Approach:** 120 new examples + format unification
3. **Training results:** Loss curves, convergence
4. **Validation results:** 25-query suite breakdown
5. **Comparison:** vs Phase 23 baseline (0% field access)
6. **Analysis:** What worked, what didn't
7. **Next steps:** Recommendations for Phase 27

### Memory Update

Update: `~/.claude/projects/.../memory/MEMORY.md`

**Required information:**
- Phase 26 completion date
- Training data composition (977 examples)
- Key results (overall accuracy, field access rate)
- Model location (`fused_model_qwen3_phase26_6bit/`)
- Critical learnings (what fixed the 0% field access issue)
- Production recommendation (use this model or continue with Phase 23?)

## Quality Gates

**Before Training:**
- ✅ All `run_pre_training_checks()` pass
- ✅ Field access patterns present in data
- ✅ Parser can handle training format
- ✅ Data split is 80/10/10

**After Training:**
- ✅ Final val loss < 1.0
- ✅ Adapter files present and valid
- ✅ No NaN/Inf in loss curve

**After Fusion:**
- ✅ Config has correct `eos_token_id`
- ✅ Model files present (config.json, weights)

**After Quantization:**
- ✅ Config shows 6-bit quantization
- ✅ Model size ~23 GB (expected for 6-bit 30B)

**After Validation:**
- ✅ Overall accuracy ≥80% (20/25)
- ✅ Field access rate ≥80%
- ✅ Single-tool discrimination 100% (5/5)
- ✅ No regressions from Phase 23

**If any gate fails:** Stop, analyze, fix before proceeding
