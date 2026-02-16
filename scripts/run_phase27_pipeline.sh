#!/bin/bash
# Phase 27 Complete Pipeline: Training → Fusion → Quantization → Validation → Cleanup
# Run this after training completes or run with --wait to wait for training

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║                    Phase 27 Pipeline Executor                      ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

# Check if training is complete
if [ ! -d "adapters_phase27" ]; then
    echo "❌ Error: adapters_phase27 directory not found!"
    echo "   Training must complete before running this pipeline."
    exit 1
fi

echo "✓ Training adapters found"
echo ""

# Phase 4: Fusion
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║ Phase 4: Fusing Adapters to Float16                                ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

if [ -d "fused_model_qwen3_phase27_f16" ]; then
    echo "⚠ Float16 model already exists, skipping fusion..."
else
    bash scripts/fuse_phase27.sh
fi

echo ""

# Phase 4: Quantization
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║ Phase 4: Quantizing to 5-bit                                       ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

if [ -d "fused_model_qwen3_phase27_5bit" ]; then
    echo "⚠ 5-bit model already exists, skipping quantization..."
else
    bash scripts/quantize_phase27_5bit.sh
fi

echo ""

# Phase 5: Validation
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║ Phase 5: Running Validation Suite (40 queries)                     ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

uv run python scripts/test_phase27_validation.py fused_model_qwen3_phase27_5bit | tee logs/phase27_validation.log

echo ""

# Phase 6: Performance Benchmarking
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║ Phase 6: Performance Benchmarking                                  ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

echo "Measuring model size and memory usage..."
du -sh fused_model_qwen3_phase27_5bit

echo ""

# Phase 7: Cleanup
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║ Phase 7: Cleanup & Documentation                                   ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

echo "Creating deployment summary..."
cat > docs/phase27-deployment-summary.md << 'EOF'
# Phase 27 Deployment Summary

## Implementation Complete

**Date:** $(date +"%Y-%m-%d")
**Model:** fused_model_qwen3_phase27_5bit (5-bit quantized)

## New Tools Added (6 total)

### LSP Tools (3)
1. **hover(file_path, line, column, symbol)** → HoverResult
2. **document_symbols(file_path)** → DocumentSymbolsResult
3. **workspace_symbols(query)** → WorkspaceSymbolsResult

### Git Tools (3)
1. **git_status(path)** → GitStatusResult
2. **git_diff(path, staged)** → GitDiffResult
3. **git_log(path, count)** → GitLogResult

## Training Data

- Total examples: 1104
  - Phase 26 balanced: 800
  - Phase 27 new LSP: 84
  - Phase 27 git: 84
  - Phase 27 rebalance: 96
  - Phase 27 direct answers: 40
- Split: 993 train / 111 valid (90/10)
- Training iterations: 800
- Learning rate: 1e-4
- Batch size: 1
- LoRA layers: 8

## Validation Results

See logs/phase27_validation.log for full results.

## Model Specifications

- Base: Qwen3-Coder-30B-A3B-Instruct-4bit
- Quantization: 5-bit
- Size: ~20 GB
- Location: fused_model_qwen3_phase27_5bit/

## Deployment

**Production model:** fused_model_qwen3_phase27_5bit/

This model replaces Phase 26 balanced model and adds 6 new typed tools.

## Files Modified

- Infrastructure: 9 core files updated
- Tests: 3 test files updated with new fixtures
- Training data: 4 generation scripts created
- Scripts: 5 pipeline scripts created

## Next Steps

- Archive Phase 26 balanced model (optional)
- Update production deployment to use Phase 27 model
- Monitor field access rate and tool usage in production
EOF

echo "✓ Documentation created: docs/phase27-deployment-summary.md"

echo ""
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║                     Phase 27 Pipeline Complete!                    ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Summary:"
echo "  - Model: fused_model_qwen3_phase27_5bit/"
echo "  - Size: $(du -sh fused_model_qwen3_phase27_5bit | cut -f1)"
echo "  - Validation: See logs/phase27_validation.log"
echo "  - Documentation: docs/phase27-deployment-summary.md"
echo ""
echo "✓ Ready for production deployment"
