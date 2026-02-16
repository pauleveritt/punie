#!/bin/bash
# Full Phase 26 training pipeline with validation checks
#
# This script runs the complete pipeline:
# 1. Pre-training checks (validate data before training)
# 2. Training (500 iterations)
# 3. Post-training checks (validate loss convergence)
# 4. Fusion (dequantize to float16)
# 5. Post-fusion checks (validate eos_token_id)
# 6. Quantization (6-bit)
# 7. Post-quantization checks (validate 6-bit config)

set -e  # Exit on error

echo "============================================================"
echo "Phase 26 Full Training Pipeline"
echo "============================================================"
echo ""

# Stage 1: Pre-training checks
echo "Stage 1: Pre-training data validation"
echo "--------------------------------------"
uv run python -c "
from pathlib import Path
from punie.training.checks import run_pre_training_checks, summarize_checks

results = run_pre_training_checks(
    data_directory=Path('data/phase26_merged'),
    expected_format='messages',
    expected_patterns=(
        'result.errors', 'result.error_count', 'result.success',
        'result.violations', 'result.violation_count', 'result.fixable_count',
        'result.tests', 'result.passed', 'result.failed',
    ),
)

print(summarize_checks(results))

# Fail if any critical check fails
if not all(r.passed for r in results):
    print('\nERROR: Pre-training checks failed!')
    print('Fix data issues before training')
    exit(1)
"

if [ $? -ne 0 ]; then
    echo ""
    echo "Pre-training checks failed. Aborting pipeline."
    exit 1
fi

echo ""
echo "✓ Pre-training checks passed"
echo ""

# Stage 2: Training
echo "Stage 2: Training"
echo "-----------------"
bash scripts/train_phase26.sh

# Check if training produced adapter
if [ ! -d "adapters_phase26" ]; then
    echo "ERROR: Training did not produce adapter"
    exit 1
fi

echo ""
echo "✓ Training complete"
echo ""

# Stage 3: Fusion
echo "Stage 3: Fusion to Float16"
echo "---------------------------"
bash scripts/fuse_phase26.sh

# Check if fusion produced model
if [ ! -d "fused_model_qwen3_phase26_f16" ]; then
    echo "ERROR: Fusion did not produce model"
    exit 1
fi

echo ""
echo "✓ Fusion complete"
echo ""

# Stage 4: Post-fusion checks
echo "Stage 4: Post-fusion validation"
echo "--------------------------------"
uv run python -c "
from pathlib import Path
from punie.training.checks import run_post_fusion_checks, summarize_checks

# Qwen3 uses eos_token_id = [151645, 151643]
results = run_post_fusion_checks(
    fused_model_path=Path('fused_model_qwen3_phase26_f16'),
    expected_eos_token_ids=(151645, 151643),
)

print(summarize_checks(results))

if not all(r.passed for r in results):
    print('\nWARNING: Post-fusion checks have issues')
"

echo ""
echo "✓ Post-fusion checks complete"
echo ""

# Stage 5: Quantization
echo "Stage 5: 6-bit Quantization"
echo "----------------------------"
bash scripts/quantize_phase26.sh

# Check if quantization produced model
if [ ! -d "fused_model_qwen3_phase26_6bit" ]; then
    echo "ERROR: Quantization did not produce model"
    exit 1
fi

echo ""
echo "✓ Quantization complete"
echo ""

# Stage 6: Post-quantization checks
echo "Stage 6: Post-quantization validation"
echo "--------------------------------------"
uv run python -c "
from pathlib import Path
from punie.training.checks import run_post_quantization_checks, summarize_checks

results = run_post_quantization_checks(
    quantized_model_path=Path('fused_model_qwen3_phase26_6bit'),
    expected_bits=6,
)

print(summarize_checks(results))

if not all(r.passed for r in results):
    print('\nWARNING: Post-quantization checks have issues')
"

echo ""
echo "✓ Post-quantization checks complete"
echo ""

echo "============================================================"
echo "Phase 26 Pipeline Complete!"
echo "============================================================"
echo ""
echo "Production model:"
echo "  Path: ./fused_model_qwen3_phase26_6bit"
echo "  Size: ~23 GB"
echo "  Format: 6-bit quantized"
echo ""
echo "Next steps:"
echo "  1. Run validation: uv run python scripts/test_phase26_validation.py"
echo "  2. Compare with Phase 23 baseline (0% field access)"
echo "  3. Document results in diary entry"
echo "============================================================"
