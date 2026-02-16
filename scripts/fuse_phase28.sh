#!/bin/bash
# Fuse and quantize Phase 28 model

set -e

BASE="mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit"
ADAPTER="adapters_phase28"
OUTPUT_F16="fused_model_qwen3_phase28_f16"
OUTPUT_5BIT="fused_model_qwen3_phase28_5bit"

echo "Fusing Phase 28 Model"
echo "====================="
echo ""

# Step 1: Fuse to float16
echo "Step 1: Fusing to float16..."
uv run python -m mlx_lm.fuse \
  --model "$BASE" \
  --adapter-path "$ADAPTER" \
  --save-path "$OUTPUT_F16" \
  --dequantize

echo "✅ Float16 model created: $OUTPUT_F16"
du -sh "$OUTPUT_F16"
echo ""

# Step 2: Quantize to 5-bit
echo "Step 2: Quantizing to 5-bit..."
uv run python -m mlx_lm.convert \
  --hf-path "$OUTPUT_F16" \
  --mlx-path "$OUTPUT_5BIT" \
  --quantize \
  --q-bits 5

echo "✅ 5-bit model created: $OUTPUT_5BIT"
du -sh "$OUTPUT_5BIT"
echo ""

echo "Next: Validate the model"
echo "  uv run python scripts/validate_model.py $OUTPUT_5BIT"
