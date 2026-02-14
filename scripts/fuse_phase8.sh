#!/bin/bash
# Fuse Phase 8 adapter to 8-bit model
#
# Based on Phase 5c success:
# - Dequantize to float16 first (preserves LoRA signal)
# - Then re-quantize to 8-bit (256 levels preserve deltas)
# - Do NOT re-quantize to 4-bit (only 16 levels, destroys signal)
#
# Expected result:
# - 100% accuracy (same as adapter)
# - 8-10x faster than adapter
# - ~8-10GB disk/memory (half of float16, double of 4-bit)

set -e

echo "========================================================================"
echo "PHASE 8: Fuse Adapter to 8-bit Model"
echo "========================================================================"
echo ""

MODEL="mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit"
ADAPTER="adapters_phase8"
F16_OUTPUT="fused_model_qwen3_phase8_f16"
Q8_OUTPUT="fused_model_qwen3_phase8_8bit"

# Validate adapter exists
if [ ! -f "$ADAPTER/adapters.safetensors" ]; then
    echo "❌ Error: Adapter not found at $ADAPTER/adapters.safetensors"
    echo "   Run scripts/train_phase8.sh first"
    exit 1
fi

echo "Configuration:"
echo "  Base model: $MODEL"
echo "  Adapter: $ADAPTER"
echo "  Float16 output: $F16_OUTPUT"
echo "  8-bit output: $Q8_OUTPUT"
echo ""

# Step 1: Dequantize and fuse to float16
echo "Step 1: Dequantizing to float16 and fusing adapter..."
echo "  This preserves LoRA signal (4-bit fusion destroys it)"
echo ""

if [ -d "$F16_OUTPUT" ]; then
    echo "⚠️  Float16 model already exists at $F16_OUTPUT"
    read -p "Overwrite? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Using existing float16 model..."
    else
        rm -rf "$F16_OUTPUT"
        uv run python -m mlx_lm.fuse \
            --model "$MODEL" \
            --adapter-path "$ADAPTER" \
            --save-path "$F16_OUTPUT" \
            --dequantize
    fi
else
    uv run python -m mlx_lm.fuse \
        --model "$MODEL" \
        --adapter-path "$ADAPTER" \
        --save-path "$F16_OUTPUT" \
        --dequantize
fi

echo ""
echo "✓ Float16 model created at $F16_OUTPUT"
du -sh "$F16_OUTPUT"
echo ""

# Step 2: Re-quantize to 8-bit
echo "Step 2: Re-quantizing to 8-bit..."
echo "  8-bit has 256 levels (vs 16 for 4-bit) - preserves LoRA deltas"
echo ""

if [ -d "$Q8_OUTPUT" ]; then
    echo "⚠️  8-bit model already exists at $Q8_OUTPUT"
    read -p "Overwrite? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Using existing 8-bit model..."
    else
        rm -rf "$Q8_OUTPUT"
        uv run python -m mlx_lm.convert \
            --hf-path "$F16_OUTPUT" \
            --mlx-path "$Q8_OUTPUT" \
            --quantize \
            --q-bits 8
    fi
else
    uv run python -m mlx_lm.convert \
        --hf-path "$F16_OUTPUT" \
        --mlx-path "$Q8_OUTPUT" \
        --quantize \
        --q-bits 8
fi

echo ""
echo "✓ 8-bit model created at $Q8_OUTPUT"
du -sh "$Q8_OUTPUT"
echo ""

# Summary
echo "========================================================================"
echo "Fusion Complete!"
echo "========================================================================"
echo ""
echo "Created models:"
echo "  Float16: $F16_OUTPUT (full precision, ~25-30GB)"
echo "  8-bit: $Q8_OUTPUT (production model, ~8-10GB)"
echo ""
echo "Model sizes:"
du -sh "$F16_OUTPUT" "$Q8_OUTPUT" 2>/dev/null | awk '{print "  " $2 ": " $1}'
echo ""
echo "Next steps:"
echo "  1. Benchmark 8-bit model: scripts/benchmark_qwen3_8bit.py"
echo "  2. If successful, archive adapter and float16 model"
echo "  3. Update punie config to use $Q8_OUTPUT"
echo ""
echo "Expected 8-bit performance (based on Phase 5c):"
echo "  - 100% accuracy (same as adapter)"
echo "  - 8-10x faster than adapter"
echo "  - ~8-10GB memory (fits in 16GB unified memory)"
echo ""
