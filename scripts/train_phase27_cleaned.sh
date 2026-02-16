#!/bin/bash
# Train Phase 27 Cleaned model (preambles removed)
# Expected: 4-6 hours on M1/M2 Mac

set -e

echo "Training Phase 27 Cleaned (no preambles)"
echo "========================================"
echo ""

MODEL="mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit"
DATA="data/phase27_cleaned"
OUTPUT="adapters_phase27_cleaned"
ITERS=800
BATCH=1
LR=1e-4
LAYERS=8

echo "Model: $MODEL"
echo "Data: $DATA"
echo "Output: $OUTPUT"
echo "Iterations: $ITERS"
echo "Batch size: $BATCH"
echo "Learning rate: $LR"
echo "Layers to train: $LAYERS"
echo ""

uv run python -m mlx_lm.lora \
  --model "$MODEL" \
  --train \
  --data "$DATA" \
  --adapter-path "$OUTPUT" \
  --iters "$ITERS" \
  --batch-size "$BATCH" \
  --learning-rate "$LR" \
  --num-layers "$LAYERS" \
  --save-every 200

echo ""
echo "✅ Training complete!"
echo "Adapter saved to: $OUTPUT"
echo ""
echo "Next: Fuse and quantize the model"
echo "  ./scripts/fuse_phase27_cleaned.sh"
