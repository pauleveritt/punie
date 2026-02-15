#!/usr/bin/env bash
# Phase 21: Train with XML-format data to fix tool-calling format mismatch
# This script trains a LoRA adapter, fuses it, and quantizes to 5-bit

set -e  # Exit on error

echo "================================================================================"
echo "PHASE 21: XML FORMAT TRAINING"
echo "================================================================================"
echo ""
echo "This training fixes the tool-calling format mismatch:"
echo "  OLD: \`\`\`json fence (model was trained on this)"
echo "  NEW: <tool_call> XML format (mlx_lm.server expects this)"
echo ""
echo "Training pipeline:"
echo "  1. LoRA training (~2 hours)"
echo "  2. Fuse to float16 (preserves LoRA deltas)"
echo "  3. Quantize to 5-bit (proven in Phase 20)"
echo ""
echo "================================================================================"
echo ""

# Step 1: Train LoRA adapter
echo "Step 1/3: Training LoRA adapter..."
echo "  Model: Qwen3-Coder-30B-A3B-Instruct-4bit"
echo "  Data: data/phase8_xml_format (683 examples, 70.7% tool-calling)"
echo "  Config: 500 iters, batch_size 1, lr 1e-4, 8 layers"
echo ""

uv run python -m mlx_lm.lora \
    --model mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit \
    --train \
    --data data/phase8_xml_format \
    --iters 500 \
    --batch-size 1 \
    --learning-rate 1e-4 \
    --num-layers 8 \
    --adapter-path adapters_phase21_xml \
    --save-every 250 \
    --val-batches 10 \
    --test

echo ""
echo "✅ LoRA training complete!"
echo ""

# Step 2: Fuse to float16 (dequantize to preserve LoRA signal)
echo "Step 2/3: Fusing adapter to float16..."
echo "  This dequantizes the model to preserve LoRA deltas"
echo ""

uv run python -m mlx_lm.fuse \
    --model mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit \
    --adapter-path adapters_phase21_xml \
    --save-path fused_model_qwen3_phase21_xml_f16 \
    --dequantize

echo ""
echo "✅ Fused to float16!"
echo ""

# Step 3: Quantize to 5-bit (proven to preserve LoRA in Phase 20)
echo "Step 3/3: Quantizing to 5-bit..."
echo "  5-bit preserves LoRA deltas while reducing size"
echo ""

uv run python -m mlx_lm.convert \
    --hf-path fused_model_qwen3_phase21_xml_f16 \
    --mlx-path fused_model_qwen3_phase21_xml_5bit \
    --quantize \
    --q-bits 5 \
    --q-group-size 64

echo ""
echo "✅ Quantized to 5-bit!"
echo ""

echo "================================================================================"
echo "✅ PHASE 21 TRAINING COMPLETE"
echo "================================================================================"
echo ""
echo "Models created:"
echo "  1. adapters_phase21_xml/ - LoRA adapter (for reference)"
echo "  2. fused_model_qwen3_phase21_xml_f16/ - Float16 fused model (~57GB)"
echo "  3. fused_model_qwen3_phase21_xml_5bit/ - 5-bit fused model (~19GB) ← Use this!"
echo ""
echo "Next steps:"
echo "  1. Test with: uv run python scripts/test_server_pipeline.py"
echo "  2. Profile with: uv run python scripts/profile_latency.py"
echo "  3. Benchmark with: uv run python scripts/benchmark_speculative.py"
echo ""
echo "================================================================================"
