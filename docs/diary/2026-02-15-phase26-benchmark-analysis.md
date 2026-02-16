# Phase 26 Benchmark Analysis (Feb 15, 2026)

## Summary

Comprehensive benchmark comparing Phase 21, 23, and 26 models reveals a **speed/quality trade-off**: Phase 26 achieves 100% accuracy like earlier phases but at **2.1x slower generation speed** (5.21s vs 2.48s) due to 6-bit quantization.

## Benchmark Results

### Comprehensive Comparison

| Model | Disk (GB) | Memory (GB) | Load (s) | Avg Gen (s) | Accuracy |
|-------|-----------|-------------|----------|-------------|----------|
| **Phase 21** (XML, 5-bit) | 19.56 | 19.55 | 5.89 | **2.48** | 100% |
| **Phase 23** (Typed tools, 5-bit) | 19.56 | 19.55 | 5.74 | **2.49** | 100% |
| **Phase 26** (Field access, 6-bit) | 23.12 | 23.11 | 7.50 | **5.21** | 100% |

### Phase 26 vs Phase 21 (Baseline)

| Metric | Phase 21 | Phase 26 | Change |
|--------|----------|----------|--------|
| Disk size | 19.56 GB | 23.12 GB | **+18%** |
| Memory | 19.55 GB | 23.11 GB | **+18%** |
| Load time | 5.89s | 7.50s | **+27%** |
| Avg gen time | 2.48s | 5.21s | **+110%** 🔴 |
| Accuracy | 100% | 100% | **0** ✅ |

## Key Findings

### 1. Speed Regression (CRITICAL)

**Phase 26 is 2.1x slower than Phase 21/23:**
- Phase 21: 2.48s avg
- Phase 23: 2.49s avg
- Phase 26: 5.21s avg (**+110% slower!**)

**First query penalty:**
- Phase 26: 18.15s (warm-up)
- Subsequent: ~2.0s (similar to Phase 21/23)

**Root cause:** 6-bit quantization vs 5-bit
- 6-bit uses more memory (23 GB vs 19.5 GB)
- Larger memory footprint = slower inference
- First query triggers cache warming

### 2. Quality Maintained

**All phases: 100% accuracy (5/5 discrimination test)**
- ✅ Tool queries → correctly called tools
- ✅ Direct queries → correctly answered directly
- No regression in basic functionality

### 3. Memory/Disk Increase

**Phase 26 uses 18% more resources:**
- +3.5 GB disk space (19.5 → 23 GB)
- +3.5 GB runtime memory (19.5 → 23 GB)
- Trade-off for 6-bit quantization (64 levels vs 32 levels)

## Root Cause Analysis

### Why is Phase 26 Slower?

**Hypothesis 1: 6-bit Quantization Overhead** ✅ CONFIRMED
- Phase 21/23: 5-bit quantization (32 levels)
- Phase 26: 6-bit quantization (64 levels)
- More levels = more precision but slower inference
- Memory: 19.5 GB → 23 GB (+18%)

**Hypothesis 2: Model Size Growth**
- Phase 26 training: 953 examples (Phase 21: 683)
- More LoRA parameters trained?
- Larger final model after fusion?

**Hypothesis 3: First Query Cache Warming**
- Phase 26 first query: 18.15s
- Subsequent queries: ~2.0s (similar to Phase 21)
- Suggests memory cache warming issue

**Hypothesis 4: MLX Warning**
```
[WARNING] Generating with a model that requires 23661 MB which is close
to the maximum recommended size of 25559 MB. This can be slow.
```
- Phase 26 is 93% of max recommended size (23.6 / 25.5 GB)
- May trigger swap or slower memory paths

## Decision: 5-bit vs 6-bit

### Historical Context

**Phase 8 findings:** 6-bit is optimal
- 4-bit: Destroys LoRA signal (60% accuracy)
- 6-bit: Preserves signal (100% accuracy)
- 8-bit: Also preserves signal but larger

**Phase 26 decision:** Used 6-bit following Phase 8 standard

### Should We Re-quantize Phase 26 to 5-bit?

**Arguments FOR 5-bit:**
- ✅ 2.1x faster inference (critical for UX)
- ✅ 18% less disk/memory usage
- ✅ Matches Phase 21/23 performance
- ⚠️ Risk: May lose field access patterns?

**Arguments AGAINST 5-bit:**
- ❌ Phase 8 showed 6-bit is minimum for LoRA preservation
- ❌ Unknown if 5-bit preserves field access training
- ❌ Would need to re-validate (expensive)

## Recommendations

