#!/usr/bin/env bash
# Fuse Phase 23 adapter to float16 (intermediate step before quantization)

set -euo pipefail

echo "=== Fusing Phase 23 Adapter to Float16 ==="

BASE_MODEL="mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit"
ADAPTER_PATH="adapters/phase23_ty"
OUTPUT_PATH="fused_model_qwen3_phase23_ty_f16"

echo "Base model: $BASE_MODEL"
echo "Adapter: $ADAPTER_PATH"
echo "Output: $OUTPUT_PATH"
echo ""

# Check adapter exists
if [ ! -d "$ADAPTER_PATH" ]; then
    echo "ERROR: Adapter not found at $ADAPTER_PATH"
    echo "Run ./scripts/train_phase23.sh first"
    exit 1
fi

# Clean output if exists
if [ -d "$OUTPUT_PATH" ]; then
    echo "Removing existing fused model..."
    rm -rf "$OUTPUT_PATH"
fi

echo "Fusing adapter (this will take 5-10 minutes)..."
echo ""

# Fuse with dequantization (creates float16 model)
uv run python -m mlx_lm.fuse \
    --model "$BASE_MODEL" \
    --adapter-path "$ADAPTER_PATH" \
    --save-path "$OUTPUT_PATH" \
    --dequantize

echo ""
echo "=== Fusion Complete ==="
echo "Float16 model saved to: $OUTPUT_PATH"
echo "Size: $(du -sh $OUTPUT_PATH | cut -f1)"
echo ""
echo "Next step: Quantize to 5-bit with ./scripts/quantize_phase23_5bit.sh"
