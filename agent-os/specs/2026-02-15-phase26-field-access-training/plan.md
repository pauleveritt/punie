# Phase 26: Train Structured Field Access Patterns - Plan

## Context

Phase 23 Task 11 revealed a critical gap: the model calls typed tools (`typecheck()`, `ruff_check()`, `pytest_run()`) correctly but **never accesses structured fields** on the results. 0% field access rate. The model treats `TypeCheckResult`, `RuffResult`, and `TestResult` as opaque objects.

**Root cause:** Only ~4.5% of training examples show field access. The Phase 24 ruff/pytest examples (which do have some field access) were merged but **never trained** — the production model was trained on Phase 23 data only.

## Goal

Add 120 focused field-access training examples, unify formats, retrain, and achieve **80%+ field access rate**.

## Success Criteria

- All `run_pre_training_checks()` pass (including coverage check for field access patterns)
- 80%+ overall accuracy on 25-query validation suite
- 80%+ structured field access rate (vs 0% in Phase 23 baseline)
- 100% single-tool discrimination (no regression)
- Training converges (val loss < 1.0)

## Key Design Decisions

1. **Format:** Use Format A (XML-wrapped `<tool_call><function=execute_code><parameter=code>`) consistently across all data
2. **Infrastructure:** Use `punie.training` module (`TrainingDataset`, `TrainingExample`, `ChatMessage`) for data generation and validation
3. **Validation:** Use new checks infrastructure (`run_pre_training_checks()` with `check_training_data_coverage()`) to verify field access patterns before training
4. **Training approach:** Train from scratch on all merged data (~977 examples)
5. **Quantization:** Use 6-bit (proven optimal in Phase 8)

## Implementation Tasks

### Task 1: Spec Documentation ✓
Create `agent-os/specs/2026-02-15-phase26-field-access-training/` with plan.md, shape.md, standards.md, references.md

### Task 2: Generate Field Access Examples
Create `scripts/generate_field_access_examples.py` to generate 120 training examples:
- **4 patterns × 3 tools × 10 examples = 120 total**
- Pattern 1: Conditional logic (if result.error_count > 0:)
- Pattern 2: Field access + formatting (print(f"Errors: {result.error_count}"))
- Pattern 3: Iteration (for error in result.errors:)
- Pattern 4: Multi-step workflows (check → access field → use in next tool call)
- Tools: typecheck(), ruff_check(), pytest_run()
- Output: `data/phase26_field_access/field_access_examples.jsonl`

### Task 3: Convert Phase 24 Format
Create `scripts/convert_phase24_format.py` to convert 100 ruff/pytest examples from Format B (bare `<tool_call>`) to Format A (XML-wrapped with system message)
- Source: `data/ruff_training/`, `data/pytest_training/`
- Output: `data/phase24_format_a/`

### Task 4: Merge Training Data
Create `scripts/merge_phase26_data.py` to merge all sources:
1. Phase 22 base (707 examples from `data/phase22_code_format/`)
2. Phase 23 ty (50 examples from `data/ty_training/`)
3. Converted Phase 24 (100 examples from `data/phase24_format_a/`)
4. Phase 26 field access (120 examples from `data/phase26_field_access/`)
- Convert all to **messages format** (not text format)
- Shuffle with seed 42
- Split 80/10/10
- Total: ~977 examples
- Output: `data/phase26_merged/`

### Task 5: Run Validation Checks
Run `run_pre_training_checks()` on merged data with expected field access patterns:
```python
expected_patterns = (
    "result.errors", "result.error_count", "result.success",
    "result.violations", "result.violation_count",
    "result.tests", "result.passed", "result.failed",
    ".fixable_count", ".warning_count",
)
```
Also run `check_eval_parser_matches_training_format()` on sample assistant content.

### Task 6: Create Training Pipeline Scripts
- `scripts/train_phase26.sh` — 500 iters, batch 1, lr 1e-4, 8 layers
- `scripts/fuse_phase26.sh` — Dequantize to float16
- `scripts/quantize_phase26.sh` — 6-bit quantization
- `scripts/run_phase26.sh` — Full pipeline with checks at each stage

### Task 7: Run Training
Execute full pipeline (~2-3 hours wall clock)

### Task 8: Create Validation Suite
Create `scripts/test_phase26_validation.py` with 25-query suite:
- Category A: Single-tool discrimination (5 queries, 100% target)
- Category B: Conditional logic (5 queries, 80% target)
- Category C: Field access (5 queries, 80% target)
- Category D: Iteration (5 queries, 80% target)
- Category E: Multi-step workflows (5 queries, 60% target)

### Task 9: Run Validation and Document
- Run 25-query suite
- Compare with Phase 23 baseline (0% field access)
- Create diary entry
- Update MEMORY.md

## Task Dependencies

```
Task 1 (spec docs)           — independent
Task 2 (generate examples)   — independent
Task 3 (convert Phase 24)    — independent
Task 4 (merge data)          — depends on Tasks 2, 3
Task 5 (run checks)          — depends on Task 4
Task 6 (pipeline scripts)    — independent
Task 7 (run training)        — depends on Tasks 5, 6
Task 8 (validation script)   — independent
Task 9 (run validation)      — depends on Tasks 7, 8
```

## Risk Mitigation

- **Signal too weak:** If <60% field access after training, increase to 200 examples or upsample 2x
- **Direct answer regression:** Monitor Category A — if <80%, add more direct-answer examples
- **Training convergence:** If val loss plateaus above 1.0, try 750 iters or adjust learning rate

## Timeline Estimate

- Tasks 1-6: 2-3 hours (parallel work)
- Task 7: 2-3 hours (training pipeline)
- Tasks 8-9: 1 hour (validation)
- **Total: 5-7 hours**
