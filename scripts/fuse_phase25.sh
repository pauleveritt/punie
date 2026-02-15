#!/usr/bin/env bash
# Fuse Phase 25b adapter to float16 (intermediate step before quantization)

set -euo pipefail

echo "=== Fusing Phase 25b Adapter (7B) to Float16 ==="

BASE_MODEL="mlx-community/Qwen2.5-Coder-7B-Instruct-4bit"
ADAPTER_PATH="adapters_phase25b_7b"
OUTPUT_PATH="fused_model_qwen25_phase25b_7b_f16"

echo "Base model: $BASE_MODEL"
echo "Adapter: $ADAPTER_PATH"
echo "Output: $OUTPUT_PATH"
echo ""

# Check adapter exists
if [ ! -d "$ADAPTER_PATH" ]; then
    echo "ERROR: Adapter not found at $ADAPTER_PATH"
    echo "Run ./scripts/train_phase25.sh first"
    exit 1
fi

# Clean output if exists
if [ -d "$OUTPUT_PATH" ]; then
    echo "Removing existing fused model..."
    rm -rf "$OUTPUT_PATH"
fi

echo "Fusing adapter (this will take ~5 minutes)..."
echo ""

# Fuse with dequantization (creates float16 model)
# CRITICAL: --dequantize flag preserves LoRA signal
uv run python -m mlx_lm.fuse \
    --model "$BASE_MODEL" \
    --adapter-path "$ADAPTER_PATH" \
    --save-path "$OUTPUT_PATH" \
    --dequantize

echo ""
echo "Patching config.json to fix eos_token_id..."
python3 -c "
import json
with open('$OUTPUT_PATH/config.json') as f:
    config = json.load(f)
config['eos_token_id'] = [151645, 151643]  # <|im_end|> + <|endoftext|>
with open('$OUTPUT_PATH/config.json', 'w') as f:
    json.dump(config, f, indent=4)
print('✓ eos_token_id patched to [151645, 151643]')
"

echo ""
echo "=== Fusion Complete ==="
echo "Float16 model saved to: $OUTPUT_PATH"
echo "Size: $(du -sh $OUTPUT_PATH | cut -f1)"
echo ""
echo "Next step: Quantize to 6-bit with ./scripts/quantize_phase25.sh"
