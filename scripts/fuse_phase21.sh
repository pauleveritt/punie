#!/bin/bash
# Fuse Phase 21 model and quantize to 5-bit

set -e

echo "Fusing Phase 21 Model"
echo "====================="
echo ""

BASE_MODEL="mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit"
ADAPTER="adapters_phase21"
OUTPUT_F16="fused_model_qwen3_phase21_f16"
OUTPUT_5BIT="fused_model_qwen3_phase21_5bit"

echo "Step 1: Fusing to float16..."
uv run python -m mlx_lm.fuse \
  --model "$BASE_MODEL" \
  --adapter-path "$ADAPTER" \
  --save-path "$OUTPUT_F16" \
  --dequantize

echo "✅ Float16 model created: $OUTPUT_F16"
du -sh "$OUTPUT_F16"
echo ""

echo "Step 2: Quantizing to 5-bit..."
uv run python -m mlx_lm.convert \
  --hf-path "$OUTPUT_F16" \
  --mlx-path "$OUTPUT_5BIT" \
  --quantize \
  --q-bits 5

echo "✅ 5-bit model created: $OUTPUT_5BIT"
du -sh "$OUTPUT_5BIT"
echo ""

echo "Next: Run benchmark comparison"
echo "  uv run python scripts/benchmark_3way.py"
