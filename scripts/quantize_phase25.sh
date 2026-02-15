#!/usr/bin/env bash
# Quantize Phase 25b fused model to 6-bit

set -euo pipefail

echo "=== Quantizing Phase 25b (7B) to 6-bit ==="

INPUT_PATH="fused_model_qwen25_phase25b_7b_f16"
OUTPUT_PATH="fused_model_qwen25_phase25b_7b_6bit"

echo "Input (float16): $INPUT_PATH"
echo "Output (6-bit): $OUTPUT_PATH"
echo ""

# Check input exists
if [ ! -d "$INPUT_PATH" ]; then
    echo "ERROR: Float16 model not found at $INPUT_PATH"
    echo "Run ./scripts/fuse_phase25.sh first"
    exit 1
fi

# Clean output if exists
if [ -d "$OUTPUT_PATH" ]; then
    echo "Removing existing quantized model..."
    rm -rf "$OUTPUT_PATH"
fi

echo "Quantizing to 6-bit (64 quantization levels)..."
echo "This preserves LoRA signal while reducing size by ~50%"
echo "6-bit is proven to maintain 100% accuracy on 30B"
echo ""

# Quantize to 6-bit with group_size 64 (proven safe)
uv run python -m mlx_lm.convert \
    --hf-path "$INPUT_PATH" \
    --mlx-path "$OUTPUT_PATH" \
    --quantize \
    --q-bits 6 \
    --q-group-size 64

echo ""
echo "=== Quantization Complete ==="
echo "6-bit model saved to: $OUTPUT_PATH"
echo "Size comparison:"
echo "  Float16: $(du -sh $INPUT_PATH | cut -f1)"
echo "  6-bit: $(du -sh $OUTPUT_PATH | cut -f1)"
echo ""
echo "Expected: ~6-7 GB (7B is ~3x smaller than 30B)"
echo ""
echo "Next step: Test with uv run python scripts/test_phase25_model.py $OUTPUT_PATH"
