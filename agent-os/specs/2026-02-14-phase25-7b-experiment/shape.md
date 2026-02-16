# Phase 25: 7B Model Experiment

**Status:** In Progress
**Created:** 2026-02-15
**Goal:** Test if Qwen2.5-Coder-7B can match Qwen3-30B-A3B performance with Code Mode fine-tuning

## Overview

Phase 25 is a critical experiment to determine if a smaller, denser 7B parameter model can achieve similar accuracy to the 30B MoE model used in Phases 22-24, while providing 4-5x speed improvement and 75% memory reduction.

## Success Criteria

- **>=90% of 30B accuracy** → Use 7B as primary model
- **70-90% accuracy** → Split by use case (7B for simple, 30B for complex)
- **<70% accuracy** → Stick with 30B

## Model Comparison

| Attribute | Qwen2.5-Coder-7B | Qwen3-30B-A3B | Notes |
|-----------|------------------|---------------|-------|
| Parameters | 7B dense | 30B MoE (3B active) | 7B all active vs 10% active |
| Layers | 28 | 48 | Dense vs MoE architecture |
| Expected size (5-bit) | 4-5 GB | 20 GB | 75-80% size reduction |
| Expected memory | 5-6 GB | 23 GB | 74-78% memory reduction |
| Expected speed | 4-5x faster | Baseline | Dense forward pass |
| Tokenizer | Qwen2.5 | Qwen3 | Same special tokens |

## Training Configuration

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Data | `data/phase24_merged/` | 857 examples (Phase 24) |
| Iterations | 600 | More data = more iterations |
| Batch size | 2 | 7B fits in memory |
| LoRA layers | 16 (57% coverage) | Dense needs more layers than MoE |
| Learning rate | 1e-4 | Proven effective |
| Quantization | 5-bit (32 levels) | Proven LoRA preservation threshold |

## Test Suite

20-query test suite covering:
- **13 tool queries:** typecheck, ruff_check, pytest_run, read_file, run_command
- **7 direct answers:** Concepts, comparisons, best practices

Test validates:
1. Code Mode format recognition (`execute_code`)
2. Tool vs direct answer discrimination
3. Typed tool result parsing (Pydantic models)
4. Response quality

## Risks

1. **Code Mode on 7B:** Never tested on dense architecture (419 examples should teach it)
2. **5-bit quantization:** Validated on 30B MoE only (fall back to 8-bit if needed)
3. **`<tool_response>` tokenization:** Qwen3 has as 1 token, Qwen2.5 as multiple (should learn from data)

## Expected Outcomes

### Best Case (>=90% accuracy)
- 7B becomes primary model
- 4-5x speed improvement in production
- 75% memory reduction
- Enables running on consumer hardware

### Middle Case (70-90% accuracy)
- Split by complexity:
  - 7B for quick queries (read, search, concepts)
  - 30B for complex reasoning (refactoring, architecture)
- User can choose speed vs accuracy

### Worst Case (<70% accuracy)
- Stick with 30B
- Document why dense 7B underperforms vs MoE 30B
- Possible causes: MoE routing, expert specialization

## Deliverables

1. Trained adapter (`adapters_phase25_7b/`)
2. Fused float16 model (`fused_model_qwen25_phase25_7b_f16/`)
3. Quantized 5-bit model (`fused_model_qwen25_phase25_7b_5bit/`)
4. Test results JSON (`logs/phase25_results.json`)
5. Comparison report (7B vs 30B side-by-side)
6. Documentation in diary + MEMORY.md

## Timeline

- Training: ~30-40 minutes
- Fusion: ~5 minutes
- Quantization: ~2 minutes
- Testing: ~15 minutes (20 queries)
- **Total: ~1 hour**

## Files Created

- `scripts/train_phase25.sh`
- `scripts/fuse_phase25.sh`
- `scripts/quantize_phase25.sh`
- `scripts/test_phase25_model.py`
- `scripts/run_phase25.sh`
- `agent-os/specs/2026-02-14-phase25-7b-experiment/shape.md` (this file)

## Next Steps After Phase 25

- If 7B succeeds: Deploy 7B for production, archive 30B
- If split needed: Implement router/selector logic
- If 7B fails: Document findings, continue with 30B
- Consider other architectures (14B, Qwen3-7B if released)
