#!/bin/bash
# Quantize Phase 27 augmented model to 5-bit (optimal from Phase 26 experiments)

set -e

echo "=================================================="
echo "Quantizing Phase 27 Augmented Model (5-bit)"
echo "=================================================="
echo ""
echo "Input: fused_model_qwen3_phase27_augmented_f16/"
echo "Output: fused_model_qwen3_phase27_augmented_5bit/"
echo "Quantization: 5-bit (32 levels, proven optimal in Phase 26)"
echo ""

uv run python -m mlx_lm.convert \
  --hf-path fused_model_qwen3_phase27_augmented_f16 \
  --mlx-path fused_model_qwen3_phase27_augmented_5bit \
  --quantize \
  --q-bits 5 \
  --q-group-size 64

echo ""
echo "✅ Quantized model saved to: fused_model_qwen3_phase27_augmented_5bit/"
echo ""
echo "Model sizes:"
echo "  Float16: $(du -sh fused_model_qwen3_phase27_augmented_f16/ | cut -f1)"
echo "  5-bit: $(du -sh fused_model_qwen3_phase27_augmented_5bit/ | cut -f1)"

echo ""
echo "Next: uv run python scripts/test_phase27_semantic_validation.py fused_model_qwen3_phase27_augmented_5bit/"
