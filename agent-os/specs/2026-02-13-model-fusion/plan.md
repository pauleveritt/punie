# Model Fusion Spec - Plan

## Goal

Fix Phase 5 fused model regression where 4-bit re-quantization destroyed fine-tuning, achieving 100% accuracy with optimal speed/memory via 8-bit quantization.

## Components

### 18.1: Identify root cause

- Phase 5 fused model: 60% accuracy (same as untrained base)
- Phase 5 adapter: 100% accuracy ✅
- Evidence: 13% of weight bytes changed during fusion
- Investigation: Trace `mlx_lm.fuse` quantization process
- Discovery: 4-bit re-quantization (16 levels) rounds away LoRA perturbations

### 18.2: Implement dequantized fusion

- Command: `mlx_lm.fuse --dequantize` to prevent re-quantization
- Result: float16 model without quantization artifacts
- Output: `fused_model_f16/` (14.20 GB)
- Validation: Test discrimination accuracy (expect 100%)

### 18.3: Test 8-bit re-quantization

- Command: `mlx_lm.convert --quantize --q-bits 8`
- Rationale: 256 levels (8-bit) >> 16 levels (4-bit)
- Output: `fused_model_8bit/` (7.55 GB)
- Validation: Test discrimination accuracy (expect 100%)

### 18.4: Benchmark 4 configurations

- Refactor `benchmark_phase5_vs_base.py` to be config-driven
- Add argparse: `--configs base adapter fused-f16 fused-8bit`
- Test all 4 on standard 5-query discrimination suite
- Compare: disk size, memory, load time, generation speed, accuracy
- Document findings in `benchmark_phase5c.log`

## Fusion Commands

**Float16 fusion:**
```bash
uv run python -m mlx_lm.fuse \
  --model mlx-community/Qwen2.5-Coder-7B-Instruct-4bit \
  --adapter-path ./adapters \
  --save-path ./fused_model_f16 \
  --dequantize
```

**8-bit quantization:**
```bash
uv run python -m mlx_lm.convert \
  --hf-path ./fused_model_f16 \
  --mlx-path ./fused_model_8bit \
  --quantize \
  --q-bits 8
```

## Success Criteria

- ✅ Float16 fused: 100% accuracy (proves dequantization works)
- ✅ 8-bit fused: 100% accuracy (proves 8-bit preserves signal)
- ✅ 8-bit fused: <15s avg inference (faster than adapter)
- ✅ 8-bit fused: <10 GB disk/memory (smaller than float16)
- ✅ Root cause documented and understood
