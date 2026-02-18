#!/usr/bin/env bash
# Phase 43b training pipeline — Qwen3-14B Dense (MoE hypothesis test)
#
# Experiment B of Phase 43: tests whether 14B dense can learn execute_code wrapper format.
# This is a clean probe of the MoE routing hypothesis.
#
# Context:
#   - Phase 40 (8B dense): ❌ 18.5% — failed. Learned which tool, not how to format call.
#   - Phase 33b (30B MoE):  ✅ 82.4% — succeeded. 3B active parameters via routing.
#   - Paradox: 8B dense (8B active) > 30B MoE (3B active) per-token, yet MoE wins.
#
# Two hypotheses:
#   A: Total parameters (30B > 14B > 8B) → 14B should succeed (≥80%)
#   B: MoE routing specialization required → 14B dense will fail (<80%)
#
# Key differences from Phase 33b:
#   - BASE_MODEL: Qwen3-14B (dense, not Coder, not MoE)
#   - --num-layers 12 (~37% LoRA coverage; dense needs more than MoE's 8/94)
#   - Phase 43b output paths
#   - Same data: data/phase33_merged (same 1159 train + 123 valid)
#   - Other hyperparams identical to Phase 33b (fair comparison)
#
# WARNING: No Coder variant exists for 14B. This introduces a confound:
#   if 14B fails, it could be capacity OR weaker code pretraining.
#   If 14B succeeds, it definitively confirms Hypothesis A.
#
# Model source: mlx-community/Qwen3-14B-4bit
# Alternative:  LibraxisAI/Qwen3-14b-MLX-Q5 (pre-quantized 5-bit, ~9 GB)
#
# Estimated time: ~90 min total on Apple Silicon (14B is ~2x faster than 30B MoE)
# Disk: ~50 GB temp (30 GB float16 + 8 GB 4-bit); ~9 GB final 5-bit model
#
# Usage:
#   bash scripts/run_phase43b_14b_dense.sh
#   nohup bash scripts/run_phase43b_14b_dense.sh &
#
# Pre-run:
#   Verify tokenizer has <tool_call> and <tool_response> as single tokens:
#   uv run python scripts/phase40_tokenizer_check.py --model mlx-community/Qwen3-14B-4bit

set -euo pipefail

LOGFILE="logs/phase43b_14b_dense_training.log"
BASE_MODEL="mlx-community/Qwen3-14B-4bit"
ADAPTER_PATH="adapters_phase43b"
FUSED_F16="fused_model_qwen3_phase43b_14b_f16"
FUSED_5BIT="fused_model_qwen3_phase43b_14b_5bit"
DATA="data/phase33_merged"
START_TIME=$(date +%s)

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOGFILE"
}

elapsed() {
    local END=$(date +%s)
    local SECS=$(( END - START_TIME ))
    printf "%02dh:%02dm:%02ds" $((SECS/3600)) $(((SECS%3600)/60)) $((SECS%60))
}

mkdir -p logs

log "======================================================"
log "Phase 43b Training Pipeline — Qwen3-14B Dense (MoE Hypothesis Test)"
log "Base model: $BASE_MODEL"
log "Data: $DATA (1159 train + 123 valid, same as Phase 33b)"
log "Adapter output: $ADAPTER_PATH"
log "LoRA layers: 12 (12/40 = 30% coverage; dense needs more than MoE's 8%)"
log ""
log "Hypothesis A (total params): 14B will succeed (≥80%)"
log "Hypothesis B (MoE routing):  14B will fail (<80%)"
log "======================================================"

# ------------------------------------------------------------------ #
# STEP 0: Preflight checks
# ------------------------------------------------------------------ #
log "STEP 0: Preflight checks"

if [ ! -f "$DATA/train.jsonl" ] || [ ! -f "$DATA/valid.jsonl" ]; then
    log "ERROR: Training data not found at $DATA/"
    log "Run: uv run python scripts/merge_phase33_data.py"
    exit 1
