#!/bin/bash
# Train Phase 27 augmented model with tool response examples
# This is a warm start from Phase 27 model

set -e

echo "=================================================="
echo "Phase 27 Augmented Training"
echo "=================================================="
echo ""
echo "Base model: fused_model_qwen3_phase27_5bit/"
echo "Training data: data/phase27_augmented/ (1053 train, 111 valid)"
echo "New data: +60 tool response examples"
echo "Strategy: Warm start from Phase 27"
echo "Iterations: 600"
echo "Learning rate: 1e-4"
echo "Batch size: 1"
echo "Layers: 8"
echo ""
echo "Expected training time: ~3-4 hours"
echo "=================================================="
echo ""

# Start training
uv run python -m mlx_lm.lora \
  --model fused_model_qwen3_phase27_5bit/ \
  --data data/phase27_augmented \
  --train \
  --iters 600 \
  --batch-size 1 \
  --learning-rate 1e-4 \
  --adapter-path adapters_phase27_augmented \
  --num-layers 8

echo ""
echo "=================================================="
echo "Training complete!"
echo "=================================================="
echo ""
echo "Adapter saved to: adapters_phase27_augmented/"
echo ""
echo "Next steps:"
echo "1. Fuse: ./scripts/fuse_phase27_augmented.sh"
echo "2. Quantize: ./scripts/quantize_phase27_augmented_5bit.sh"
echo "3. Validate: uv run python scripts/test_phase27_semantic_validation.py <model>"
