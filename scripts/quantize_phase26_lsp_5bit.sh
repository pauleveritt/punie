#!/bin/bash
# Quantize Phase 26 LSP model to 5-bit (proven optimal in Phase 26.1)
#
# Input: fused_model_qwen3_phase26_lsp_f16/
# Output: fused_model_qwen3_phase26_lsp_5bit/

set -e

echo "Quantizing Phase 26 LSP model to 5-bit..."
echo "Input: fused_model_qwen3_phase26_lsp_f16/"
echo "Output: fused_model_qwen3_phase26_lsp_5bit/"
echo ""

uv run python -m mlx_lm.convert \
  --hf-path ./fused_model_qwen3_phase26_lsp_f16 \
  --mlx-path ./fused_model_qwen3_phase26_lsp_5bit \
  --quantize \
  --q-bits 5 \
  --q-group-size 64

echo ""
echo "✓ Quantization complete"
echo "5-bit model saved to: fused_model_qwen3_phase26_lsp_5bit/"
echo "Size: ~20 GB"
echo ""
echo "Phase 26.1 validation proved 5-bit is optimal:"
echo "  - 92% accuracy (vs 88% for 6-bit)"
echo "  - 2.53s avg generation time"
echo "  - 19.5 GB size"
