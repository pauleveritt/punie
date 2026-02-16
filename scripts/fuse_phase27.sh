#!/bin/bash
# Fuse Phase 27 adapters to float16

set -e

echo "=== Fusing Phase 27 Adapters to Float16 ==="
echo "This will create a ~57GB float16 model"
echo ""

uv run python -m mlx_lm.fuse \
  --model mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit \
  --adapter-path ./adapters_phase27 \
  --save-path ./fused_model_qwen3_phase27_f16 \
  --dequantize

echo ""
echo "=== Fusion Complete ==="
echo "Model saved to: fused_model_qwen3_phase27_f16/"
echo "Size:"
du -sh fused_model_qwen3_phase27_f16
