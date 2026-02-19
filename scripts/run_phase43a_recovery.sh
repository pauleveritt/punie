#!/usr/bin/env bash
# Phase 43a Recovery: Re-fuse + re-quantize iter-800 adapter, then eval
#
# Preconditions:
#   - adapters_phase43a/adapters.safetensors  (iter-800 final, DO NOT DELETE)
#   - No existing fused model dirs (they will be created here)
#
# GPU timeout history:
#   Attempt 1: timeout → 9.9 GB (truncated)
#   Attempt 2: OK → 20 GB (eval 38.9%, iter-600 adapter was fused)
#   Attempt 3: timeout → 5.0 GB (truncated)
#
# Fix: sleep 60 between fuse and quantize; integrity check + retry on quantize.
#
# Usage:
#   bash scripts/run_phase43a_recovery.sh
#   nohup bash scripts/run_phase43a_recovery.sh > logs/phase43a_recovery.log 2>&1 &

set -euo pipefail

LOGFILE="logs/phase43a_recovery.log"
BASE_MODEL="mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit"
ADAPTER_PATH="adapters_phase43a"
FUSED_F16="fused_model_qwen3_phase43a_f16"
FUSED_5BIT="fused_model_qwen3_phase43a_coder30b_5bit"
START_TIME=$(date +%s)

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOGFILE"
}

mkdir -p logs

log "======================================================"
log "Phase 43a Recovery — Re-fuse + Re-quantize iter-800 adapter"
log "Adapter: $ADAPTER_PATH/adapters.safetensors"
log "Output: $FUSED_5BIT"
log "======================================================"

# ------------------------------------------------------------------ #
# STEP 0: Preflight
# ------------------------------------------------------------------ #
log ""
log "STEP 0: Preflight"

if [ ! -f "$ADAPTER_PATH/adapters.safetensors" ]; then
    log "ERROR: $ADAPTER_PATH/adapters.safetensors not found — aborting"
    exit 1
fi

ADAPTER_SIZE=$(du -sh "$ADAPTER_PATH/adapters.safetensors" | cut -f1)
log "  Adapter: $ADAPTER_SIZE ✓"
log "  Disk free: $(df -h . | tail -1 | awk '{print $4}')"

# Clean up any stale partial models
if [ -d "$FUSED_F16" ]; then
    log "  Removing stale $FUSED_F16"
    rm -rf "$FUSED_F16"
fi
if [ -d "$FUSED_5BIT" ]; then
    log "  Removing stale $FUSED_5BIT"
    rm -rf "$FUSED_5BIT"
fi

log "  Sleeping 60s for GPU memory to stabilize before fuse"
sleep 60
log "  Preflight done ✓"

# ------------------------------------------------------------------ #
# STEP 1: Fuse adapter → float16
# ------------------------------------------------------------------ #
log ""
log "STEP 1: Fuse adapter → float16 (~10-20 min)"
log "  Output: $FUSED_F16"

FUSE_START=$(date +%s)

uv run python -m mlx_lm fuse \
    --model "$BASE_MODEL" \
    --adapter-path "$ADAPTER_PATH" \
    --save-path "$FUSED_F16" \
    --dequantize \
    2>&1 | tee -a "$LOGFILE"

FUSE_END=$(date +%s)
FUSE_MINS=$(( (FUSE_END - FUSE_START) / 60 ))
log "STEP 1 complete: fuse finished in ${FUSE_MINS}m"

if [ ! -d "$FUSED_F16" ]; then
    log "ERROR: Fused model directory not created: $FUSED_F16"
    exit 1
fi
FUSE_SIZE=$(du -sh "$FUSED_F16" | cut -f1)
log "  Fused model: $FUSED_F16 ($FUSE_SIZE) ✓"

# ------------------------------------------------------------------ #
# STEP 2: Sleep — critical to avoid GPU memory pressure race
# ------------------------------------------------------------------ #
log ""
log "STEP 2: Sleeping 60s to let Metal GPU memory release after fuse"
sleep 60
log "  GPU sleep done ✓"

# ------------------------------------------------------------------ #
# STEP 3: Quantize to 5-bit (with integrity check + one retry)
# ------------------------------------------------------------------ #
log ""
log "STEP 3: Quantize float16 → 5-bit (~10-20 min)"