fi

TRAIN_COUNT=$(wc -l < "$DATA/train.jsonl")
VALID_COUNT=$(wc -l < "$DATA/valid.jsonl")
log "  train.jsonl: $TRAIN_COUNT examples"
log "  valid.jsonl: $VALID_COUNT examples"

if [ "$TRAIN_COUNT" -lt 1000 ]; then
    log "ERROR: Expected at least 1000 training examples, got $TRAIN_COUNT"
    exit 1
fi

log "  Preflight passed ✓"
log ""
log "  REMINDER: Run tokenizer check before first use:"
log "    uv run python scripts/phase40_tokenizer_check.py --model $BASE_MODEL"
log "  Must confirm: <tool_call> and <tool_response> are single tokens in vocabulary"

# ------------------------------------------------------------------ #
# STEP 1: LoRA Training
# ------------------------------------------------------------------ #
log ""
log "STEP 1: LoRA Training (800 iters, ~45-60 min for 14B dense)"
log "  Note: 12 LoRA layers (vs 8 for MoE) for higher dense model coverage"

# Remove stale adapter if exists (resume from scratch)
if [ -d "$ADAPTER_PATH" ] && [ ! -f "$ADAPTER_PATH/adapters.safetensors" ]; then
    log "  Removing incomplete adapter directory: $ADAPTER_PATH"
    rm -rf "$ADAPTER_PATH"
fi

TRAIN_START=$(date +%s)

uv run python -m mlx_lm lora \
    --train \
    --model "$BASE_MODEL" \
    --data "$DATA" \
    --adapter-path "$ADAPTER_PATH" \
    --iters 800 \
    --batch-size 1 \
    --learning-rate 1e-4 \
    --num-layers 12 \
    --grad-accumulation-steps 4 \
    --mask-prompt \
    --save-every 200 \
    --steps-per-report 10 \
    --steps-per-eval 50 \
    --val-batches 10 \
    2>&1 | tee -a "$LOGFILE"

TRAIN_END=$(date +%s)
TRAIN_MINS=$(( (TRAIN_END - TRAIN_START) / 60 ))
log ""
log "STEP 1 complete: training finished in ${TRAIN_MINS}m"

if [ ! -f "$ADAPTER_PATH/adapters.safetensors" ]; then
    log "ERROR: adapters.safetensors not found after training"
    exit 1
fi
log "  Adapter saved: $ADAPTER_PATH/adapters.safetensors ✓"

# ------------------------------------------------------------------ #
# STEP 2: Fuse adapters (dequantize → float16)
# ------------------------------------------------------------------ #
log ""
log "STEP 2: Fuse adapters → float16 (~5-10 min for 14B)"
log "  Output: $FUSED_F16"

if [ -d "$FUSED_F16" ]; then
    log "  Removing existing $FUSED_F16"
    rm -rf "$FUSED_F16"
fi

FUSE_START=$(date +%s)

uv run python -m mlx_lm fuse \
    --model "$BASE_MODEL" \
    --adapter-path "$ADAPTER_PATH" \
    --save-path "$FUSED_F16" \
    --dequantize \
    2>&1 | tee -a "$LOGFILE"

FUSE_END=$(date +%s)
FUSE_MINS=$(( (FUSE_END - FUSE_START) / 60 ))
log "STEP 2 complete: fuse finished in ${FUSE_MINS}m"

if [ ! -d "$FUSED_F16" ]; then
    log "ERROR: Fused model directory not created: $FUSED_F16"
    exit 1
fi
log "  Fused model: $FUSED_F16 ✓"

# ------------------------------------------------------------------ #
# STEP 3: Quantize to 5-bit
# ------------------------------------------------------------------ #
log ""
log "STEP 3: Quantize float16 → 5-bit (~5-10 min for 14B)"
log "  Output: $FUSED_5BIT"

