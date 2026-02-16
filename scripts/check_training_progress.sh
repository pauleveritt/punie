#!/bin/bash
# Check Phase 27.5 training progress

echo "==================================="
echo "Phase 27.5 Training Status Check"
echo "==================================="
echo ""

# Check if training is running
if ps aux | grep -v grep | grep "mlx_lm.lora" > /dev/null; then
    echo "✅ Training process is ACTIVE"
    ps aux | grep -v grep | grep "mlx_lm.lora" | head -1 | awk '{printf "   PID: %s | CPU: %s%% | Mem: %s%% | Runtime: %s\n", $2, $3, $4, $10}'
    echo ""
else
    echo "❌ Training process not found"
    echo ""
    exit 1
fi

# Check for checkpoints
echo "Checkpoint Status:"
if ls adapters_phase275/*.safetensors > /dev/null 2>&1; then
    echo "   Found checkpoints:"
    ls -lh adapters_phase275/*.safetensors | awk '{print "   -", $9, "("$5")"}'

    # Estimate iteration from checkpoint count
    CHECKPOINT_COUNT=$(ls adapters_phase275/*.safetensors 2>/dev/null | wc -l | xargs)
    ESTIMATED_ITER=$((CHECKPOINT_COUNT * 200))
    echo ""
    echo "   Estimated progress: ~${ESTIMATED_ITER}/800 iterations (${CHECKPOINT_COUNT}/4 checkpoints)"
else
    echo "   No checkpoints yet (waiting for iteration 200)"
fi

echo ""
echo "==================================="
echo "Training is progressing normally!"
echo "First checkpoint will appear at iteration 200"
echo "==================================="
