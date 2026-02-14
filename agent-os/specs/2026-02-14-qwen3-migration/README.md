# Phase 8: Qwen3-Coder-30B-A3B Migration

**Date:** February 14, 2026
**Status:** In Progress
**Goal:** Migrate from Qwen2.5-Coder-7B (dense) to Qwen3-Coder-30B-A3B (MoE) with domain-pruned training data

## Overview

Phase 8 migrates Punie from a 7B dense model to a 30B MoE model with only 3.3B active parameters. This provides better quality while maintaining reasonable latency and memory usage on M1 Mac hardware.

## Key Decisions

### Model Selection
- **Base:** `mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit`
- **Total parameters:** 30.5B (30B model weights + 0.5B expert router)
- **Active parameters:** 3.3B per token (via MoE routing)
- **Memory:** ~22GB peak during training, ~8-10GB for 8-bit inference
- **Hardware:** M1 Max 32GB unified memory

### Training Data Strategy
- **Approach:** Domain-pruned from Phase 7 data
- **Target:** 600-800 examples (down from 824 in Phase 7)
- **Focus:** Python + HTML + CSS + JS with Django/FastAPI/Flask/Sphinx
- **Split:** 70% tool-calling, 30% direct-answer
- **Removed:** Stack v2 examples not relevant to target stack

### Training Configuration
Based on Phase 7 success and Phase 0-5c learnings:
- **Iterations:** 500
- **Batch size:** 2
- **Learning rate:** 1e-4
- **LoRA rank:** 8
- **Layers adapted:** 16
- **Stop sequences:** Fixed in `factory.py` (use `stop_sequences` key, not `stop`)

### Quantization Strategy
Based on Phase 5c findings:
- **DO NOT** fuse to 4-bit (destroys LoRA signal)
- **DO** fuse to float16, then re-quantize to 8-bit
- **8-bit** provides 256 quantization levels (vs 16 for 4-bit)
- **Result:** 100% accuracy + 8-10x speedup vs adapter

## Implementation Steps

### 1. Verify Trainability ✅ Complete
- Downloaded Qwen3-30B-A3B-Instruct-4bit
- Ran 5-iteration test on M1 32GB
- **Result:** Peak memory 22.978 GB (safe!)
- **Script:** `scripts/test_qwen3_trainability.sh`

### 2. Generate Training Data ✅ Complete
- Cloned Django and Sphinx repos
- Filtered Phase 7 data to domain-relevant examples (824 → 673)
- Added 10 new domain-specific examples (Django, Sphinx, HTML/CSS/JS)
- **Total:** 683 examples (546 train, 68 valid, 69 test)
- **Split:** 70.7% tool, 29.3% direct (target: 70/30) ✅
- **Script:** `scripts/generate_phase8_data.py`

### 3. Train Adapter ⏳ In Progress
- Training with 500 iterations, batch_size=2
- Checkpoints at iter 250 and 500
- **ETA:** ~25 minutes (not 2 hours as initially estimated)
- **Script:** `scripts/train_phase8.sh`

### 4. Benchmark Performance 📋 Pending
- 5-query discrimination test vs Phase 7
- Measure accuracy, speed, memory
- **Script:** `scripts/benchmark_phase8.py`

### 5. Fuse to 8-bit 📋 Pending
- Dequantize → fuse → re-quantize to 8-bit
- **Expected:** 100% accuracy, 8-10x speedup
- **Script:** `scripts/fuse_phase8.sh`

### 6. Update References ⏳ In Progress
- Updated `src/punie/agent/adapter.py` error message (line 274)
- Creating this migration spec
- Update README.md to add Phase 8 section
- Update training scripts

## Expected Results

Based on Phase 5c and Phase 7 learnings:

### Accuracy
- **Target:** 100% on 5-query discrimination test
- **Rationale:** 8-bit fusion preserves LoRA signal

### Speed
- **Adapter:** Slower due to runtime merging overhead
- **8-bit fused:** 8-10x faster than adapter
- **vs Base 4-bit:** 2.7x faster (based on Phase 5c results)

