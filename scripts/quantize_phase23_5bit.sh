#!/usr/bin/env bash
# Quantize Phase 23 fused model to 5-bit

set -euo pipefail

echo "=== Quantizing Phase 23 to 5-bit ==="

INPUT_PATH="fused_model_qwen3_phase23_ty_f16"
OUTPUT_PATH="fused_model_qwen3_phase23_ty_5bit"

echo "Input (float16): $INPUT_PATH"
echo "Output (5-bit): $OUTPUT_PATH"
echo ""

# Check input exists
if [ ! -d "$INPUT_PATH" ]; then
    echo "ERROR: Float16 model not found at $INPUT_PATH"
    echo "Run ./scripts/fuse_phase23.sh first"
    exit 1
fi

# Clean output if exists
if [ -d "$OUTPUT_PATH" ]; then
    echo "Removing existing quantized model..."
    rm -rf "$OUTPUT_PATH"
fi

echo "Quantizing to 5-bit (32 quantization levels)..."
echo "This preserves LoRA signal while reducing size by ~65%"
echo ""

# Quantize to 5-bit
uv run python -m mlx_lm.convert \
    --hf-path "$INPUT_PATH" \
    --mlx-path "$OUTPUT_PATH" \
    --quantize \
    --q-bits 5

echo ""
echo "=== Quantization Complete ==="
echo "5-bit model saved to: $OUTPUT_PATH"
echo "Size comparison:"
echo "  Float16: $(du -sh $INPUT_PATH | cut -f1)"
echo "  5-bit: $(du -sh $OUTPUT_PATH | cut -f1)"
echo ""
echo "Next step: Test with ./scripts/test_phase23_model.py"
