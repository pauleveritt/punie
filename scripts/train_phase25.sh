#!/usr/bin/env bash
# Train Phase 25b: 7B model experiment with Qwen2.5 JSON format (857 examples)
#
# Training parameters:
# - 600 iterations (more data than Phase 23)
# - batch_size 2 (7B fits in memory)
# - learning_rate 1e-4
# - 16 layers (57% coverage for dense model)
# - Model: Qwen2.5-Coder-7B-Instruct-4bit

set -euo pipefail

echo "=== Phase 25b Training: 7B Model with Qwen2.5 JSON Format ==="
echo "Dataset: 857 examples (Qwen2.5 JSON format)"
echo "Testing if 7B can match 30B performance with proper format"
echo ""

# Training parameters
MODEL="mlx-community/Qwen2.5-Coder-7B-Instruct-4bit"
DATA_DIR="data/phase25b_qwen25_format"
OUTPUT_DIR="adapters_phase25b_7b"
ITERS=600
BATCH_SIZE=2
LR="1e-4"
LAYERS=16

echo "Model: $MODEL"
echo "Architecture: Dense 7B (28 layers)"
echo "Data: $DATA_DIR"
echo "Output: $OUTPUT_DIR"
echo "Iterations: $ITERS"
echo "Batch size: $BATCH_SIZE"
echo "Learning rate: $LR"
echo "LoRA layers: $LAYERS (57% coverage)"
echo ""

# Check data directory exists
if [ ! -d "$DATA_DIR" ]; then
    echo "ERROR: Data directory not found at $DATA_DIR"
    echo "Run Phase 24 data generation first"
    exit 1
fi

# Clean output directory if it exists
if [ -d "$OUTPUT_DIR" ]; then
    echo "Removing existing adapter directory..."
    rm -rf "$OUTPUT_DIR"
fi

echo "Starting training..."
echo "Expected time: ~30-40 minutes"
echo ""

# Run training
uv run python -m mlx_lm.lora \
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
echo "1. Fuse adapter: ./scripts/fuse_phase25.sh"
echo "2. Quantize to 6-bit: ./scripts/quantize_phase25.sh"
echo "3. Test: uv run python scripts/test_phase25_model.py fused_model_qwen25_phase25b_7b_6bit"
echo "4. Compare: uv run python scripts/test_phase25_model.py --compare"