### Memory
- **Training:** ~23GB peak (fits in 32GB)
- **Adapter inference:** ~8GB (4-bit base + 0.4GB adapter)
- **8-bit fused:** ~8-10GB (single model file)
- **Float16 fused:** ~25-30GB (archive only, not for production)

## Critical Learnings Applied

### From Phase 4
- **Stop sequences:** Must use `stop_sequences` key (not `stop`) in `factory.py` line 241
- Prevents infinite loops when model doesn't respect `<|im_end|>` tokens

### From Phase 5
- **Balanced training data:** 70/30 tool vs direct-answer split
- Prevents model from calling tools for concept questions

### From Phase 5c
- **8-bit is optimal:** 4-bit fusion destroys LoRA signal
- **Dequantize first:** Preserve deltas, then re-quantize
- **8-bit = production:** 100% accuracy + 8x speedup + 8GB memory

### From Phase 7
- **Training config:** 500 iters, batch_size 2, lr 1e-4 works well
- **MoE LoRA:** Trainable parameters auto-discovered by mlx_lm

## Files Modified

### Source Code
- `src/punie/agent/adapter.py` - Updated model reference in error message (line 274)

### Scripts
- `scripts/test_qwen3_trainability.sh` - NEW: 5-iter trainability test
- `scripts/generate_phase8_data.py` - NEW: domain-pruned data generator
- `scripts/train_phase8.sh` - NEW: Phase 8 training script
- `scripts/benchmark_phase8.py` - NEW: Phase 8 vs Phase 7 benchmark
- `scripts/fuse_phase8.sh` - NEW: 8-bit fusion script

### Data
- `data/phase8_format/` - NEW: 683 domain-pruned examples (80/10/10 split)
- `data/repos/django/` - NEW: Cloned Django for examples
- `data/repos/sphinx/` - NEW: Cloned Sphinx for examples

### Models (Created by Scripts)
- `adapters_phase8/` - Phase 8 LoRA adapter (training output)
- `fused_model_qwen3_phase8_f16/` - Float16 fused model (~25-30GB)
- `fused_model_qwen3_phase8_8bit/` - 8-bit fused model (~8-10GB, production)

### Documentation
- `agent-os/specs/2026-02-14-qwen3-migration/` - This spec
- `README.md` - Will add Phase 8 quick start section
- `MODEL_PERFORMANCE_TRACKER.md` - Will add Phase 8 results

## Success Criteria

- [x] Training completes without OOM on M1 32GB
- [x] 100% accuracy on 5-query discrimination test (5-bit: 100%, 6-bit: 100%)
- [x] End-to-end latency measurement (5-bit: 2.61s avg, 6-bit: 3.83s avg)
- [x] Memory usage within 32GB during both training and inference (5-bit: 20GB, training: 23GB peak)
- [x] Code quality checks pass (`astral:ruff`, `astral:ty`)
- [x] Tests pass (`uv run pytest`)

## Quantization Breakthrough (Post-Phase 8)

After Phase 8 training, experimented with quantization levels to optimize memory:
- **5-bit (32 levels):** 20GB, 100% accuracy ✅ **OPTIMAL**
- **6-bit (64 levels):** 23GB, 100% accuracy ✅
- **8-bit (256 levels):** 30GB, 100% accuracy ✅
- **4-bit (16 levels):** 15GB, 60% accuracy ❌

**Discovery:** LoRA signal preservation threshold is between 16 and 32 quantization levels.
**Production:** Use 5-bit quantization for 33% size reduction with zero quality loss.

## Next Phase Ideas

### Phase 9: Speculative Decoding
- Use smaller model (1.5B) to draft tokens
- Use Qwen3-30B to verify and accept/reject
- Target: 2-3x speedup with same quality

### Phase 10: Multi-Agent Architecture
- Separate "planner" and "executor" agents
- Planner uses direct-answer model for reasoning
- Executor uses tool-calling model for actions

### Phase 11: Continuous Learning
- Collect user feedback on responses
- Generate new training examples from corrections
- Periodic retraining with expanded dataset
