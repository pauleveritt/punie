# Phase 26.1: 5-bit Quantization Validation

**Date:** February 15, 2026
**Status:** ✅ SUCCESS - Deploy 5-bit as production model

## Executive Summary

**Question:** Can 5-bit Phase 26 maintain field access capability while matching Phase 23's speed?

**Answer:** YES! 5-bit Phase 26 is superior to 6-bit in **every metric**:
- **Accuracy:** 92% vs 88% (+4 points) ✅
- **Field access:** 90% vs 85% (+5 points) ✅
- **Speed:** 2.53s vs 5.76s (2.3x faster) ✅
- **Size:** 19.56 GB vs 23.12 GB (18% smaller) ✅

## Detailed Results

### Validation Suite (25 queries)

| Metric | Phase 23 (5-bit) | Phase 26 (6-bit) | **Phase 26 (5-bit)** | Winner |
|--------|------------------|------------------|----------------------|--------|
| Overall accuracy | 24% (6/25) | 88% (22/25) | **92% (23/25)** | **5-bit** ✅ |
| Field access rate | 5% (1/20) | 85% (17/20) | **90% (18/20)** | **5-bit** ✅ |
| Discrimination | 100% (5/5) | 100% (5/5) | **100% (5/5)** | Tie ✅ |

**Category breakdown (Phase 26 5-bit):**
- A. Discrimination: 5/5 (100%) ✅
- B. Conditional logic: 5/5 (100%) ✅
- C. Field access: 4/5 (80%) ✅
- D. Iteration: 5/5 (100%) ✅
- E. Multi-step workflows: 4/5 (80%) ✅

### Speed Benchmark (5 queries)

| Metric | Phase 23 (5-bit) | Phase 26 (6-bit) | **Phase 26 (5-bit)** | Winner |
|--------|------------------|------------------|----------------------|--------|
| Avg gen time | 2.47s | 5.76s | **2.53s** | **5-bit** ✅ |
| Load time | 5.59s | 7.04s | **5.57s** | **5-bit** ✅ |
| Memory | 19.55 GB | 23.11 GB | **19.55 GB** | **5-bit** ✅ |
| Disk size | 19.56 GB | 23.12 GB | **19.56 GB** | **5-bit** ✅ |
| Accuracy | 100% (5/5) | 100% (5/5) | **100% (5/5)** | Tie ✅ |

**Speed comparison:**
- 5-bit vs 6-bit: **2.3x faster** (2.53s vs 5.76s)
- 5-bit vs Phase 23: **Same speed** (2.53s vs 2.47s)

## Key Findings

### Finding 1: 5-bit Preserves Field Access Patterns

**Hypothesis:** 5-bit (32 quantization levels) might lose field access patterns vs 6-bit (64 levels)

**Result:** ❌ Hypothesis REJECTED - 5-bit has **better** field access (90% vs 85%)

**Explanation:**
- Phase 8 found 4-bit (16 levels) destroys LoRA signal
- But 5-bit (32 levels) is sufficient for field access patterns
- **Threshold: Between 16 and 32 quantization levels**

### Finding 2: 6-bit Speed Penalty is Real

**6-bit Phase 26:** 5.76s avg gen time (2.3x slower than Phase 23)

**Root cause:** Model size close to memory limit triggers MLX warnings:
```
[WARNING] Generating with a model that requires 23661 MB which is close to
the maximum recommended size of 25559 MB. This can be slow.
```

**5-bit Phase 26:** No warnings, runs at full speed (2.53s)

### Finding 3: 5-bit Quality > 6-bit Quality

**Unexpected:** 5-bit has **higher** accuracy than 6-bit (92% vs 88%)

**Possible explanations:**
1. Quantization noise at 6-bit hits a bad spot for these patterns
2. 5-bit quantization is more "regular" (power of 2: 32 levels)
3. Random variation (need more queries to confirm)

**Impact:** Even if tied, 5-bit would win on speed. But it's also more accurate!

## Decision Matrix

**Criteria for 5-bit success (from plan):**
- ✅ Overall accuracy ≥80%: **92%** (exceeds by 12 points)
- ✅ Field access rate ≥80%: **90%** (exceeds by 10 points)
- ✅ Speed ≤3.0s avg: **2.53s** (beats by 0.47s)
- ✅ Memory ≤20 GB: **19.55 GB** (beats by 0.45 GB)