if [ -d "$FUSED_5BIT" ]; then
    log "  Removing existing $FUSED_5BIT"
    rm -rf "$FUSED_5BIT"
fi

QUANT_START=$(date +%s)

uv run python -m mlx_lm convert \
    --hf-path "$FUSED_F16" \
    --mlx-path "$FUSED_5BIT" \
    -q \
    --q-bits 5 \
    --q-group-size 64 \
    2>&1 | tee -a "$LOGFILE"

QUANT_END=$(date +%s)
QUANT_MINS=$(( (QUANT_END - QUANT_START) / 60 ))
log "STEP 3 complete: quantize finished in ${QUANT_MINS}m"

if [ ! -d "$FUSED_5BIT" ]; then
    log "ERROR: Quantized model directory not created: $FUSED_5BIT"
    exit 1
fi
MODEL_SIZE=$(du -sh "$FUSED_5BIT" | cut -f1)
log "  5-bit model: $FUSED_5BIT ($MODEL_SIZE) ✓"

# ------------------------------------------------------------------ #
# STEP 4: Clean up intermediate float16 model to save disk
# ------------------------------------------------------------------ #
log ""
log "STEP 4: Cleanup — removing intermediate float16 model"
log "  Disk before: $(df -h . | tail -1 | awk '{print $4}') free"

rm -rf "$FUSED_F16"
log "  Removed $FUSED_F16"
log "  Disk after: $(df -h . | tail -1 | awk '{print $4}') free"

# ------------------------------------------------------------------ #
# STEP 5: Run Phase 33 direct eval (27 prompts)
# ------------------------------------------------------------------ #
log ""
log "STEP 5: Running Phase 33 direct eval (27 prompts, target ≥80%)"

EVAL_EXIT=0
uv run python scripts/run_phase33_direct_eval.py --model "$FUSED_5BIT" --port 8080 \
    2>&1 | tee -a "$LOGFILE" || EVAL_EXIT=$?

if [ $EVAL_EXIT -eq 0 ]; then
    log "STEP 5 complete: eval PASSED ✓"
else
    log "STEP 5 complete: eval did not reach ≥80% target — check $LOGFILE"
fi

# ------------------------------------------------------------------ #
# DONE
# ------------------------------------------------------------------ #
TOTAL_MINS=$(( ($(date +%s) - START_TIME) / 60 ))
log ""
log "======================================================"
log "Phase 43b training pipeline COMPLETE"
log "  Total time: ${TOTAL_MINS}m"
log "  14B model: $FUSED_5BIT"
log "  Model size: $(du -sh "$FUSED_5BIT" | cut -f1)"
log "  Eval verdict: $([ $EVAL_EXIT -eq 0 ] && echo 'PASS ✓' || echo 'needs review')"
log "======================================================"
log ""
log "Pre-registered success criteria (Phase 43b vs Phase 33b baseline 82.4%):"
log "  text_tools:  ≥90%   (baseline 100%)"
log "  validation:  ≥90%   (baseline 100%)"
log "  git:         ≥80%   (baseline 100%)"
log "  cst:         ≥80%   (baseline 100%)"
log "  lsp:         ≥60%   (baseline 90%)"
log "  domain:      ≥40%   (baseline 60%)"
log "  multi_tool:  ≥20%   (baseline 35%)"
log "  Overall:     ≥80%   (baseline 82.4%)"
log ""
log "Interpretation:"
log "  ≥80% → Hypothesis A (total params): 14B crosses threshold"
log "  50-79%  → Ambiguous; MoE and params both contribute"
log "  <50%    → Hypothesis B (MoE routing) likely"
log "  ~18%    → Strong B; 14B failed same way as 8B (Phase 40)"
log ""
log "Compare against:"
log "  Phase 33b (production, 82.4%): fused_model_qwen3_phase33b_5bit/"
log "  Phase 40  (8B dense, 18.5%):   fused_model_qwen3_phase40_8b_5bit/"
log ""
log "Log: $LOGFILE"