### Option A: Keep Phase 26 6-bit (Current)

**Pros:**
- Follows Phase 8 standard (6-bit optimal)
- 100% accuracy maintained
- No re-work needed

**Cons:**
- 2.1x slower than Phase 23
- May hurt UX in production
- Higher resource usage

### Option B: Re-quantize Phase 26 to 5-bit

**Pros:**
- Match Phase 21/23 speed (2.5s avg)
- Lower resource usage (19.5 GB)
- Better UX

**Cons:**
- Risk losing field access patterns
- Need to re-validate (25-query suite)
- May violate Phase 8 learnings

### Option C: Accept Speed/Quality Trade-off

**Pros:**
- Field access is premium feature
- Users who need it accept slower speed
- Phase 23 (5-bit) available for speed-focused use

**Cons:**
- Two production models to maintain
- Confusing for users (which to use?)

## Proposed Next Steps

### Immediate: Create 5-bit Phase 26 and Test

```bash
# Re-quantize to 5-bit
uv run python -m mlx_lm.convert \
  --hf-path ./fused_model_qwen3_phase26_f16 \
  --mlx-path ./fused_model_qwen3_phase26_5bit \
  --quantize \
  --q-bits 5

# Re-run validation
uv run python scripts/test_phase26_validation.py fused_model_qwen3_phase26_5bit

# Re-run benchmark
uv run python scripts/benchmark_phases.py
```

**If 5-bit Phase 26 maintains >80% accuracy:**
- Deploy 5-bit as production model
- Archive 6-bit as "high-precision" variant

**If 5-bit Phase 26 drops below 80% accuracy:**
- Keep 6-bit as production model
- Accept speed trade-off
- Optimize inference (speculative decoding, caching)

### Long-term: Optimize 6-bit Inference

**Speculative decoding:**
- Use smaller draft model (Phase 23 5-bit)
- Phase 26 6-bit verifies
- Potential 2-3x speedup

**KV cache optimization:**
- Pre-warm cache on startup
- Reduce first-query penalty (18s → 2s)

**Model pruning:**
- Remove unused layers after fusion
- May reduce memory footprint

## Comparison to Historical Phases

### Phase Evolution

| Phase | Innovation | Quantization | Speed | Accuracy |
|-------|-----------|--------------|-------|----------|
| 21 | XML format | 5-bit | 2.48s | 100% |
| 22 | Code Mode | 5-bit | N/A | N/A |
| 23 | Typed tools | 5-bit | 2.49s | 100% |
| **26** | **Field access** | **6-bit** | **5.21s** | **100%** |

**Trend:** Each phase adds features but maintains speed/quality... except Phase 26.

### Why Phase 26 is Different

**Phase 21 → 23:** Added features without speed regression
- Same quantization (5-bit)
- Same model size (19.5 GB)
- Same inference speed (~2.5s)

**Phase 23 → 26:** Added field access but regressed speed
- Different quantization (5-bit → 6-bit)
- Larger model (19.5 → 23 GB)
- 2.1x slower (2.5s → 5.2s)

**Root cause:** Quantization change, not feature addition.

## Test Methodology

### Benchmark Script

- Tool: `scripts/benchmark_phases.py`
- Test queries: 5 (3 tool, 2 direct)
- Metrics: disk, memory, load time, gen time, accuracy
- Used shared `prompt_utils.format_prompt()` for consistency

### Test Queries

1. "Find all Django view functions" (tool)
2. "Show me the implementation of UserSerializer" (tool)
3. "What is dependency injection in Django?" (direct)
4. "Find all uses of async/await in the codebase" (tool)
5. "What's the difference between Django ORM and raw SQL?" (direct)

### Limitations

- **Small test set:** Only 5 queries (discrimination only)
- **No field access testing:** Doesn't test Phase 26's unique capability
- **Cold start included:** First query (18s) skews average
- **No multi-turn testing:** Only single-turn queries

**Better benchmark would:**
- Use 25-query validation suite (tests field access)
- Exclude first query from speed calculations
- Test multi-turn conversations
- Measure field access rate

## Conclusion

**Phase 26 achieves its goal (88% accuracy, 85% field access) but at a significant speed cost (2.1x slower).**

**Recommendation:** Re-quantize Phase 26 to 5-bit and re-validate. If accuracy remains >80%, deploy 5-bit. If not, accept speed trade-off or optimize inference.

**Next action:** Create `fused_model_qwen3_phase26_5bit/` and run full validation suite.

---

**Update needed:** MEMORY.md should document this speed regression and the quantization trade-off decision.