quantize_and_check() {
    if [ -d "$FUSED_5BIT" ]; then
        log "  Removing existing $FUSED_5BIT"
        rm -rf "$FUSED_5BIT"
    fi

    local QUANT_START
    QUANT_START=$(date +%s)

    uv run python -m mlx_lm convert \
        --hf-path "$FUSED_F16" \
        --mlx-path "$FUSED_5BIT" \
        -q \
        --q-bits 5 \
        --q-group-size 64 \
        2>&1 | tee -a "$LOGFILE"

    local QUANT_END
    QUANT_END=$(date +%s)
    local QUANT_MINS=$(( (QUANT_END - QUANT_START) / 60 ))
    log "  Quantize completed in ${QUANT_MINS}m"

    # Integrity check: must have 4 shards, no 0-byte files, total ≥15 GB
    local SHARD_COUNT
    SHARD_COUNT=$(ls "$FUSED_5BIT"/model-*.safetensors 2>/dev/null | wc -l | tr -d ' ')
    local ZERO_BYTE
    ZERO_BYTE=$(find "$FUSED_5BIT" -name "model-*.safetensors" -empty 2>/dev/null | wc -l | tr -d ' ')
    local TOTAL_KB
    TOTAL_KB=$(du -sk "$FUSED_5BIT" 2>/dev/null | cut -f1)
    local TOTAL_DISPLAY
    TOTAL_DISPLAY=$(du -sh "$FUSED_5BIT" 2>/dev/null | cut -f1)

    log "  Shards: ${SHARD_COUNT}/4 | zero-byte: ${ZERO_BYTE} | size: ${TOTAL_DISPLAY}"

    if [ "${SHARD_COUNT}" -lt 4 ] || [ "${ZERO_BYTE}" -gt 0 ] || [ "${TOTAL_KB}" -lt 15000000 ]; then
        log "  INTEGRITY CHECK FAILED — GPU timeout likely truncated the output"
        return 1
    fi

    log "  Integrity check PASSED ✓"
    return 0
}

# First quantize attempt
if ! quantize_and_check; then
    log "STEP 3: First attempt failed — sleeping 120s then retrying"
    sleep 120
    if ! quantize_and_check; then
        log "ERROR: Quantize integrity check failed after retry — aborting"
        log "  Manual retry: delete $FUSED_5BIT, sleep, re-run this script"
        exit 1
    fi
fi

log "STEP 3 complete ✓"

# ------------------------------------------------------------------ #
# STEP 4: Cleanup float16 model
# ------------------------------------------------------------------ #
log ""
log "STEP 4: Cleaning up float16 model (~57 GB)"
log "  Disk before: $(df -h . | tail -1 | awk '{print $4}') free"
rm -rf "$FUSED_F16"
log "  Removed $FUSED_F16"
log "  Disk after: $(df -h . | tail -1 | awk '{print $4}') free"

# ------------------------------------------------------------------ #
# STEP 5: Run Phase 33 direct eval (27 prompts)
# ------------------------------------------------------------------ #
log ""
log "STEP 5: Running Phase 33 direct eval (27 prompts)"
log "  Model: $FUSED_5BIT"
log "  Target: ≥80% overall (baseline 82.4%)"
log ""
log "  NOTE: Start the mlx_lm server before this step if not already running:"
log "    uv run python -m mlx_lm.server --model $FUSED_5BIT --port 8080"
log ""

EVAL_EXIT=0
uv run python scripts/run_phase33_direct_eval.py \
    --model "$FUSED_5BIT" \
    --port 8080 \
    2>&1 | tee -a "$LOGFILE" || EVAL_EXIT=$?

if [ $EVAL_EXIT -eq 0 ]; then
    log "STEP 5 complete: eval PASSED ✓"
else
    log "STEP 5 complete: eval did not reach ≥80% — review $LOGFILE for category breakdown"
fi

# ------------------------------------------------------------------ #
# DONE
# ------------------------------------------------------------------ #
TOTAL_SECS=$(( $(date +%s) - START_TIME ))
TOTAL_MINS=$(( TOTAL_SECS / 60 ))

log ""
log "======================================================"
log "Phase 43a Recovery COMPLETE"
log "  Total time: ${TOTAL_MINS}m"
log "  Model: $FUSED_5BIT ($(du -sh "$FUSED_5BIT" | cut -f1))"
log "  Eval verdict: $([ $EVAL_EXIT -eq 0 ] && echo 'PASS ✓' || echo 'FAIL — check log')"
log "  Log: $LOGFILE"
log "======================================================"
