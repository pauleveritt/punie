#!/usr/bin/env bash
# Phase 33b overnight training pipeline — re-run with corrected domain tool APIs
# Fixes Phase 33 audit findings F1+F2: training data now uses real result attributes
# and bare function names (no _direct suffix).
#
# Saves to phase33b paths to distinguish from original Phase 33 run.
# Runs: train → fuse → quantize → eval (direct HTTP eval, 27 prompts)
#
# Usage:
#   bash scripts/run_phase33b_overnight.sh
#   nohup bash scripts/run_phase33b_overnight.sh &

set -euo pipefail

LOGFILE="logs/phase33b_training.log"
BASE_MODEL="mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit"
ADAPTER_PATH="adapters_phase33b"
FUSED_F16="fused_model_qwen3_phase33b_f16"
FUSED_5BIT="fused_model_qwen3_phase33b_5bit"
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
log "Phase 33b Overnight Training Pipeline"
log "Base model: $BASE_MODEL"
log "Data: $DATA (1159 train + 123 valid, corrected APIs)"
log "Adapter output: $ADAPTER_PATH"
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
# STEP 5: Run Phase 33 direct eval (27 prompts, corrected scoring)
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
log "Phase 33b training pipeline COMPLETE"
log "  Total time: ${TOTAL_MINS}m"
log "  Production model: $FUSED_5BIT"
log "  Model size: $(du -sh "$FUSED_5BIT" | cut -f1)"
log "  Eval verdict: $([ $EVAL_EXIT -eq 0 ] && echo 'PASS ✓' || echo 'needs review')"
log "======================================================"
log ""
log "Log: $LOGFILE"
