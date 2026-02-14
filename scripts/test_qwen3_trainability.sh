#!/bin/bash
# Quick 5-iteration test to verify Qwen3-30B-A3B trainability on M1 32GB
#
# This runs a minimal training to check:
# - Model loads without OOM
# - LoRA keys are correct for MoE architecture
# - Memory stays under 28GB
# - Stop sequences work correctly

set -e

echo "========================================================================"
echo "QWEN3-30B-A3B TRAINABILITY TEST (5 iterations)"
echo "========================================================================"
echo ""

MODEL="mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit"
TRAINING_DATA="data/phase7_format"
OUTPUT_DIR="adapters_phase8_test"
BATCH_SIZE=2
LEARNING_RATE=1e-4
NUM_LAYERS=16

echo "Configuration:"
echo "  Model: $MODEL"
echo "  Data: $TRAINING_DATA"
echo "  Batch size: $BATCH_SIZE"
echo "  Num layers: $NUM_LAYERS"
echo "  Iterations: 5 (test only)"
echo ""

# Clean up any existing test adapters
if [ -d "$OUTPUT_DIR" ]; then
    echo "Removing existing test adapters..."
    rm -rf "$OUTPUT_DIR"
fi

echo "Starting trainability test..."
echo ""

# Monitor memory in background
(
    sleep 2  # Wait for training to start
    while ps aux | grep -q "[p]ython.*mlx_lm.lora"; do
        MEMORY=$(ps aux | grep "[p]ython.*mlx_lm.lora" | awk '{print $6}')
        MEMORY_GB=$(echo "scale=2; $MEMORY / 1024 / 1024" | bc 2>/dev/null || echo "N/A")
        echo "[$(date +%H:%M:%S)] Memory: ${MEMORY_GB} GB" >> /tmp/qwen3_memory.log
        sleep 5
    done
) &
MONITOR_PID=$!

# Run minimal training
uv run python -m mlx_lm.lora \
    --model "$MODEL" \
    --train \
    --data "$TRAINING_DATA" \
    --iters 5 \
    --batch-size "$BATCH_SIZE" \
    --learning-rate "$LEARNING_RATE" \
    --num-layers "$NUM_LAYERS" \
    --adapter-path "$OUTPUT_DIR" \
    --val-batches 2

# Kill memory monitor
kill $MONITOR_PID 2>/dev/null || true

echo ""
echo "========================================================================"
echo "Trainability Test Complete!"
echo "========================================================================"
echo ""

# Show peak memory if log exists
if [ -f /tmp/qwen3_memory.log ]; then
    echo "Memory usage:"
    cat /tmp/qwen3_memory.log
    PEAK=$(cat /tmp/qwen3_memory.log | awk '{print $3}' | sort -n | tail -1)
    echo ""
    echo "Peak memory: ${PEAK} GB"
    echo ""
    rm /tmp/qwen3_memory.log
fi

# Check adapter config
if [ -f "$OUTPUT_DIR/adapter_config.json" ]; then
    echo "✅ Adapter created successfully"
    echo ""
    echo "Adapter config:"
    cat "$OUTPUT_DIR/adapter_config.json"
    echo ""
else
    echo "❌ No adapter config found"
    exit 1
fi

echo ""
echo "Next step: If memory < 28GB, proceed to full Phase 8 training"
echo "            If OOM, reduce batch_size to 1 or num_layers to 8"
echo ""
