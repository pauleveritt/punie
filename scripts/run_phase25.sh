#!/usr/bin/env bash
# Phase 25b: Complete pipeline (train → fuse → quantize → test → compare)

set -euo pipefail

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="logs/phase25b_pipeline_${TIMESTAMP}.log"

# Create logs directory
mkdir -p logs

echo "==================================================================="
echo "Phase 25b: 7B Model with Qwen2.5 JSON Format"
echo "==================================================================="
echo ""
echo "This will:"
echo "  1. Train 7B model with Qwen2.5 JSON format (857 examples)"
echo "  2. Fuse adapter to float16"
echo "  3. Quantize to 6-bit"
echo "  4. Test with 20-query suite"
echo "  5. Compare 7B vs 30B"
echo ""
echo "Expected time: ~1 hour total"
echo "  - Training: ~30-40 minutes"
echo "  - Fusion: ~5 minutes"
echo "  - Quantization: ~2 minutes"
echo "  - Testing: ~15 minutes"
echo ""
echo "Logging to: $LOG_FILE"
echo ""
echo "==================================================================="
echo ""

# Redirect all output to log file and terminal
exec > >(tee "$LOG_FILE") 2>&1

START_TIME=$(date +%s)

# Step 1: Train
echo ""
echo "==================================================================="
echo "STEP 1/5: Training 7B model"
echo "==================================================================="
echo ""

if [ ! -f scripts/train_phase25.sh ]; then
    echo "ERROR: scripts/train_phase25.sh not found"
    exit 1
fi

chmod +x scripts/train_phase25.sh
./scripts/train_phase25.sh

TRAIN_END=$(date +%s)
TRAIN_TIME=$((TRAIN_END - START_TIME))
echo ""
echo "✓ Training complete in ${TRAIN_TIME}s"

# Step 2: Fuse
echo ""
echo "==================================================================="
echo "STEP 2/5: Fusing adapter to float16"
echo "==================================================================="
echo ""

if [ ! -f scripts/fuse_phase25.sh ]; then
    echo "ERROR: scripts/fuse_phase25.sh not found"
    exit 1
fi

chmod +x scripts/fuse_phase25.sh
./scripts/fuse_phase25.sh

FUSE_END=$(date +%s)
FUSE_TIME=$((FUSE_END - TRAIN_END))
echo ""
echo "✓ Fusion complete in ${FUSE_TIME}s"

# Step 3: Quantize
echo ""
echo "==================================================================="
echo "STEP 3/5: Quantizing to 6-bit"
echo "==================================================================="
echo ""

if [ ! -f scripts/quantize_phase25.sh ]; then
    echo "ERROR: scripts/quantize_phase25.sh not found"
    exit 1
fi

chmod +x scripts/quantize_phase25.sh
./scripts/quantize_phase25.sh

QUANT_END=$(date +%s)
QUANT_TIME=$((QUANT_END - FUSE_END))
echo ""
echo "✓ Quantization complete in ${QUANT_TIME}s"

# Step 4: Test 7B
echo ""
echo "==================================================================="
echo "STEP 4/5: Testing 7B model"
echo "==================================================================="
echo ""

uv run python scripts/test_phase25_model.py fused_model_qwen25_phase25b_7b_6bit

TEST_END=$(date +%s)
TEST_TIME=$((TEST_END - QUANT_END))
echo ""
echo "✓ Testing complete in ${TEST_TIME}s"

# Step 5: Compare
echo ""
echo "==================================================================="
echo "STEP 5/5: Comparing 7B vs 30B"
echo "==================================================================="
echo ""

# Check if 30B model exists
if [ ! -d "fused_model_qwen3_phase23_ty_5bit" ]; then
    echo "⚠️  WARNING: 30B baseline model not found"
    echo "Skipping comparison. Run Phase 23 first to get baseline."
else
    uv run python scripts/test_phase25_model.py --compare

    COMPARE_END=$(date +%s)
    COMPARE_TIME=$((COMPARE_END - TEST_END))
    echo ""
    echo "✓ Comparison complete in ${COMPARE_TIME}s"
fi

# Summary
END_TIME=$(date +%s)
TOTAL_TIME=$((END_TIME - START_TIME))
TOTAL_MINUTES=$((TOTAL_TIME / 60))

echo ""
echo "==================================================================="
echo "PIPELINE COMPLETE"
echo "==================================================================="
echo ""
echo "Timing breakdown:"
echo "  Training:      ${TRAIN_TIME}s"
echo "  Fusion:        ${FUSE_TIME}s"
echo "  Quantization:  ${QUANT_TIME}s"
echo "  Testing:       ${TEST_TIME}s"
if [ -d "fused_model_qwen3_phase23_ty_5bit" ]; then
    echo "  Comparison:    ${COMPARE_TIME}s"
fi
echo "  -------------------------"
echo "  Total:         ${TOTAL_TIME}s (~${TOTAL_MINUTES} minutes)"
echo ""
echo "Artifacts created:"
echo "  - adapters_phase25b_7b/"
echo "  - fused_model_qwen25_phase25b_7b_f16/"
echo "  - fused_model_qwen25_phase25b_7b_6bit/"
echo "  - logs/fused_model_qwen25_phase25b_7b_6bit_results.json"
if [ -d "fused_model_qwen3_phase23_ty_5bit" ]; then
    echo "  - logs/phase25b_comparison.json"
fi
echo ""
echo "Log saved to: $LOG_FILE"
echo ""
echo "==================================================================="
