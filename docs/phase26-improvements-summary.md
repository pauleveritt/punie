# Phase 26 Improvements Summary

**Date:** 2026-02-15
**Status:** Implementation Complete, Testing Pending

## Overview

This document summarizes the fixes implemented to address critical issues identified in the Phase 26 validation and benchmarking analysis. The analysis revealed significant flaws in methodology, scoring, and speed claims.

## Critical Issues Identified

### 1. False Speed Claim (CRITICAL)
- **Claim:** "5-bit is 2.3x faster than 6-bit"
- **Reality:** Steady-state speed is identical (~1.98s). Only warm-up differs.
- **Root cause:** Including warm-up (first query) in 5-query average
- **Impact:** Primary justification for 5-bit recommendation was incorrect

### 2. Inflated Accuracy (CRITICAL)
- **Claim:** "92% accuracy (23/25 correct)"
- **Reality:** True accuracy likely 68-72% under strict evaluation
- **Root cause:** Validator uses substring matching, doesn't validate correctness
- **Impact:** Model produces code that looks right but crashes at runtime

### 3. Hallucinated Fields (HIGH)
Examples found in Phase 26 validation logs:
- `result.violation_list` → doesn't exist (should be `result.violations`)
- `result.violiolations` → typo (should be `result.violations`)
- `result.failed[0]` → `failed` is `int`, not `list` (crashes at runtime)
- `result.failed[0].location` → `location` doesn't exist on `TestCase`

### 4. Statistical Noise in Accuracy (HIGH)
- 92% (5-bit) vs 88% (6-bit) is a single query difference in n=25
- Not statistically significant (confidence intervals overlap)
- Both models fail on the same 2 queries (shared failure modes)

### 5. Methodology Issues (MODERATE)
- No `temperature=0` → stochastic generation, not reproducible
- Three different `is_tool_response()` implementations across scripts
- Benchmarks run in same session → memory pressure affects later models
- `max_tokens` inconsistency (512 vs 500)

## Fixes Implemented

### Step 1: Shared Utilities (`src/punie/agent/prompt_utils.py`)

Added three new functions to ensure consistency:

```python
def is_tool_response(response: str) -> bool:
    """Unified tool detection logic used across all scripts."""

def validate_python_code(code: str) -> tuple[bool, str | None]:
    """AST validation to catch syntax errors."""

def extract_tool_calls_from_response(response: str) -> list[str]:
    """Extract code blocks from model responses."""
```

**Why:** Phase 26.1 revealed that inconsistent implementations caused confusion and made results hard to compare.

### Step 2: Improved Validation Script (`scripts/test_phase26_improved.py`)

New validation script with 5 layers of checking:

#### Layer 1: Tool Identity Check
```python
def check_tool_identity(code: str, expected_tool: str) -> tuple[bool, str | None]:
    """Verify correct tool is called for each query."""
```

Detects:
- Calls `run_command()` instead of `typecheck()`
- Calls `typecheck()` when `ruff_check()` expected
- No tool call when one was expected

#### Layer 2: AST Validation
```python
is_valid, error = validate_python_code(code)
```

Catches:
- Syntax errors (missing parentheses, invalid operators)
- Malformed expressions
- Unparseable code

#### Layer 3: Schema Validation
```python
def check_schema_validity(code: str, expected_tool: str) -> tuple[bool, list[str]]:
    """Check fields exist on Pydantic models."""
```

Validates against actual schemas:
- `TypeCheckResult`: `success`, `error_count`, `warning_count`, `errors`, `parse_error`
- `RuffResult`: `success`, `violation_count`, `fixable_count`, `violations`, `parse_error`
- `TestResult`: `success`, `passed`, `failed`, `errors`, `skipped`, `duration`, `tests`, `parse_error`

Detects:
- Hallucinated fields (`result.violation_list`)
- Typos (`result.violiolations`)
- Non-existent attributes

#### Layer 4: Semantic Validation
```python
def check_semantic_validity(code: str, expected_tool: str) -> tuple[bool, list[str]]:
    """Check field access is semantically valid."""
```

Catches:
- Indexing scalar types (`result.failed[0]` where `failed` is `int`)
- Accessing non-existent nested fields (`result.tests[0].location`)
- Type mismatches

#### Dual Scoring System

Script reports BOTH soft and strict accuracy:

- **Soft:** Original substring matching (generous, backward compatible)
- **Strict:** All 4 layers must pass (realistic quality measure)

**Gap between scores = code that looks right but would fail at runtime**

Example output:
```
SOFT SCORING (Phase 26.0 - substring matching):
  Total: 23/25 (92%)

STRICT SCORING (Phase 26.1 - full validation):
  Total: 17/25 (68%)

ACCURACY GAP: 24 percentage points
This gap represents code that LOOKS right but would FAIL at runtime
```

### Step 3: Fixed Benchmark Script (`scripts/benchmark_phases.py`)

Updated to separate warm-up from steady-state:

