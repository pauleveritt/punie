#!/bin/bash
# Quantize Phase 27.5 model to 5-bit

set -e

echo "=========================================="
echo "Quantizing Phase 27.5 model to 5-bit..."
echo "=========================================="

uv run python -m mlx_lm.convert \
  --hf-path fused_model_qwen3_phase275_f16 \
  --mlx-path fused_model_qwen3_phase275_5bit \
  --quantize \
  --q-bits 5 \
  --q-group-size 64

echo ""
echo "✅ 5-bit model saved to: fused_model_qwen3_phase275_5bit/"
