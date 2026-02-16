#!/bin/bash
set -e

echo "Quantizing Phase 26 to 5-bit..."

# Convert from float16 to 5-bit
uv run python -m mlx_lm.convert \
  --hf-path ./fused_model_qwen3_phase26_f16 \
  --mlx-path ./fused_model_qwen3_phase26_5bit \
  --quantize \
  --q-bits 5

echo "✓ 5-bit quantization complete"
ls -lh fused_model_qwen3_phase26_5bit/
