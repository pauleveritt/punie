#!/bin/bash
# Fuse Phase 26 contrastive LoRA adapters to base model (dequantize to float16)
#
# Output: fused_model_qwen3_phase26_contrastive_f16/ (~57 GB)
# Next step: quantize_phase26_contrastive_5bit.sh

set -e

echo "Fusing Phase 26 contrastive adapters..."
echo "This will create fused_model_qwen3_phase26_contrastive_f16/ (~57 GB)"
echo ""

uv run python -m mlx_lm.fuse \
  --model mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit \
  --adapter-path ./adapters_phase26_contrastive \
  --save-path ./fused_model_qwen3_phase26_contrastive_f16 \
  --dequantize

echo ""
echo "✓ Fused model saved to: fused_model_qwen3_phase26_contrastive_f16/"
echo "Next: ./scripts/quantize_phase26_contrastive_5bit.sh"
