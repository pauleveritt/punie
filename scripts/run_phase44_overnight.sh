#!/usr/bin/env bash
# Phase 44 overnight autonomous analysis — runs without user intervention.
#
# What this does:
#   1. Waits for Phase 44 eval JSON to appear (training pipeline must already be running)
#   2. Re-runs the Phase 44 eval with a clean server (in case the pipeline eval was blocked)
#   3. Runs deep-dive analysis: methodology audit, think-mode probe, consistency check,
#      performance benchmark (Phase 44 + Phase 33b comparison), writes markdown report
#   4. Writes summary to logs/phase44_overnight.log
#
# Usage:
#   nohup bash scripts/run_phase44_overnight.sh > logs/phase44_overnight.log 2>&1 &
#
# Prerequisites: Phase 44 training pipeline must have been started with:
#   bash scripts/run_phase44_format_fix.sh

set -euo pipefail

LOGFILE="logs/phase44_overnight.log"
MODEL="fused_model_qwen3_phase44_format_fix_5bit"
PROD_MODEL="fused_model_qwen3_phase33b_5bit"
EVAL_SCRIPT="scripts/run_phase33_direct_eval.py"
DIVE_SCRIPT="scripts/phase44_deep_dive.py"
MAX_WAIT_HOURS=6
START_TIME=$(date +%s)

mkdir -p logs

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOGFILE"
}

log "======================================================"
log "Phase 44 Overnight Analysis — starting"
log "Target model:    $MODEL"
log "Production comp: $PROD_MODEL"
log "Max wait:        ${MAX_WAIT_HOURS}h for model to appear"
log "======================================================"

# ------------------------------------------------------------------ #
# STEP 0: Wait for Phase 44 model to be ready
# ------------------------------------------------------------------ #
log ""
log "STEP 0: Waiting for $MODEL to be ready"

DEADLINE=$(( START_TIME + MAX_WAIT_HOURS * 3600 ))
while true; do
    if [ "$(ls "$MODEL"/model-*.safetensors 2>/dev/null | wc -l | tr -d ' ')" -ge 4 ]; then
        MODEL_SIZE=$(du -sh "$MODEL" | cut -f1)
        log "  Model ready: $MODEL ($MODEL_SIZE) ✓"
        break
    fi

    NOW=$(date +%s)
    if [ "$NOW" -ge "$DEADLINE" ]; then
        log "ERROR: Timed out after ${MAX_WAIT_HOURS}h waiting for $MODEL"
        exit 1
    fi

    log "  Not ready yet — sleeping 60s (waited $(( (NOW - START_TIME) / 60 ))m)"
    sleep 60
done

# ------------------------------------------------------------------ #
# STEP 1: Kill any lingering servers on port 8080
# ------------------------------------------------------------------ #
log ""
log "STEP 1: Clearing port 8080"
pkill -9 -f "mlx_lm.*server" 2>/dev/null || true
sleep 5
if lsof -iTCP:8080 -sTCP:LISTEN 2>/dev/null | grep -q LISTEN; then
    log "  WARNING: Port 8080 still in use — eval may fail"
else
    log "  Port 8080 clear ✓"
fi

# ------------------------------------------------------------------ #
# STEP 2: Run Phase 44 eval (fresh server)
# ------------------------------------------------------------------ #
log ""
log "STEP 2: Running Phase 44 eval (27 prompts)"

EVAL_EXIT=0
uv run python "$EVAL_SCRIPT" \
    --model "$MODEL" \
    --port 8080 \
    2>&1 | tee -a "$LOGFILE" || EVAL_EXIT=${PIPESTATUS[0]}

if [ $EVAL_EXIT -eq 0 ]; then
    log "  Eval PASSED ✓"
else
    log "  Eval did not reach ≥80% — continuing with deep dive"
fi

# ------------------------------------------------------------------ #
# STEP 3: Run deep-dive analysis
# ------------------------------------------------------------------ #
log ""
log "STEP 3: Running deep-dive analysis"

sleep 10  # Let GPU memory settle after eval server shutdown

DIVE_ARGS="--phase44-model $MODEL"
if [ -d "$PROD_MODEL" ]; then
    DIVE_ARGS="$DIVE_ARGS --phase33b-model $PROD_MODEL"
    log "  Will benchmark Phase 33b for comparison ✓"
else
    log "  Phase 33b model not found — skipping comparison"
fi

DIVE_EXIT=0
uv run python "$DIVE_SCRIPT" $DIVE_ARGS \
    2>&1 | tee -a "$LOGFILE" || DIVE_EXIT=${PIPESTATUS[0]}

if [ $DIVE_EXIT -eq 0 ]; then
    log "  Deep dive completed ✓"
else
    log "  Deep dive encountered issues — check $LOGFILE"
fi

# ------------------------------------------------------------------ #
# DONE
# ------------------------------------------------------------------ #
TOTAL_MINS=$(( ($(date +%s) - START_TIME) / 60 ))
log ""
log "======================================================"
log "Phase 44 Overnight Analysis COMPLETE"
log "  Total time:   ${TOTAL_MINS}m"
log "  Eval verdict: $([ $EVAL_EXIT -eq 0 ] && echo 'PASS ✓' || echo 'needs review')"
log "  Deep dive:    $([ $DIVE_EXIT -eq 0 ] && echo 'PASS ✓' || echo 'check log')"
log "  Report:       docs/research/phase44-deep-dive.md"
log "  Log:          $LOGFILE"
log "======================================================"
