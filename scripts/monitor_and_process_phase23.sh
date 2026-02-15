#!/usr/bin/env bash
# Monitor Phase 23 training and automatically proceed with fusion + quantization

set -euo pipefail

TRAINING_OUTPUT="/private/tmp/claude-501/-Users-pauleveritt-projects-pauleveritt-punie/tasks/bf30316.output"
CHECK_INTERVAL=30  # seconds

echo "=== Phase 23 Training Monitor ==="
echo "Monitoring: $TRAINING_OUTPUT"
echo "Checking every $CHECK_INTERVAL seconds for completion..."
echo ""

while true; do
    # Check if training has completed (look for final validation loss or "Training complete")
    if grep -q "Iter 500:" "$TRAINING_OUTPUT" 2>/dev/null; then
        echo "✅ Training complete! (Iter 500 reached)"
        break
    fi

    # Show current progress
    LAST_ITER=$(grep "^Iter [0-9]*: Train loss" "$TRAINING_OUTPUT" 2>/dev/null | tail -1 || echo "No progress yet")
    echo "$(date '+%H:%M:%S') - Latest: $LAST_ITER"

    sleep "$CHECK_INTERVAL"
done

echo ""
echo "=== Starting Fusion ===="
./scripts/fuse_phase23.sh

echo ""
echo "=== Starting Quantization ===="
./scripts/quantize_phase23_5bit.sh

echo ""
echo "=== Phase 23 Processing Complete ===="
echo "Model ready at: fused_model_qwen3_phase23_ty_5bit/"
echo ""
echo "Next step: Test with ./scripts/test_phase23_model.py"
