#!/bin/bash
# Train Phase 27.5 model - "train as hard as you can"
# Increased iterations: 800 (up from 600)
# Warm start from Phase 27 augmented 5-bit model

set -e

echo "================================"
echo "Phase 27.5 Training - Hard Mode"
echo "================================"
echo ""
echo "Base model: fused_model_qwen3_phase27_augmented_5bit/"
echo "Training data: data/phase275_merged/ (1098 train, 122 valid)"
echo "Iterations: 800 (train as hard as possible!)"
echo "Batch size: 1 (maximum precision)"
echo "Learning rate: 1e-4 (optimal)"
echo "Layers: 8 (optimal for tool learning)"
echo ""
echo "Starting training..."
echo ""

uv run python -m mlx_lm.lora --model fused_model_qwen3_phase27_augmented_5bit/ --data data/phase275_merged --train --iters 800 --batch-size 1 --learning-rate 1e-4 --adapter-path adapters_phase275 --num-layers 8 --save-every 200

echo ""
echo "================================"
echo "✅ Training complete!"
echo "Adapters saved to: adapters_phase275/"
echo "================================"