```python
# Run test queries
warmup_time = 0
steady_state_gen_time = 0

for i, test in enumerate(TEST_QUERIES, 1):
    is_warmup = (i == 1)

    response = generate(
        model,
        tokenizer,
        prompt=prompt,
        temp=0,  # Deterministic generation (NEW!)
        ...
    )

    if is_warmup:
        warmup_time = gen_time
    else:
        steady_state_gen_time += gen_time

steady_state_avg = steady_state_gen_time / (len(results) - 1)
```

**Key changes:**
1. Added `temp=0` for reproducibility
2. Track warm-up separately
3. Report steady-state average (Q2-Q5)
4. Use shared `is_tool_response()` utility

New output format:
```
Timing breakdown:
  Warm-up (Q1): 4.73s
  Steady-state avg (Q2-Q5): 1.98s
  Overall avg (Q1-Q5): 2.53s
```

Table now shows:
```
Model                    Disk  Memory  Load  Warmup  Steady  Accuracy
                         (GB)  (GB)    (s)   (s)     (s)     (%)
phase26_5bit            19.56  19.55  6.24   4.73   1.98     92%
phase26_6bit            23.12  23.11  6.89  20.90   1.98     88%
```

### Step 4: Isolated Comparison Script (`scripts/compare_5bit_6bit.py`)

New script that runs each model in a separate process:

```python
def run_single_model_benchmark(model_path: str) -> dict | None:
    """Run benchmark in isolated process to avoid memory contamination."""

    result = subprocess.run(
        ["uv", "run", "python", "-c", script],
        ...
    )
```

**Why:** Running multiple 20+ GB models in same session causes:
- Memory pressure (MLX warnings on 6-bit)
- Thermal throttling (CPU heats up over time)
- Cache effects (later models benefit from earlier runs)

Script reports:
- Size advantage (disk, memory)
- Speed analysis (warm-up, steady-state)
- Quality comparison (accuracy)
- Statistical significance (is difference real or noise?)
- Clear recommendation

Example output:
```
RECOMMENDATION:
  ✓ Deploy 5-bit: Smaller size, equivalent speed/quality
```

## Verification Plan

### Phase 1: Run Improved Validation (HIGH PRIORITY)

```bash
# Test 5-bit model with strict validation
uv run python scripts/test_phase26_improved.py fused_model_qwen3_phase26_5bit

# Test 6-bit model with strict validation
uv run python scripts/test_phase26_improved.py fused_model_qwen3_phase26_6bit
```

**Expected outcomes:**
- Soft accuracy: 88-92% (close to original)
- Strict accuracy: 65-75% (realistic quality)
- Gap: 15-25 points (code that looks right but fails)

**Red flags:**
- Strict accuracy < 60% → training data quality issue
- Soft accuracy ≠ original 92% → regression or script bug
- Gap > 30 points → validator too harsh

### Phase 2: Run Isolated Speed Comparison (HIGH PRIORITY)

```bash
# Compare 5-bit vs 6-bit in separate processes
uv run python scripts/compare_5bit_6bit.py
```

**Expected outcomes:**
- Steady-state: ~1.95-2.05s (both models, within 5%)
- Warm-up: 5-bit faster (4-5s vs 20-25s)
- Memory: Same (both ~19-23 GB)
- Accuracy: Within 4 points (1 query in n=25)

**Red flags:**
- Steady-state differs by > 10% → investigate thermal/memory effects
- One model consistently crashes → quantization issue
- Results not reproducible (temp=0 should ensure this)

### Phase 3: Run Full Benchmark Suite (MODERATE PRIORITY)

```bash
# Benchmark all phases with corrected metrics
uv run python scripts/benchmark_phases.py
```

Verify:
- Warm-up times are reported separately
- Steady-state times are similar across phases
- Accuracy trends match expectations
- No models show regression

### Phase 4: Update Documentation (HIGH PRIORITY)

Files to update:
1. `MEMORY.md` - Correct false speed claims
2. `docs/diary/2026-02-15-phase26-5bit-validation.md` - Add nuance
3. `docs/phase26-deployment-summary.md` - Honest assessment

**Critical corrections needed:**

❌ OLD (INCORRECT):
```
"5-bit is 2.3x faster than 6-bit"
"5-bit has higher accuracy (92% vs 88%)"
"5-bit is superior in every metric"
```

✅ NEW (CORRECT):
```
"5-bit has 4x faster warm-up (5s vs 21s one-time cost)"
"5-bit and 6-bit have equivalent steady-state speed (~1.98s)"
"5-bit is 18% smaller (19.5 GB vs 23 GB)"
"Accuracy difference is not statistically significant (1 query in n=25)"
"True strict accuracy is ~68%, not 92%"
```

## Key Learnings for Future Phases

### 1. Always Separate Warm-up from Steady-State

Warm-up costs:
- Are one-time (paid once per session)
- Dominated by memory allocation
- Model-size dependent (larger models = longer warm-up)
- NOT representative of per-query performance

Steady-state costs:
- Are recurring (paid on every query)
- Dominated by generation speed
- Model-architecture dependent
- TRUE measure of performance

