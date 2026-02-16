#!/bin/bash
# Quantize Phase 26 model to 6-bit
#
# 6-bit quantization (64 levels) preserves LoRA signal while reducing size by 23%
# compared to 8-bit (Phase 8 discovery)

set -e  # Exit on error

echo "============================================================"
echo "Phase 26 Quantization: 6-bit"
echo "============================================================"
echo ""

# Check if fused model exists
if [ ! -d "fused_model_qwen3_phase26_f16" ]; then
    echo "Error: fused_model_qwen3_phase26_f16 directory not found"
    echo "Run scripts/fuse_phase26.sh first"
    exit 1
fi

echo "Quantizing float16 model to 6-bit..."
echo "  Input: ./fused_model_qwen3_phase26_f16 (~57 GB)"
echo "  Output: ./fused_model_qwen3_phase26_6bit (~23 GB)"
echo "  Quantization: 6-bit (64 levels)"
echo ""

# Run quantization
uv run python -m mlx_lm.convert \
  --hf-path ./fused_model_qwen3_phase26_f16 \
  --mlx-path ./fused_model_qwen3_phase26_6bit \
  --quantize \
  --q-bits 6

echo ""
echo "============================================================"
echo "Quantization complete!"
echo "6-bit model saved to: ./fused_model_qwen3_phase26_6bit"
echo "Size: ~23 GB"
echo ""
echo "✓ Ready for production use"
echo "============================================================"
