# Next Steps: Phase 27 Cleaned Model

**Date:** 2026-02-16
**Status:** Data Cleaned ✅ → Ready for Training
**Projected Accuracy:** 75-80% (up from 46%)

---

## Current Status

### ✅ Completed

1. **Multi-Turn Validation Implemented** (57 queries total)
   - 45 single-turn queries
   - 12 multi-turn queries (8 summary + 4 cross-tool chaining)
   - Files: `scripts/validate_model.py` (extended), `docs/multi-turn-validation-*.md`

2. **Phase 27 Augmented Baseline Established** (46% strict accuracy)
   - Full validation run completed
   - Files: `validation_phase27_baseline.json`, `validation_phase27_baseline.log`

3. **Root Cause Identified** (Inconsistent preamble training)
   - 360 examples had preambles (34%), causing early EOS tokens
   - goto_definition/find_references: 68% with preambles
   - git_status/typecheck: 0% with preambles
   - Model confusion → generates preamble → hits EOS → never calls tool
   - File: `docs/phase27-augmented-root-cause-analysis.md`

4. **Data Cleaned** (399 preambles removed)
   - Input: `data/phase27_augmented/` (1164 examples)
   - Output: `data/phase27_cleaned/` (1164 examples, 0 preambles)
   - Script: `scripts/remove_preambles.py`
   - Verification: ✅ 0 preambles remaining

---

## Next Actions

### Step 1: Review Cleaned Data (5 min)

Verify the cleaning worked correctly:

```bash
# Check a few examples
head -3 data/phase27_cleaned/train.jsonl | python3 -m json.tool | less

# Count examples
wc -l data/phase27_cleaned/*.jsonl

# Verify no preambles remain
grep '"role": "assistant"' data/phase27_cleaned/train.jsonl | \
  grep '<tool_call>' | \
  python3 -c "
import json, sys
for line in sys.stdin:
    msg = json.loads(line.strip().rstrip(','))
    if '<tool_call>' in msg['content']:
        before = msg['content'].split('<tool_call>')[0].strip()
        if before:
            print(f'WARNING: Preamble found: {before[:50]}')
"
```

**Expected:**
- 1053 train examples
- 111 valid examples
- 0 warnings about remaining preambles

---

### Step 2: Train Phase 27 Cleaned Model (4-6 hours)

Create training script:

```bash
cat > scripts/train_phase27_cleaned.sh << 'EOF'
#!/bin/bash
set -e

echo "Training Phase 27 Cleaned (no preambles)"
echo "========================================"
echo ""

# Training parameters (same as Phase 27)
MODEL="mlx-community/Qwen2.5-Coder-32B-Instruct-4bit"
DATA="data/phase27_cleaned"
OUTPUT="adapters_phase27_cleaned"
ITERS=800
BATCH=1
LR=1e-4
LAYERS=8

echo "Model: $MODEL"
echo "Data: $DATA"
echo "Output: $OUTPUT"
echo "Iterations: $ITERS"
echo "Batch size: $BATCH"
echo "Learning rate: $LR"
echo "Layers to train: $LAYERS"
echo ""

# Train
uv run mlx_lm.lora \
  --model "$MODEL" \
  --train \
  --data "$DATA" \
  --adapter-path "$OUTPUT" \
  --iters "$ITERS" \
  --batch-size "$BATCH" \
  --learning-rate "$LR" \
  --lora-layers "$LAYERS"

echo ""
echo "✅ Training complete!"
echo "Adapter saved to: $OUTPUT"
echo ""
echo "Next: Fuse and quantize the model"
echo "  ./scripts/fuse_phase27_cleaned.sh"
EOF

chmod +x scripts/train_phase27_cleaned.sh
```

**Run training:**

```bash
./scripts/train_phase27_cleaned.sh 2>&1 | tee logs/train_phase27_cleaned.log
```

**Expected:**
- Initial val loss: ~3.0-3.5
- Final val loss: ~0.4-0.6
- Final train loss: ~0.08-0.15
- Time: 4-6 hours on M1/M2 Mac
- Output: `adapters_phase27_cleaned/` (~2 GB)

---

### Step 3: Fuse and Quantize (1-2 hours)

Create fusion script:

