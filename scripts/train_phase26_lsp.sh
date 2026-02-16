#!/bin/bash
# Train Phase 26 LSP navigation model
#
# Settings: 500 iters, batch 1, lr 1e-4, 8 layers
# Input: data/phase26_lsp_final/
# Output: adapters_phase26_lsp/

set -e

echo "Training Phase 26 LSP model..."
echo "Data: data/phase26_lsp_final/ (1023 examples)"
echo "Output: adapters_phase26_lsp/"
echo ""

uv run mlx_lm.lora \
  --model mlx-community/Qwen2.5-Coder-32B-Instruct-4bit \
  --train \
  --data data/phase26_lsp_final \
  --adapter-path ./adapters_phase26_lsp \
  --iters 500 \
  --steps-per-eval 50 \
  --steps-per-report 10 \
  --batch-size 1 \
  --learning-rate 1e-4 \
  --num-layers 8

echo ""
echo "✓ Training complete"
echo "Adapters saved to: adapters_phase26_lsp/"