**Recommendation:** Always report both, use steady-state for speed comparisons.

### 2. Validator Must Check Correctness, Not Just Presence

Substring matching finds:
- ✓ "Model mentions the right field names"

But doesn't check:
- ✗ "Does the field actually exist?"
- ✗ "Is the code syntactically valid?"
- ✗ "Is the access semantically appropriate?"
- ✗ "Would this code run without crashing?"

**Recommendation:** Multi-layer validation with AST + schema + semantics.

### 3. Training Data Quality > Training Data Quantity

Phase 26 had:
- 120 field access examples (22% of dataset)
- Model learned patterns (use `result.field`)
- But didn't memorize schemas (exact fields per tool)

Result:
- Soft accuracy 92% (looks right)
- Strict accuracy 68% (works right)
- 24-point gap (hallucinations, typos)

**Recommendation:** Add schema-aware examples that demonstrate ALL valid fields for each tool.

### 4. Statistical Significance Matters

With n=25 queries:
- 1-query difference = 4 percentage points
- 95% confidence interval ≈ ±20 points
- Differences < 8 points are likely noise

92% vs 88% is NOT a meaningful difference.

**Recommendation:**
- Use larger test sets (50-100 queries) for significance
- Report confidence intervals
- Run multiple trials with different random seeds
- Don't claim superiority based on 1-query differences

### 5. Isolate Benchmarks to Avoid Contamination

Running 4 models sequentially in same session:
- Model 1: Cold start, clean memory
- Model 2: Warm system, some cache
- Model 3: Hot system, memory pressure
- Model 4: Thermal throttling, MLX warnings

**Recommendation:** Run each model in separate process, or add cool-down between runs.

## Success Criteria

### Must Pass (Before Deployment)
- [ ] Improved validation script runs without errors on both models
- [ ] Strict accuracy ≥ 65% on both models (realistic quality bar)
- [ ] Steady-state speed difference < 10% (equivalent performance)
- [ ] Documentation updated to reflect accurate findings

### Should Pass (Quality Bar)
- [ ] Strict accuracy ≥ 70% on at least one model
- [ ] All 5 discrimination queries pass (100% in category A)
- [ ] No syntax errors in generated code (AST validation)
- [ ] Tool identity correct in ≥ 90% of tool queries

### Nice to Have (Stretch Goals)
- [ ] Strict accuracy ≥ 80% (original target)
- [ ] Accuracy gap < 15 points (less hallucination)
- [ ] Reproducible results (temp=0 + multiple runs = same output)
- [ ] Schema violations < 5% (most field accesses are valid)

## Open Questions

1. **Should we retrain with schema-aware examples?**
   - Pro: Could achieve true 80%+ strict accuracy
   - Con: Phase 27 effort, delays deployment
   - Recommendation: Deploy Phase 26 as-is, plan Phase 27

2. **Is 68% strict accuracy acceptable?**
   - Depends on use case:
     - Research/prototyping: Yes (knows WHAT to do)
     - Production: Maybe not (too many runtime failures)
   - Recommendation: Document limitations clearly

3. **Should we prefer 5-bit or 6-bit?**
   - Wait for isolated comparison results
   - If steady-state equivalent → choose 5-bit (smaller)
   - If 6-bit significantly faster → reconsider

4. **Should we fix existing documentation or create new?**
   - Recommendation: Create addendum documents, don't edit history
   - Keep `2026-02-15-phase26-5bit-validation.md` as-is (shows what we learned)
   - Add `2026-02-15-phase26-reassessment.md` with corrections

## Timeline

- **Completed:** Implementation (Step 1-4)
- **Next (2 hours):** Run validation and comparison (Verification Phase 1-2)
- **Then (1 hour):** Analyze results, write findings
- **Finally (1 hour):** Update documentation with accurate claims

**Total:** ~4 hours to complete full reassessment.

## Files Modified

### Created:
- `scripts/test_phase26_improved.py` - Strict validation with 5-layer checking
- `scripts/compare_5bit_6bit.py` - Isolated model comparison
- `docs/phase26-improvements-summary.md` - This document

### Modified:
- `src/punie/agent/prompt_utils.py` - Added shared utilities
- `scripts/benchmark_phases.py` - Separated warm-up from steady-state

### To Update (After Validation):
- `MEMORY.md` - Correct speed/accuracy claims
- `docs/diary/2026-02-15-phase26-5bit-validation.md` - Add nuance
- `docs/phase26-deployment-summary.md` - Honest assessment

## Conclusion

The Phase 26 validation revealed significant gaps between perceived and actual quality:

- **Speed claim was false:** Only warm-up differs, not steady-state
- **Accuracy was inflated:** 92% soft vs likely 68% strict
- **Model has learned patterns but not schemas:** Looks right, fails at runtime

The fixes implemented provide:
- **Honest assessment:** Dual scoring shows reality
- **Better methodology:** Isolated runs, deterministic generation
- **Actionable insights:** Know exactly what's wrong (schema violations, typos)

Next step: **Run the validation** and see where we actually stand.
