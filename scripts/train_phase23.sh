#!/usr/bin/env bash
# Train Phase 23: Phase 22 (707) + ty examples (50) = 757 total
#
# Training parameters (same as Phase 22):
# - 500 iterations
# - batch_size 1
# - learning_rate 1e-4
# - 8 layers (lora_layers)
# - Model: Qwen3-Coder-30B-A3B-Instruct-4bit

set -euo pipefail

echo "=== Phase 23 Training: Code Mode + ty integration ==="
echo "Dataset: 757 examples (605 train, 75 valid, 77 test)"
echo "Phase 22 (707) + ty (50)"
echo ""

# Training parameters
MODEL="mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit"
DATA_DIR="data/phase23_merged"
OUTPUT_DIR="adapters/phase23_ty"
ITERS=500
BATCH_SIZE=1
LR="1e-4"
LAYERS=8

echo "Model: $MODEL"
echo "Data: $DATA_DIR"
echo "Output: $OUTPUT_DIR"
echo "Iterations: $ITERS"
echo "Batch size: $BATCH_SIZE"
echo "Learning rate: $LR"
echo "LoRA layers: $LAYERS"
echo ""

# Clean output directory if it exists
if [ -d "$OUTPUT_DIR" ]; then
    echo "Removing existing adapter directory..."
    rm -rf "$OUTPUT_DIR"
fi

echo "Starting training..."
echo ""

# Run training
uv run python -m mlx_lm lora \
    --model "$MODEL" \
    --data "$DATA_DIR" \
    --train \
    --iters $ITERS \
    --batch-size $BATCH_SIZE \
    --learning-rate $LR \
    --num-layers $LAYERS \
    --adapter-path "$OUTPUT_DIR"

echo ""
echo "=== Training Complete ==="
echo "Adapter saved to: $OUTPUT_DIR"
echo ""
echo "Next steps:"
echo "1. Fuse adapter: ./scripts/fuse_phase23.sh"
echo "2. Quantize to 5-bit: ./scripts/quantize_phase23_5bit.sh"
echo "3. Validate: ./scripts/test_phase23_model.py"
