#!/bin/bash
# Fuse Phase 27 augmented adapters to float16

set -e

echo "=================================================="
echo "Fusing Phase 27 Augmented Model (float16)"
echo "=================================================="
echo ""
echo "Base model: fused_model_qwen3_phase27_5bit/"
echo "Adapter: adapters_phase27_augmented/"
echo "Output: fused_model_qwen3_phase27_augmented_f16/"
echo ""

uv run python -m mlx_lm.fuse \
  --model fused_model_qwen3_phase27_5bit/ \
  --adapter-path adapters_phase27_augmented \
  --save-path fused_model_qwen3_phase27_augmented_f16 \
  --dequantize

echo ""
echo "✅ Fused model saved to: fused_model_qwen3_phase27_augmented_f16/"
echo ""
echo "Model size:"
du -sh fused_model_qwen3_phase27_augmented_f16/

echo ""
echo "Next: ./scripts/quantize_phase27_augmented_5bit.sh"
