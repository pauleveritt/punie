#!/bin/bash
# Train Phase 26 balanced model from scratch
# Dataset: data/phase26_balanced/ (800 examples, 50/50 LSP/non-LSP)
# Base: Qwen2.5-Coder-32B-Instruct-4bit
# Training: 700 iterations (more than before to ensure convergence)

set -e

echo "Training Phase 26 balanced model..."
echo "Data: data/phase26_balanced/ (800 examples, 50/50 split)"
echo "Output: adapters_phase26_balanced/"
echo ""

uv run mlx_lm.lora \
  --model mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit \
  --train \
  --data data/phase26_balanced \
  --adapter-path ./adapters_phase26_balanced \
  --iters 700 \
  --steps-per-eval 50 \
  --steps-per-report 10 \
  --batch-size 1 \
  --learning-rate 1e-4 \
  --num-layers 8

echo ""
echo "✓ Training complete"
echo "✓ Adapters saved to adapters_phase26_balanced/"
