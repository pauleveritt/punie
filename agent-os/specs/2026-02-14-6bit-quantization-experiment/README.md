# 6-bit Quantization Experiment

**Date:** February 14, 2026
**Status:** In Progress
**Goal:** Reduce model memory footprint by 30-40% while preserving fine-tuning quality

## Research Question

Can 6-bit quantization (64 discrete levels per group) preserve LoRA fine-tuning deltas while reducing memory usage compared to 8-bit (256 levels)?

## Background

From Phase 5c, we learned that quantization level directly impacts LoRA signal preservation:
- **4-bit (16 levels):** ❌ Destroys LoRA signal → 60% accuracy (no better than base)
- **8-bit (256 levels):** ✅ Preserves LoRA signal → 100% accuracy
- **Float16 (infinite precision):** ✅ Perfect preservation → 100% accuracy

The question: Where is the threshold? Can 6-bit (64 levels) preserve enough signal while reducing size?

## Hypothesis

6-bit quantization may offer a "sweet spot":
- **64 quantization levels** could preserve small LoRA deltas (unlike 4-bit's 16 levels)
- **~30-40% disk size reduction** compared to 8-bit
- **Similar memory reduction** during inference
- **Potentially faster** due to smaller model size

## Current Model Sizes

| Quantization | Disk Size | Runtime Memory | Accuracy |
|--------------|-----------|----------------|----------|
| Float16      | 60 GB     | ~25-30 GB      | 100%     |
| 8-bit        | 30 GB     | ~8-10 GB       | 100%     |
| 6-bit        | ~20 GB?   | ~6-8 GB?       | ???      |
| 4-bit        | 15 GB     | ~4-5 GB        | 60% ❌   |

## Experiment Design

### 1. Quantization
Convert Phase 8 float16 model to 6-bit:
```bash
./scripts/quantize_6bit.sh
```

Configuration:
- Input: `fused_model_qwen3_phase8_f16/` (60GB)
- Output: `fused_model_qwen3_phase8_6bit/` (~20GB expected)
- Group size: 64 (standard for MLX)
- Quantization bits: 6

### 2. Benchmarking
Compare 6-bit vs 8-bit on 5-query discrimination test:
```bash
./scripts/benchmark_6bit_vs_8bit.py
```

Metrics:
- **Accuracy:** 5-query discrimination (3 tool, 2 direct)
- **Disk size:** Total model file size
- **Runtime memory:** Active memory during inference
- **Speed:** Average generation time per query
- **Load time:** Model loading latency

### 3. Success Criteria

**Minimum viable (proceed with 6-bit):**
- Accuracy ≥ 80% (4/5 correct)
- Disk size reduction ≥ 25%
- Memory reduction ≥ 20%
- Speed similar or better than 8-bit

**Optimal (6-bit is the new standard):**
- Accuracy ≥ 100% (5/5 correct)
- Disk size reduction ≥ 30%
- Memory reduction ≥ 25%
- Speed ≥ 1.1x faster

**Failure (stick with 8-bit):**
- Accuracy < 80%
- Minimal size/memory reduction
- Slower than 8-bit

## Implementation

### Scripts Created
- `scripts/quantize_6bit.sh` - Convert float16 to 6-bit
- `scripts/benchmark_6bit_vs_8bit.py` - Compare quantization levels

### Files Generated
- `fused_model_qwen3_phase8_6bit/` - 6-bit quantized model (~20GB)
- `logs/6bit_vs_8bit_benchmark.json` - Benchmark results

## Expected Outcomes

### If 6-bit succeeds (≥80% accuracy):
- **Immediate:** Switch to 6-bit for production
- **Memory savings:** ~30% reduction vs 8-bit
- **Documentation:** Update MEMORY.md with 6-bit as standard
- **Next phase:** Archive float16 and 8-bit models

### If 6-bit fails (<80% accuracy):
- **Root cause:** 64 quantization levels insufficient for LoRA deltas
- **Alternative 1:** Try 7-bit quantization (128 levels)
- **Alternative 2:** Distill to smaller base model (Qwen2.5-3B)
- **Alternative 3:** Expert pruning for MoE (remove unused experts)
- **Fallback:** Keep using 8-bit (30GB)

## Timeline

- **Quantization:** 30-45 minutes (convert float16 → 6-bit)
- **Benchmark:** 10-15 minutes (5 queries × 2 models)
- **Total:** ~1 hour

## Related Work

- Phase 5c: Discovered 4-bit destroys LoRA signal
- Phase 8: Qwen3-30B-A3B MoE migration (30GB 8-bit model)
- This experiment: Optimizing for memory while preserving quality

## Next Steps

1. ✅ Create quantization script
2. ✅ Create benchmark script
3. ⏳ Run 6-bit quantization (~30 min)
4. 📋 Run benchmark comparison
5. 📋 Analyze results and decide next action
6. 📋 Update MEMORY.md with findings
