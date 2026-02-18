#!/usr/bin/env bash
# Phase 43a training pipeline — Qwen3-Coder-30B-A3B baseline confirmation
#
# Experiment A of Phase 43: confirms production Coder-30B-A3B baseline with fresh training run.
# Tests whether domain (60%) and multi_tool (35%) can be improved with Phase 43 naming.
#
# Key differences from Phase 33b:
#   - Phase 43 output paths (adapters_phase43a, fused_model_qwen3_phase43a_*)
#   - Same base model: Qwen3-Coder-30B-A3B-Instruct-4bit (confirmed production model)
#   - Same data: data/phase33_merged (1159 train + 123 valid)
#   - Same hyperparams: 800 iters, lr=1e-4, 8 LoRA layers, grad-accum=4
#
# Hypothesis: Fresh run with production Coder weights confirms 82.4% baseline.
# Success criteria: Overall ≥82.4% AND (domain >60% OR multi_tool >35%)
#
# Estimated time: ~30-40 min total on Apple Silicon M-series (32 GB)
# Disk usage: ~77 GB temp (57 GB float16 + 20 GB 5-bit); 20 GB final
#
# Usage:
#   bash scripts/run_phase43a_coder30b.sh
#   nohup bash scripts/run_phase43a_coder30b.sh &

set -euo pipefail

LOGFILE="logs/phase43a_coder30b_training.log"
BASE_MODEL="mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit"
ADAPTER_PATH="adapters_phase43a"
FUSED_F16="fused_model_qwen3_phase43a_f16"
FUSED_5BIT="fused_model_qwen3_phase43a_coder30b_5bit"
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
log "Phase 43a Training Pipeline — Qwen3-Coder-30B-A3B Baseline"
log "Base model: $BASE_MODEL"
log "Data: $DATA (1159 train + 123 valid)"
log "Adapter output: $ADAPTER_PATH"
log "LoRA layers: 8 (MoE default; 8/94 attention layers = expert-level coverage)"
log "Hypothesis: Confirms 82.4% baseline; may improve domain/multi_tool"
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

# ------------------------------------------------------------------ #
# STEP 1: LoRA Training
# ------------------------------------------------------------------ #
log ""
log "STEP 1: LoRA Training (800 iters, ~3-4 hours)"

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
    --num-layers 8 \
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
log "STEP 2: Fuse adapters → float16 (~10-20 min)"
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
log "STEP 3: Quantize float16 → 5-bit (~10-20 min)"
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
log "STEP 5: Running Phase 33 direct eval (27 prompts, target ≥82.4%)"

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
log "Phase 43a training pipeline COMPLETE"
log "  Total time: ${TOTAL_MINS}m"
log "  Production model: $FUSED_5BIT"
log "  Model size: $(du -sh "$FUSED_5BIT" | cut -f1)"
log "  Eval verdict: $([ $EVAL_EXIT -eq 0 ] && echo 'PASS ✓' || echo 'needs review')"
log "======================================================"
log ""
log "Pre-registered success criteria (Phase 43a vs Phase 33b baseline):"
log "  text_tools:  ≥100%  (baseline 100%)"
log "  validation:  ≥100%  (baseline 100%)"
log "  git:         ≥100%  (baseline 100%)"
log "  cst:         ≥100%  (baseline 100%)"
log "  lsp:         ≥90%   (baseline 90%)"
log "  domain:      >60%   (baseline 60%) ← target improvement"
log "  multi_tool:  >35%   (baseline 35%) ← target improvement"
log "  Overall:     ≥82.4% (baseline 82.4%)"
log ""
log "Compare against Phase 33b (production): fused_model_qwen3_phase33b_5bit/"
log "Log: $LOGFILE"
