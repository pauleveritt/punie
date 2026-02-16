#!/bin/bash
# Fuse Phase 26 adapter with base model
#
# This dequantizes the 4-bit base model to float16 and applies the LoRA adapter.
# Critical: Must dequantize to avoid destroying the LoRA signal (Phase 5c lesson)

set -e  # Exit on error

echo "============================================================"
echo "Phase 26 Fusion: Dequantize to Float16"
echo "============================================================"
echo ""

# Check if adapter exists
if [ ! -d "adapters_phase26" ]; then
    echo "Error: adapters_phase26 directory not found"
    echo "Run scripts/train_phase26.sh first"
    exit 1
fi

echo "Fusing adapter with base model..."
echo "  Base model: mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit"
echo "  Adapter: ./adapters_phase26"
echo "  Output: ./fused_model_qwen3_phase26_f16"
echo "  Format: Float16 (dequantized)"
echo ""

# Run fusion with dequantize flag
uv run python -m mlx_lm.fuse \
  --model mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit \
  --adapter-path ./adapters_phase26 \
  --save-path ./fused_model_qwen3_phase26_f16 \
  --dequantize

echo ""
echo "============================================================"
echo "Fusion complete!"
echo "Fused model saved to: ./fused_model_qwen3_phase26_f16"
echo "Size: ~57 GB (float16)"
echo ""
echo "Next step: Run scripts/quantize_phase26.sh for 6-bit quantization"
echo "============================================================"
