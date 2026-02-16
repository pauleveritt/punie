#!/bin/bash
# Master pipeline: Train Phase 27.5, fuse, quantize, validate
# User command: "train as hard as you can"

set -e

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="logs/phase275_pipeline_${TIMESTAMP}.log"

mkdir -p logs

echo "🚀 Phase 27.5 Pipeline - Training Hard Mode"
echo "==========================================="
echo ""
echo "Log file: ${LOG_FILE}"
echo "Started at: $(date)"
echo ""

# Run pipeline and log everything
{
  echo "PHASE 27.5 PIPELINE - TRAINING HARD MODE"
  echo "========================================"
  echo "Started: $(date)"
  echo ""

  # Step 1: Train (800 iterations, batch 1, lr 1e-4, 8 layers)
  echo "Step 1: Training (800 iterations)..."
  ./scripts/train_phase275.sh
  echo ""

  # Step 2: Fuse to float16
  echo "Step 2: Fusing to float16..."
  ./scripts/fuse_phase275.sh
  echo ""

  # Step 3: Quantize to 5-bit
  echo "Step 3: Quantizing to 5-bit..."
  ./scripts/quantize_phase275_5bit.sh
  echo ""

  # Step 4: Semantic validation
  echo "Step 4: Running semantic validation..."
  uv run python scripts/test_phase27_semantic_validation.py fused_model_qwen3_phase275_5bit/
  echo ""

  echo "========================================"
  echo "✅ PIPELINE COMPLETE!"
  echo "Completed: $(date)"
  echo ""
  echo "Production model: fused_model_qwen3_phase275_5bit/"
  echo "Adapters: adapters_phase275/"
  echo "Log: ${LOG_FILE}"
  echo "========================================"

} 2>&1 | tee "${LOG_FILE}"

echo ""
echo "✅ Full pipeline complete! Check ${LOG_FILE} for details."
