#!/bin/bash
# Experiment: 5-bit quantization for maximum memory reduction
#
# Goal: Test if 5-bit (32 quantization levels) preserves LoRA signal
#
# Context:
# - 4-bit (16 levels) ❌ Destroys signal → 60% accuracy
# - 6-bit (64 levels) ✅ Preserves signal → 100% accuracy
# - Question: Is 5-bit (32 levels) the threshold?
#
# Expected:
# - Size: ~18-19GB (vs 23GB for 6-bit, 30GB for 8-bit)
# - Quality: Unknown - this is the experiment!
# - 32 levels may be on the edge of preserving fine-tuning deltas

set -e

echo "========================================================================"
echo "5-BIT QUANTIZATION EXPERIMENT"
echo "========================================================================"
echo ""

F16_INPUT="fused_model_qwen3_phase8_f16"
Q5_OUTPUT="fused_model_qwen3_phase8_5bit"

# Check if we need to recreate float16
if [ ! -d "$F16_INPUT" ]; then
    echo "❌ Error: Float16 model not found at $F16_INPUT"
    echo ""
    echo "To create it, run:"
    echo "  ./scripts/fuse_phase8.sh"
    echo ""
    exit 1
fi

echo "Configuration:"
echo "  Input: $F16_INPUT (float16, ~57GB)"
echo "  Output: $Q5_OUTPUT (5-bit, expected ~18-19GB)"
echo "  Group size: 64 (standard for MLX)"
echo ""

# Convert to 5-bit
echo "Converting to 5-bit quantization..."
echo "  5-bit = 32 discrete values per group"
echo "  vs 4-bit = 16 values (destroys LoRA signal)"
echo "  vs 6-bit = 64 values (preserves LoRA signal)"
echo ""
echo "Research question: Is 32 levels the threshold for LoRA preservation?"
echo ""

if [ -d "$Q5_OUTPUT" ]; then
    echo "⚠️  5-bit model already exists at $Q5_OUTPUT"
    read -p "Overwrite? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Using existing 5-bit model..."
        echo ""
        du -sh "$Q5_OUTPUT"
        exit 0
    else
        rm -rf "$Q5_OUTPUT"
    fi
fi

uv run python -m mlx_lm.convert \
    --hf-path "$F16_INPUT" \
    --mlx-path "$Q5_OUTPUT" \
    --quantize \
    --q-bits 5 \
    --q-group-size 64

echo ""
echo "✓ 5-bit model created at $Q5_OUTPUT"
du -sh "$Q5_OUTPUT"
echo ""

# Summary
echo "========================================================================"
echo "5-bit Quantization Complete!"
echo "========================================================================"
echo ""
echo "Model sizes:"
du -sh fused_model_qwen3_phase8_* archived_models/fused_model_qwen3_phase8_8bit 2>/dev/null | awk '{print "  " $2 ": " $1}'
echo ""
echo "Next steps:"
echo "  1. Test quality: uv run python scripts/test_single_model.py $Q5_OUTPUT"
echo "  2. Compare with 6-bit results"
echo "  3. If accuracy ≥ 80%, we found the threshold!"
echo ""
echo "Research question:"
echo "  Does 32 quantization levels (5-bit) preserve LoRA signal?"
echo "  This would save another 4-5 GB vs 6-bit!"
echo ""
