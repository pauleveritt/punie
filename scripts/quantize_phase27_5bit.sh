#!/bin/bash
# Quantize Phase 27 float16 model to 5-bit

set -e

echo "=== Quantizing Phase 27 Model to 5-bit ==="
echo "This will create a ~20GB 5-bit model"
echo ""

uv run python -m mlx_lm.convert \
  --hf-path ./fused_model_qwen3_phase27_f16 \
  --mlx-path ./fused_model_qwen3_phase27_5bit \
  --quantize \
  --q-bits 5

echo ""
echo "=== Quantization Complete ==="
echo "Model saved to: fused_model_qwen3_phase27_5bit/"
echo "Size:"
du -sh fused_model_qwen3_phase27_5bit

echo ""
echo "=== Cleaning up float16 intermediate ==="
rm -rf fused_model_qwen3_phase27_f16
echo "Removed fused_model_qwen3_phase27_f16/"
