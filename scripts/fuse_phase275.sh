#!/bin/bash
# Fuse Phase 27.5 adapters to float16

set -e

echo "========================================="
echo "Fusing Phase 27.5 adapters to float16..."
echo "========================================="

uv run python -m mlx_lm.fuse \
  --model fused_model_qwen3_phase27_augmented_5bit/ \
  --adapter-path adapters_phase275 \
  --save-path fused_model_qwen3_phase275_f16 \
  --dequantize

echo ""
echo "✅ Fused model saved to: fused_model_qwen3_phase275_f16/"