```bash
cat > scripts/fuse_phase27_cleaned.sh << 'EOF'
#!/bin/bash
set -e

echo "Fusing Phase 27 Cleaned Model"
echo "=============================="
echo ""

BASE="mlx-community/Qwen2.5-Coder-32B-Instruct-4bit"
ADAPTER="adapters_phase27_cleaned"
OUTPUT_F16="fused_model_qwen3_phase27_cleaned_f16"
OUTPUT_5BIT="fused_model_qwen3_phase27_cleaned_5bit"

# Step 1: Fuse to float16 (with dequantization)
echo "Step 1: Fusing to float16..."
uv run python -m mlx_lm.fuse \
  --model "$BASE" \
  --adapter-path "$ADAPTER" \
  --save-path "$OUTPUT_F16" \
  --dequantize

echo "✅ Float16 model created: $OUTPUT_F16"
echo ""

# Step 2: Quantize to 5-bit
echo "Step 2: Quantizing to 5-bit..."
uv run python -m mlx_lm.convert \
  --hf-path "$OUTPUT_F16" \
  --mlx-path "$OUTPUT_5BIT" \
  --quantize \
  --q-bits 5

echo "✅ 5-bit model created: $OUTPUT_5BIT"
echo ""
echo "Next: Validate the model"
echo "  python scripts/validate_model.py $OUTPUT_5BIT"
EOF

chmod +x scripts/fuse_phase27_cleaned.sh
```

**Run fusion:**

```bash
./scripts/fuse_phase27_cleaned.sh 2>&1 | tee logs/fuse_phase27_cleaned.log
```

**Expected:**
- `fused_model_qwen3_phase27_cleaned_f16/` (~57 GB, can delete after quantization)
- `fused_model_qwen3_phase27_cleaned_5bit/` (~20 GB) **← Production model**
- Time: 1-2 hours

---

### Step 4: Validate Cleaned Model (5 min)

Run full 57-query validation suite:

```bash
uv run python scripts/validate_model.py \
  fused_model_qwen3_phase27_cleaned_5bit/ \
  --output validation_phase27_cleaned.json \
  2>&1 | tee validation_phase27_cleaned.log
```

**Expected Results:**

| Category | Phase 27 Augmented | Phase 27 Cleaned (Target) |
|----------|-------------------|---------------------------|
| direct_answers | 100% (5/5) | 100% (5/5) |
| edge_cases | 80% (4/5) | 80% (4/5) |
| tool_identity | 80% (4/5) | 80% (4/5) |
| **single_tool** | **30% (3/10)** | **≥80% (8/10)** ✅ |
| **field_access** | **30% (3/10)** | **≥70% (7/10)** ✅ |
| **cross_tool** | **20% (2/10)** | **≥50% (5/10)** ✅ |
| **multi_turn** | **42% (5/12)** | **≥60% (7/12)** ✅ |
| **OVERALL** | **46% (26/57)** | **≥75% (43/57)** ✅ |

**Key improvements expected:**
- ✅ Git tools: 0% → 100% (all 8 queries)
- ✅ LSP tools (document_symbols, workspace_symbols): 0% → 100% (3 queries)
- ✅ Specific typecheck queries: 0% → 100% (2 queries)
- ✅ Multi-turn turn 2: No more early EOS

**Projected gain:** +29 points (46% → 75%)

---

### Step 5: Compare Results

Generate comparison report:

```bash
cat > scripts/compare_phase27_models.py << 'EOF'
#!/usr/bin/env python3
"""Compare Phase 27 augmented vs cleaned validation results."""
import json

with open('validation_phase27_baseline.json') as f:
    augmented = json.load(f)

with open('validation_phase27_cleaned.json') as f:
    cleaned = json.load(f)

print("Phase 27 Model Comparison")
print("=" * 70)
print()

# Overall
aug_strict = augmented['summary']['strict_pct']
clean_strict = cleaned['summary']['strict_pct']
delta = clean_strict - aug_strict

print(f"Overall Strict Accuracy:")
print(f"  Augmented: {aug_strict:.1f}%")
print(f"  Cleaned:   {clean_strict:.1f}%")
print(f"  Improvement: {delta:+.1f} points")
print()

# By category
print("Category Breakdown:")
print(f"{'Category':<20} {'Augmented':<12} {'Cleaned':<12} {'Delta'}")
print("-" * 70)

for cat in sorted(augmented['summary']['categories'].keys()):
    aug_pct = augmented['summary']['categories'][cat]['strict_pct']
    clean_pct = cleaned['summary']['categories'][cat]['strict_pct']
    delta = clean_pct - aug_pct
    symbol = "✅" if delta >= 20 else ("➡️" if delta >= 0 else "❌")
    print(f"{cat:<20} {aug_pct:>5.0f}% {clean_pct:>10.0f}% {delta:>8.0f}  {symbol}")

print()

# Success threshold
if clean_strict >= 75:
    print("✅ SUCCESS: Phase 27 cleaned meets 75% threshold")
    print("   Ready for production deployment")
elif clean_strict >= 65:
    print("⚠️  PARTIAL: 65-75% range, close to target")
    print("   Consider additional targeted examples")
else:
    print("❌ INSUFFICIENT: <65% accuracy")
    print("   Need deeper investigation")
EOF

chmod +x scripts/compare_phase27_models.py
uv run python scripts/compare_phase27_models.py
```

