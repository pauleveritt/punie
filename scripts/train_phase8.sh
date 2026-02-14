#!/bin/bash
# Train Phase 8 adapter with Qwen3-Coder-30B-A3B-Instruct-4bit
#
# Configuration based on:
# - Phase 7 success (500 iters, batch_size 2, lr 1e-4)
# - Phase 8 domain-pruned data (683 examples, 70/30 split)
# - M1 Max 32GB memory (verified 22.9GB peak)

set -e

echo "========================================================================"
echo "PHASE 8: Qwen3-30B-A3B Training"
echo "========================================================================"
echo ""

MODEL="mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit"
TRAINING_DATA="data/phase8_format"
OUTPUT_DIR="adapters_phase8"
BATCH_SIZE=1  # Reduced from 2 due to OOM
LEARNING_RATE=1e-4
NUM_LAYERS=8  # Reduced from 16 due to OOM
ITERATIONS=500

echo "Configuration:"
echo "  Model: $MODEL"
echo "  Data: $TRAINING_DATA"
echo "  Batch size: $BATCH_SIZE"
echo "  Learning rate: $LEARNING_RATE"
echo "  Num layers: $NUM_LAYERS"
echo "  Iterations: $ITERATIONS"
echo ""

# Validate data
if [ ! -f "$TRAINING_DATA/train.jsonl" ]; then
    echo "❌ Error: Training data not found at $TRAINING_DATA/train.jsonl"
    echo "   Run scripts/generate_phase8_data.py first"
    exit 1
fi

TRAIN_COUNT=$(wc -l < "$TRAINING_DATA/train.jsonl")
VALID_COUNT=$(wc -l < "$TRAINING_DATA/valid.jsonl")
echo "Training examples: $TRAIN_COUNT"
echo "Validation examples: $VALID_COUNT"
echo ""

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Log file
LOG_FILE="logs/phase8_training_$(date +%Y%m%d_%H%M%S).log"
mkdir -p logs

echo "Starting training at $(date)"
echo "Log file: $LOG_FILE"
echo ""
echo "Estimated time: ~50 minutes (batch_size=1 is slower)"
echo "Expected peak memory: ~18-20GB (reduced from 26GB with batch_size=2, num_layers=16)"
echo ""

# Run training with tee to show output and save to log
uv run python -m mlx_lm.lora \
    --model "$MODEL" \
    --train \
    --data "$TRAINING_DATA" \
    --iters "$ITERATIONS" \
    --batch-size "$BATCH_SIZE" \
    --learning-rate "$LEARNING_RATE" \
    --num-layers "$NUM_LAYERS" \
    --adapter-path "$OUTPUT_DIR" \
    --save-every 250 \
    --val-batches 10 \
    --test 2>&1 | tee "$LOG_FILE"

echo ""
echo "========================================================================"
echo "Phase 8 Training Complete!"
echo "========================================================================"
echo ""
echo "Finished at $(date)"
echo "Adapter saved to: $OUTPUT_DIR/"
echo "Log saved to: $LOG_FILE"
echo ""

# Show final metrics
echo "Final training metrics:"
tail -20 "$LOG_FILE" | grep -E "(loss|mem)" || echo "Check log file for details"
echo ""

echo "Next steps:"
echo "  1. Review training log: cat $LOG_FILE"
echo "  2. Run benchmark: python scripts/benchmark_phase8.py"
echo "  3. If successful, fuse to 8-bit: scripts/fuse_phase8.sh"
echo ""