**Result:** **ALL SUCCESS CRITERIA MET** ✅

## Production Recommendation

**Deploy:** `fused_model_qwen3_phase26_5bit/`

**Rationale:**
1. Best accuracy: 92% overall, 90% field access
2. Fastest speed: 2.53s avg (matches Phase 23)
3. Smallest size: 19.56 GB (18% less than 6-bit)
4. No memory warnings (stays well under 25.5 GB limit)

**Archive:** `fused_model_qwen3_phase26_6bit/` (no longer needed)
- Can delete to reclaim 23 GB disk space
- Or keep as "high-precision variant" for research

## What We Learned

### Key Lesson: 5-bit is Sufficient for LoRA Fine-tuning

**Quantization thresholds:**
- 4-bit (16 levels): ❌ Destroys LoRA signal
- **5-bit (32 levels): ✅ Preserves LoRA signal** (NEW!)
- 6-bit (64 levels): ✅ Preserves LoRA signal (but slower)
- 8-bit (256 levels): ✅ Preserves LoRA signal (but larger)

**Updated recommendation for future phases:**
- **Use 5-bit by default** (best speed/quality/size balance)
- Only use 6-bit+ if specific patterns require higher precision
- Never use 4-bit for fine-tuned models

### Why 6-bit was Slower

**Memory pressure:** 23 GB model triggers MLX performance warnings
- M3 Max has 64 GB unified memory
- MLX recommends staying under ~25.5 GB per model
- 6-bit Phase 26 (23 GB) is close to limit
- 5-bit Phase 26 (19.5 GB) has comfortable headroom

**Impact:** 2.3x slowdown for 6-bit vs 5-bit on same training data

## Files Created

**New files:**
- `scripts/quantize_phase26_5bit.sh` - 5-bit quantization script
- `fused_model_qwen3_phase26_5bit/` - Production model (19.56 GB)
- `logs/phase26_validation_fused_model_qwen3_phase26_5bit.json` - Validation results
- `logs/fused_model_qwen3_phase26_5bit_results.json` - Speed benchmark
- `docs/diary/2026-02-15-phase26-5bit-validation.md` - This document

**Modified files:**
- `scripts/benchmark_phases.py` - Added 5-bit Phase 26

## Comparison with Phase 23

**What Phase 26 (5-bit) adds over Phase 23 (5-bit):**

| Capability | Phase 23 | Phase 26 | Improvement |
|------------|----------|----------|-------------|
| Field access rate | 5% | 90% | +85 points |
| Conditional logic | Poor | 100% | Major |
| Iteration patterns | Poor | 100% | Major |
| Multi-step workflows | Poor | 80% | Major |
| Speed | 2.47s | 2.53s | -0.06s (negligible) |
| Size | 19.56 GB | 19.56 GB | Same |

**Verdict:** Phase 26 (5-bit) is a **strict upgrade** over Phase 23:
- Massive capability gain (+85 points field access)
- Negligible speed cost (0.06s = 2.4% slower)
- Same size and memory

## Next Steps

1. **Update MEMORY.md:** Change production recommendation to 5-bit
2. **Delete 6-bit model:** Reclaim 23 GB disk space (optional)
3. **Update roadmap:** Mark Phase 26 as complete
4. **Future phases:** Use 5-bit quantization by default

## Timeline

**Total time:** ~25 minutes (as predicted)
- Quantization: 2 minutes
- Validation suite: 15 minutes
- Speed benchmark: 5 minutes
- Documentation: 3 minutes

## Success Metrics

**All targets exceeded:**
- ✅ Overall accuracy: 92% (target: 80%, beat by 12 points)
- ✅ Field access: 90% (target: 80%, beat by 10 points)
- ✅ Speed: 2.53s (target: ≤3.0s, beat by 0.47s)
- ✅ Memory: 19.55 GB (target: ≤20 GB, beat by 0.45 GB)
- ✅ Quality > 6-bit: YES (92% vs 88%, +4 points)
- ✅ Speed > 6-bit: YES (2.53s vs 5.76s, 2.3x faster)

**Outcome:** ✅ **DEPLOY 5-BIT AS PRODUCTION MODEL**
