#!/bin/bash
# Train Phase 26 model with field access patterns
#
# Configuration:
# - Model: Qwen3-Coder-30B-A3B-Instruct-4bit
# - Data: Phase 26 merged (953 examples with field access)
# - Iterations: 500 (proven sufficient in Phase 23)
# - Batch size: 1 (stable memory usage)
# - Learning rate: 1e-4 (standard)
# - LoRA layers: 8 (balance between quality and training time)

set -e  # Exit on error

echo "============================================================"
echo "Phase 26 Training: Field Access Patterns"
echo "============================================================"
echo ""

# Check if data directory exists
if [ ! -d "data/phase26_merged" ]; then
    echo "Error: data/phase26_merged directory not found"
    echo "Run scripts/merge_phase26_data.py first"
    exit 1
fi

# Count examples
train_count=$(wc -l < data/phase26_merged/train.jsonl)
valid_count=$(wc -l < data/phase26_merged/valid.jsonl)
test_count=$(wc -l < data/phase26_merged/test.jsonl)
total_count=$((train_count + valid_count + test_count))

echo "Training data:"
echo "  Train: $train_count examples"
echo "  Valid: $valid_count examples"
echo "  Test: $test_count examples"
echo "  Total: $total_count examples"
echo ""

echo "Training configuration:"
echo "  Model: mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit"
echo "  Iterations: 500"
echo "  Batch size: 1"
echo "  Learning rate: 1e-4"
echo "  LoRA layers: 8"
echo ""

echo "Starting training..."
echo ""

# Run training
uv run python -m mlx_lm.lora \
  --model mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit \
  --data data/phase26_merged \
  --train \
  --iters 500 \
  --batch-size 1 \
  --learning-rate 1e-4 \
  --num-layers 8 \
  --adapter-path ./adapters_phase26

echo ""
echo "============================================================"
echo "Training complete!"
echo "Adapter saved to: ./adapters_phase26"
echo "============================================================"