---

### Step 6: Decision Matrix

Based on Phase 27 cleaned validation results:

#### If ≥80% strict accuracy → DEPLOY
- Update `MEMORY.md` with Phase 27 cleaned as production model
- Archive Phase 27 augmented
- Document in `docs/phase27-cleaned-deployment.md`
- Consider this the baseline for Phase 28

#### If 70-79% strict accuracy → AUGMENT
- Good progress, but needs targeted fixes
- Generate 50-100 examples for weakest categories
- Quick retrain (Phase 27.5) targeting specific gaps
- Re-validate

#### If <70% strict accuracy → INVESTIGATE
- Preamble removal didn't solve the full problem
- Deep dive into remaining failures
- May need format audit, different approach

---

## Timeline

| Step | Duration | Cumulative |
|------|----------|-----------|
| 1. Review cleaned data | 5 min | 5 min |
| 2. Train model | 4-6 hours | 4-6 hours |
| 3. Fuse & quantize | 1-2 hours | 5-8 hours |
| 4. Validate | 5 min | 5-8 hours |
| 5. Compare & analyze | 15 min | 5-8 hours |

**Total time:** 5-8 hours (mostly unattended training)

---

## Success Criteria

### Minimum Viable (75% threshold)
- ✅ Overall strict accuracy ≥75%
- ✅ Git tools ≥90% (up from 0%)
- ✅ LSP tools ≥70% (up from 38%)
- ✅ Multi-turn ≥60% (up from 42%)

### Stretch Goals (85% threshold)
- 🎯 Overall strict accuracy ≥85%
- 🎯 All categories ≥80%
- 🎯 Multi-turn cross-tool chaining ≥70%

---

## Risk Mitigation

### If Training Fails
- Check data format: `head data/phase27_cleaned/train.jsonl | python3 -m json.tool`
- Verify no preambles: `grep '"Let me"' data/phase27_cleaned/train.jsonl`
- Compare sizes: `wc -l data/phase27_{augmented,cleaned}/train.jsonl`

### If Validation Shows <70%
- Check if preamble issue persists: Test queries manually with verbose output
- Look for new failure patterns: Analyze `validation_phase27_cleaned.json`
- Consider alternative fixes: Remove preambles from base model responses too

### If Disk Space Issues
- Delete intermediate models: `rm -rf fused_model_qwen3_phase27_cleaned_f16/`
- Archive old adapters: `mv adapters_phase27_augmented archives/`
- Clean up logs: `rm logs/*.log` (keep only latest)

---

## Files Created This Session

### Documentation
- `docs/multi-turn-validation-implementation.md` - Implementation details
- `docs/multi-turn-validation-complete.md` - Comprehensive reference
- `docs/phase27-augmented-validation-analysis.md` - Failure analysis
- `docs/phase27-augmented-root-cause-analysis.md` - Root cause + fix
- `docs/next-steps-phase27-cleaned.md` - This file

### Scripts
- `scripts/validate_model.py` - Extended with 12 multi-turn queries
- `scripts/remove_preambles.py` - Preamble removal tool
- `scripts/train_phase27_cleaned.sh` - Training script (to be created)
- `scripts/fuse_phase27_cleaned.sh` - Fusion script (to be created)
- `scripts/compare_phase27_models.py` - Comparison script (to be created)

### Data
- `data/phase27_cleaned/train.jsonl` - 1053 examples, 0 preambles
- `data/phase27_cleaned/valid.jsonl` - 111 examples, 0 preambles

### Results
- `validation_phase27_baseline.json` - Augmented model results (46%)
- `validation_phase27_baseline.log` - Human-readable output

---

## Next Immediate Action

**Start training:**

```bash
# Create and run training script
./scripts/train_phase27_cleaned.sh 2>&1 | tee logs/train_phase27_cleaned.log

# While training (4-6 hours), review:
# - Multi-turn validation implementation
# - Root cause analysis
# - Expected improvements

# After training completes:
# - Fuse & quantize (1-2 hours)
# - Validate (5 min)
# - Compare results
# - Deploy if ≥75%
```

**Estimated completion:** 6-8 hours from now (mostly unattended)
**Expected outcome:** 75-80% strict accuracy (up from 46%)
**Confidence:** HIGH (root cause clearly identified and fixed)
