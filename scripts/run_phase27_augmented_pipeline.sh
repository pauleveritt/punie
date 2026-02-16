#!/bin/bash
# Master pipeline for Phase 27 augmented training
# Runs: train → fuse → quantize → validate

set -e

LOG_FILE="logs/phase27_augmented_pipeline_$(date +%Y%m%d_%H%M%S).log"
mkdir -p logs

echo "=================================================="
echo "Phase 27 Augmented Pipeline"
echo "=================================================="
echo ""
echo "This will run the complete pipeline:"
echo "1. Train with tool response examples (600 iters, ~3-4 hours)"
echo "2. Fuse to float16 (~5 minutes)"
echo "3. Quantize to 5-bit (~5 minutes)"
echo "4. Run semantic validation (~5 minutes)"
echo ""
echo "Total estimated time: ~4 hours"
echo "Log file: $LOG_FILE"
echo ""
echo "=================================================="
echo ""

# Redirect all output to log and console
exec > >(tee -a "$LOG_FILE") 2>&1

START_TIME=$(date +%s)

echo "[$(date)] Step 1/4: Training model..."
./scripts/train_phase27_augmented.sh

echo ""
echo "[$(date)] Step 2/4: Fusing to float16..."
./scripts/fuse_phase27_augmented.sh

echo ""
echo "[$(date)] Step 3/4: Quantizing to 5-bit..."
./scripts/quantize_phase27_augmented_5bit.sh

echo ""
echo "[$(date)] Step 4/4: Running semantic validation..."
uv run python scripts/test_phase27_semantic_validation.py fused_model_qwen3_phase27_augmented_5bit/

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
HOURS=$((DURATION / 3600))
MINUTES=$(((DURATION % 3600) / 60))

echo ""
echo "=================================================="
echo "Pipeline Complete!"
echo "=================================================="
echo ""
echo "Total time: ${HOURS}h ${MINUTES}m"
echo "Log file: $LOG_FILE"
echo ""
echo "Model locations:"
echo "  - Adapters: adapters_phase27_augmented/"
echo "  - Float16: fused_model_qwen3_phase27_augmented_f16/"
echo "  - 5-bit (production): fused_model_qwen3_phase27_augmented_5bit/"
echo ""
echo "Next steps:"
echo "  - Review validation results above"
echo "  - Deploy: fused_model_qwen3_phase27_augmented_5bit/"
echo "  - Compare with baseline: fused_model_qwen3_phase27_5bit/"
