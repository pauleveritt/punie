#!/bin/bash
# Fine-tune 7B model with LoRA using training data from 30B
#
# Prerequisites:
# - data/training_examples_1k.jsonl exists and validated
# - MLX installed (uv should handle this)
# - M1/M2 Mac with 32GB RAM
#
# Expected time: 6-8 hours overnight
# Expected RAM: 16-20GB peak

set -e  # Exit on error

echo "========================================================================"
echo "LORA FINE-TUNING: 7B Model with 30B Knowledge"
echo "========================================================================"
echo ""

# Configuration
MODEL="mlx-community/Qwen2.5-Coder-7B-Instruct-4bit"
TRAINING_DATA="data/training_examples_1k.jsonl"
OUTPUT_DIR="models/qwen25-7b-distilled"
BATCH_SIZE=2
LEARNING_RATE=1e-4
LORA_RANK=16
EPOCHS=3

# Validate inputs
if [ ! -f "$TRAINING_DATA" ]; then
    echo "❌ Error: Training data not found at $TRAINING_DATA"
    echo "   Run scripts/generate_training_data.py first"
    exit 1
fi

EXAMPLE_COUNT=$(wc -l < "$TRAINING_DATA")
echo "Training data: $TRAINING_DATA"
echo "Examples: $EXAMPLE_COUNT"
echo ""

if [ "$EXAMPLE_COUNT" -lt 50 ]; then
    echo "⚠️  Warning: Only $EXAMPLE_COUNT examples. Recommended: 100+"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Convert training data to MLX format
echo ""
echo "Converting training data to MLX format..."
python3 scripts/convert_training_data.py
if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to convert training data"
    exit 1
fi

# Update training data path to use converted format
TRAINING_DATA="data/mlx_format"
echo "✅ Training data converted to $TRAINING_DATA"
echo ""

# Create output directory
mkdir -p "$OUTPUT_DIR"

echo "Configuration:"
echo "  Model: $MODEL"
echo "  Batch size: $BATCH_SIZE"
echo "  Learning rate: $LEARNING_RATE"
echo "  LoRA rank: $LORA_RANK"
echo "  Epochs: $EPOCHS"
echo "  Output: $OUTPUT_DIR"
echo ""

# Calculate iterations
TOTAL_ITERATIONS=$((EXAMPLE_COUNT * EPOCHS / BATCH_SIZE))
echo "Estimated iterations: $TOTAL_ITERATIONS"
echo "Estimated time: 6-8 hours"
echo ""

read -p "Start training? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Training cancelled"
    exit 0
fi

echo ""
echo "========================================================================"
echo "Starting LoRA Training"
echo "========================================================================"
echo ""

# Run training
uv run python -m mlx_lm.lora \
    --model "$MODEL" \
    --train \
    --data "$TRAINING_DATA" \
    --iters "$TOTAL_ITERATIONS" \
    --batch-size "$BATCH_SIZE" \
    --learning-rate "$LEARNING_RATE" \
    --num-layers 16 \
    --adapter-path "$OUTPUT_DIR/adapters" \
    --save-every 100 \
    --val-batches 5 \
    --test

echo ""
echo "========================================================================"
echo "Training Complete!"
echo "========================================================================"
echo ""
echo "Adapter saved to: $OUTPUT_DIR/adapters"
echo ""
echo "Next steps:"
echo "  1. Run scripts/evaluate_distilled_model.py"
echo "  2. Compare to 30B baseline"
echo "  3. If >80% success, deploy to production!"
echo ""
