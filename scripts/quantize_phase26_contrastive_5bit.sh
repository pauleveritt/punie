#!/bin/bash
# Quantize Phase 26 contrastive fused model to 5-bit
#
# Input: fused_model_qwen3_phase26_contrastive_f16/ (~57 GB)
# Output: fused_model_qwen3_phase26_contrastive_5bit/ (~20 GB)
# Compression: 65% reduction (57 GB → 20 GB)

set -e

if [ ! -d "fused_model_qwen3_phase26_contrastive_f16" ]; then
  echo "Error: fused_model_qwen3_phase26_contrastive_f16/ not found"
  echo "Run ./scripts/fuse_phase26_contrastive.sh first"
  exit 1
fi

echo "Quantizing to 5-bit..."
echo "This will create fused_model_qwen3_phase26_contrastive_5bit/ (~20 GB)"
echo ""

uv run python -m mlx_lm.convert \
  --hf-path ./fused_model_qwen3_phase26_contrastive_f16 \
  --mlx-path ./fused_model_qwen3_phase26_contrastive_5bit \
  --quantize \
  --q-bits 5

echo ""
echo "✓ Quantized model saved to: fused_model_qwen3_phase26_contrastive_5bit/"
echo "✓ 5-bit quantization (proven optimal for LoRA in Phase 26.1)"
echo ""
echo "Next: Test with LSP validation suite"
echo "  uv run python scripts/test_phase26_lsp_validation.py fused_model_qwen3_phase26_contrastive_5bit"
