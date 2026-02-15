# Phase 26 Fixes: Ready for Testing

**Date:** 2026-02-15
**Status:** ✅ Implementation Complete, Ready for Verification

## What Was Fixed

The deep analysis of Phase 26 identified **5 critical issues** with validation and benchmarking:

### Issue 1: False Speed Claim ❌ → FIXED ✅
- **Problem:** "5-bit is 2.3x faster" claim came from including 20s warm-up in 5-query average
- **Reality:** Steady-state speed is identical (~1.98s)
- **Fix:** `benchmark_phases.py` now separates warm-up (Q1) from steady-state (Q2-Q5)

### Issue 2: Inflated Accuracy ❌ → FIXED ✅
- **Problem:** 92% accuracy from substring matching, doesn't validate correctness
- **Reality:** True accuracy likely 68-72% (code looks right but crashes at runtime)
- **Fix:** `test_phase26_improved.py` with 5-layer validation (tool identity, AST, schema, semantics)

### Issue 3: Hallucinated Fields ❌ → FIXED ✅
- **Problem:** Model produces `result.violation_list` (doesn't exist), `result.violiolations` (typo)
- **Fix:** Schema validation checks against actual Pydantic models

### Issue 4: Statistical Noise ❌ → FIXED ✅
- **Problem:** 92% vs 88% is 1 query in n=25, not significant
- **Fix:** Comparison script reports statistical significance

### Issue 5: Methodology Flaws ❌ → FIXED ✅
- **Problem:** No `temperature=0`, inconsistent tool detection, memory contamination
- **Fix:** Shared utilities, deterministic generation, isolated runs

## Files Created

### 1. Shared Utilities (`src/punie/agent/prompt_utils.py`)
Added 3 new functions:
- `is_tool_response()` - Unified tool detection
- `validate_python_code()` - AST syntax validation
- `extract_tool_calls_from_response()` - Code block extraction

**Status:** ✅ Tested, all 3 functions working

### 2. Improved Validation (`scripts/test_phase26_improved.py`)
5-layer validation:
1. Tool identity (correct tool for query)
2. AST validation (syntax errors)
3. Schema validation (fields exist on models)
4. Semantic validation (appropriate access)
5. Dual scoring (soft vs strict)

**Status:** ✅ Syntax verified, ready to run

### 3. Fixed Benchmark (`scripts/benchmark_phases.py`)
Updates:
- Separates warm-up from steady-state
- Adds `temperature=0` for reproducibility
- Uses shared `is_tool_response()` utility
- Reports timing breakdown

**Status:** ✅ Updated, ready to run

### 4. Isolated Comparison (`scripts/compare_5bit_6bit.py`)
Runs each model in separate process to avoid:
- Memory pressure (MLX warnings)
- Thermal effects (CPU heating)
- Cache contamination

**Status:** ✅ Created, ready to run

### 5. Documentation (`docs/phase26-improvements-summary.md`)
Comprehensive summary of:
- Issues identified
- Fixes implemented
- Verification plan
- Success criteria

**Status:** ✅ Complete

## How to Run Verification

### Step 1: Test Improved Validation (10 min per model)

```bash
# Test 5-bit model with strict validation
uv run python scripts/test_phase26_improved.py fused_model_qwen3_phase26_5bit

# Test 6-bit model with strict validation
uv run python scripts/test_phase26_improved.py fused_model_qwen3_phase26_6bit
```

**What to look for:**
```
SOFT SCORING (Phase 26.0 - substring matching):
  Total: 23/25 (92%)           ← Should match original

STRICT SCORING (Phase 26.1 - full validation):
  Total: 17/25 (68%)           ← Realistic quality

ACCURACY GAP: 24 percentage points
This gap represents code that LOOKS right but would FAIL at runtime
```

**Success criteria:**
- Soft accuracy 88-92% (close to original)
- Strict accuracy 65-75% (realistic)
- Gap 15-25 points (code quality issues)

### Step 2: Run Isolated Speed Comparison (5 min)

```bash
# Compare 5-bit vs 6-bit in separate processes
uv run python scripts/compare_5bit_6bit.py
```

**What to look for:**
```
Steady-state avg (s)      1.98       1.98       +0.0% ≈ EQUIVALENT
```

**Success criteria:**
- Steady-state difference < 5% (equivalent speed)
- 5-bit has faster warm-up (4-5s vs 20-25s)
- 5-bit is ~18% smaller (19.5 GB vs 23 GB)

### Step 3: Run Full Benchmark Suite (15 min)

```bash
# Benchmark all phases with corrected metrics
uv run python scripts/benchmark_phases.py
```

**What to look for:**
- Warm-up and steady-state reported separately
- Steady-state times similar across phases
- No unexpected regressions

## Expected Outcomes

### Likely Results

**5-bit model:**
- Soft accuracy: ~92% (substring matching, generous)
- Strict accuracy: ~68% (full validation, realistic)
- Steady-state speed: ~1.98s
- Warm-up: ~4.7s

**6-bit model:**
- Soft accuracy: ~88% (1 query difference = noise)
- Strict accuracy: ~68% (same quality)
- Steady-state speed: ~1.98s (equivalent!)
- Warm-up: ~20.9s (slower due to size)

**Recommendation:** Deploy 5-bit
- Reason: 18% smaller, 4x faster warm-up, equivalent speed/quality

### If Results Differ Significantly

**Strict accuracy < 60%:**
- Training data quality issue
- Model needs more schema-aware examples
- Consider Phase 27 retraining

**Steady-state differs by > 10%:**
- Investigate thermal/memory effects
- Run comparison multiple times
- Check for system load

**Soft ≠ original 92%:**
- Possible regression in model
- Or script bug - check logs

## Next Steps After Verification

### If Results Confirm Analysis

1. **Update MEMORY.md**
   - Remove "2.3x faster" claim
   - Add "4x faster warm-up, equivalent steady-state"
   - Note strict accuracy is ~68%, not 92%

2. **Create reassessment document**
   - `docs/diary/2026-02-15-phase26-reassessment.md`
   - Honest findings
   - Lessons learned

3. **Decide on deployment**
   - 5-bit recommended (smaller, same quality)
   - Document limitations (68% strict accuracy)

4. **Plan Phase 27** (optional)
   - Schema-aware training examples
   - Target: 80%+ strict accuracy
   - Focus on correct field access

### If Results Show Unexpected Issues

1. **Debug the script**
   - Check logs in `logs/phase26_improved_*.json`
   - Verify AST/schema validators work correctly

2. **Investigate model behavior**
   - Run individual failing queries
   - Check for patterns in failures

3. **Revise success criteria**
   - Maybe 68% is actually good for this task?
   - Or maybe we need different validation approach?

## Key Learnings

### Validator Design
- **Substring matching finds patterns, not correctness**
- Need multi-layer validation (AST + schema + semantics)
- Gap between soft and strict = hidden quality issues

### Benchmark Design
- **Always separate warm-up from steady-state**
- Warm-up = one-time cost (model size dependent)
- Steady-state = per-query cost (architecture dependent)

### Statistical Significance
- **1 query in n=25 = 4 percentage points of noise**
- Need larger test sets (50-100) for confidence
- Report confidence intervals, not point estimates

### Model Quality
- **Model learned patterns (use `result.field`)**
- But didn't memorize schemas (exact fields per tool)
- Training data needs more schema coverage

## Questions?

- How to interpret strict accuracy results?
- Should we retrain for better schema adherence?
- Is 68% acceptable for production use?
- Should we deploy 5-bit or 6-bit?

All will be answered by running the verification tests!

---

**Ready to run?** Start with Step 1 above. Each script prints clear output and saves JSON logs for later analysis.
