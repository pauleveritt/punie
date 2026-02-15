#!/usr/bin/env bash
# Phase 22: Train with Code Mode format for multi-step Python workflows
# This script trains a LoRA adapter, fuses it, and quantizes to 5-bit

set -e  # Exit on error

echo "================================================================================"
echo "PHASE 22: CODE MODE TRAINING"
echo "================================================================================"
echo ""
echo "This training enables Code Mode - Python workflows with multiple tool calls:"
echo "  OLD: Sequential tool calls (N+2 model turns for N operations)"
echo "  NEW: execute_code with Python (1-2 turns for multi-step workflows)"
echo ""
echo "Training data:"
echo "  - 683 converted Phase 21 examples (single-tool → execute_code)"
echo "  - 24 new multi-step workflow examples"
echo "  - Total: 707 examples (68% tool-calling, 31% direct answers)"
echo ""
echo "Training pipeline:"
echo "  1. LoRA training (~2 hours)"
echo "  2. Fuse to float16 (preserves LoRA deltas)"
echo "  3. Quantize to 5-bit (proven in Phase 21)"
echo ""
echo "================================================================================"
echo ""

# Step 1: Train LoRA adapter
echo "Step 1/3: Training LoRA adapter..."
echo "  Model: Qwen3-Coder-30B-A3B-Instruct-4bit"
echo "  Data: data/phase22_merged (707 examples, 68% tool-calling)"
echo "  Config: 500 iters, batch_size 1, lr 1e-4, 8 layers"
echo ""

uv run python -m mlx_lm.lora \
    --model mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit \
    --train \
    --data data/phase22_merged \
    --iters 500 \
    --batch-size 1 \
    --learning-rate 1e-4 \
    --num-layers 8 \
    --adapter-path adapters_phase22_code \
    --save-every 250 \
    --val-batches 10 \
    --test

echo ""
echo "✅ LoRA training complete!"
echo ""

# Step 2: Fuse to float16 (dequantize to preserve LoRA signal)
echo "Step 2/3: Fusing adapter to float16..."
echo "  This dequantizes the model to preserve LoRA deltas"
echo "  Size: ~57GB (will be deleted after quantization)"
echo ""

uv run python -m mlx_lm.fuse \
    --model mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit \
    --adapter-path adapters_phase22_code \
    --save-path fused_model_qwen3_phase22_code_f16 \
    --dequantize

echo ""
echo "✅ Fused to float16!"
echo ""

# Step 3: Quantize to 5-bit (proven to preserve LoRA in Phase 21)
echo "Step 3/3: Quantizing to 5-bit..."
echo "  5-bit preserves LoRA deltas while reducing size to ~20GB"
echo ""

uv run python -m mlx_lm.convert \
    --hf-path fused_model_qwen3_phase22_code_f16 \
    --mlx-path fused_model_qwen3_phase22_code_5bit \
    --quantize \
    --q-bits 5 \
    --q-group-size 64

echo ""
echo "✅ Quantized to 5-bit!"
echo ""

# Clean up float16 intermediate (save disk space)
echo "Cleaning up float16 intermediate model..."
rm -rf fused_model_qwen3_phase22_code_f16
echo "✅ Removed float16 model (reclaimed ~57GB)"
echo ""

echo "================================================================================"
echo "✅ PHASE 22 TRAINING COMPLETE"
echo "================================================================================"
echo ""
echo "Models created:"
echo "  1. adapters_phase22_code/ - LoRA adapter (for reference)"
echo "  2. fused_model_qwen3_phase22_code_5bit/ - 5-bit fused model (~20GB) ← Use this!"
echo ""
echo "Next steps:"
echo "  1. Test single-tool accuracy: uv run python scripts/test_phase22_model.py"
echo "  2. Benchmark vs Phase 21: uv run python scripts/benchmark_phase22_vs_21.py"
echo ""
echo "Expected results:"
echo "  - Single-tool queries: 100% (5/5) - parity with Phase 21"
echo "  - Multi-step queries: 80%+ (4/5) - new capability"
echo "  - Latency: 40-60% reduction on multi-step queries"
echo ""
echo "================================================================================"
