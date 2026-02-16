#!/bin/bash
# Fuse Phase 26 LSP adapters to float16 base model
#
# Input: adapters_phase26_lsp/
# Output: fused_model_qwen3_phase26_lsp_f16/

set -e

echo "Fusing Phase 26 LSP adapters to float16..."
echo "Adapters: adapters_phase26_lsp/"
echo "Output: fused_model_qwen3_phase26_lsp_f16/"
echo ""

uv run python -m mlx_lm.fuse \
  --model mlx-community/Qwen2.5-Coder-32B-Instruct-4bit \
  --adapter-path ./adapters_phase26_lsp \
  --save-path ./fused_model_qwen3_phase26_lsp_f16 \
  --dequantize

echo ""
echo "✓ Fuse complete"
echo "Float16 model saved to: fused_model_qwen3_phase26_lsp_f16/"
echo "Size: ~57 GB"
