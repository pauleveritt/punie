#!/bin/bash
# Experiment: 6-bit quantization for memory reduction
#
# Goal: Test if 6-bit (64 quantization levels) preserves LoRA signal
# better than 4-bit (16 levels) while reducing size vs 8-bit (256 levels)
#
# Expected:
# - Size: ~20GB (vs 30GB for 8-bit, 60GB for float16)
# - Quality: Unknown - this is the experiment!
# - 64 levels may be enough to preserve fine-tuning deltas

set -e

echo "========================================================================"
echo "6-BIT QUANTIZATION EXPERIMENT"
echo "========================================================================"
echo ""

F16_INPUT="fused_model_qwen3_phase8_f16"
Q6_OUTPUT="fused_model_qwen3_phase8_6bit"

# Validate float16 model exists
if [ ! -d "$F16_INPUT" ]; then
    echo "❌ Error: Float16 model not found at $F16_INPUT"
    echo "   Run scripts/fuse_phase8.sh first"
    exit 1
fi

echo "Configuration:"
echo "  Input: $F16_INPUT (float16, ~60GB)"
echo "  Output: $Q6_OUTPUT (6-bit, expected ~20GB)"
echo "  Group size: 64 (standard for MLX)"
echo ""

# Convert to 6-bit
echo "Converting to 6-bit quantization..."
echo "  6-bit = 64 discrete values per group"
echo "  vs 4-bit = 16 values (destroys LoRA signal)"
echo "  vs 8-bit = 256 values (preserves LoRA signal)"
echo ""

if [ -d "$Q6_OUTPUT" ]; then
    echo "⚠️  6-bit model already exists at $Q6_OUTPUT"
    read -p "Overwrite? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Using existing 6-bit model..."
        echo ""
        du -sh "$Q6_OUTPUT"
        exit 0
    else
        rm -rf "$Q6_OUTPUT"
    fi
fi

uv run python -m mlx_lm.convert \
    --hf-path "$F16_INPUT" \
    --mlx-path "$Q6_OUTPUT" \
    --quantize \
    --q-bits 6 \
    --q-group-size 64

echo ""
echo "✓ 6-bit model created at $Q6_OUTPUT"
du -sh "$Q6_OUTPUT"
echo ""

# Summary
echo "========================================================================"
echo "6-bit Quantization Complete!"
echo "========================================================================"
echo ""
echo "Model sizes:"
du -sh fused_model_qwen3_phase8_* 2>/dev/null | awk '{print "  " $2 ": " $1}'
echo ""
echo "Next steps:"
echo "  1. Run benchmark: scripts/benchmark_6bit_vs_8bit.py"
echo "  2. Test 5-query discrimination accuracy"
echo "  3. Measure memory usage and speed"
echo ""
echo "Research question:"
echo "  Does 64 quantization levels (6-bit) preserve LoRA signal"
echo "  while reducing memory by ~33% vs 8-bit?"
echo ""
