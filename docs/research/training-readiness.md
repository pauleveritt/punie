# LoRA Training Readiness Summary

**Date:** February 12, 2026
**Status:** ✅ Ready to Resume Training
**Confidence Level:** HIGH (evaluation pipeline verified)

## Pipeline Verification Complete

### What We Verified

1. ✅ **Parser Functionality**
   - Handles 4 different tool call formats
   - 17 comprehensive tests, all passing
   - Multi-format support for future-proofing

2. ✅ **Evaluation Accuracy**
   - Baseline metrics established for both models
   - Tool calling detection working (83.3% on both models)
   - HTML reports generating correctly
   - Scores can be trusted

3. ✅ **Training Templates**
   - Aligned with parser expectations
   - Use `<tool_call>{"name": ...}</tool_call>` format
   - Will produce parsable output when fine-tuned

4. ✅ **Model Selection**
   - Tested both 1.5B and 30B models
   - Baseline performance measured
   - Format differences understood

## Model Recommendation: Use 1.5B for Training

**Qwen2.5-Coder-1.5B-Instruct-4bit** is recommended for LoRA training:

### Performance (Better than 30B!)
- Overall: **92.9%** vs 75.0% (30B)
- Code generation: **100%** vs 87.5%
- Reasoning: **100%** vs 50.0%
- Tool calling: **83.3%** (same as 30B)

### Practical Benefits
- **Size:** 839 MB vs 16 GB (19x smaller)
- **Speed:** Faster loading, faster training iterations
- **Memory:** More headroom for larger LoRA ranks
- **Cost:** Less GPU time, more experiments possible

### Training Implications
- Baseline already strong (92.9% overall)
- Room for improvement in tool calling (83.3% → goal: 100%)
- Training should focus on tool calling accuracy
- Can experiment with larger LoRA ranks due to smaller model

## Available Resources

### Datasets

**Tool-Calling Focused:**
- `data/qwen-tool-calling/` - 10 examples (8 train, 1 valid, 1 test)
- `data/synthetic/` - Synthetic tool calling examples
- `data/realistic-training/` - Realistic scenarios

**General Code:**
- `data/downloaded/` - Downloaded code examples
- `data/hand-authored/` - Manually crafted examples

### Existing Adapters

**Already Trained (on 1.5B):**
- `adapters/qwen-tool-calling/` - 20 MB adapter
- `adapters/tool-calling-synthetic/` - Trained on synthetic data
- `adapters/successful-demo/` - Demo adapter
- `adapters/baseline-diverse-python-5k/` - Large Python dataset adapter
- `adapters/glaive-function-calling/` - Function calling dataset

**Note:** All existing adapters were trained on 1.5B model, not 30B.

## Training Strategy Recommendations

### Option 1: Evaluate Existing Adapters (Quick Win)

**Goal:** See if existing training already improved tool calling.

**Steps:**
```bash
# Evaluate qwen-tool-calling adapter
uv run punie eval \
  --model mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit \
  --adapter adapters/qwen-tool-calling \
  --port 8766

# Evaluate tool-calling-synthetic adapter
uv run punie eval \
  --model mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit \
  --adapter adapters/tool-calling-synthetic \
  --port 8766
```

**Expected Outcome:**
- Tool calling score should be > 83.3% (baseline)
- Target: 90-100% tool calling accuracy
- If met, training is complete! If not, proceed to Option 2.

### Option 2: Create High-Quality Tool Calling Dataset

**Goal:** Build a focused dataset that teaches the model our exact tool usage patterns.

**Requirements:**
- Examples must use `<tool_call>` format (matches training templates)
- Cover all 7 Punie tools (read_file, write_file, run_command, etc.)
- Include multi-step tool sequences
- Real-world scenarios from PyCharm workflow

**Tools:**
```bash
# Create dataset from templates
uv run python -c "
from pathlib import Path
from punie.training.tool_calling_templates import (
    create_read_file_example,
    create_write_file_example,
    create_run_command_example,
)
from punie.training.dataset import TrainingDataset
from punie.training.dataset_io import write_dataset

# Create examples (expand this!)
examples = [
    create_read_file_example(
        file_path='src/main.py',
        file_content='def main():\\n    print(\"Hello\")',
        user_question='What does main.py do?',
        assistant_answer='It defines a main function that prints Hello.',
    ),
    # Add more examples...
]

dataset = TrainingDataset(train=tuple(examples), valid=(), test=())
write_dataset(dataset, Path('data/punie-tools-focused'))
"

# Validate dataset
uv run punie dataset validate data/punie-tools-focused
```

### Option 3: Train New Adapter with Focused Data

**Goal:** Fine-tune specifically for perfect tool calling.

**Configuration:**
```bash
uv run punie train \
  data/punie-tools-focused \
  --model mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit \
  --iters 100 \
  --learning-rate 1e-5 \
  --lora-rank 16 \
  --batch-size 4
```

**Training Parameters (Recommended):**
- **Model:** Qwen2.5-Coder-1.5B-Instruct-4bit
- **Iterations:** 100 (start conservative)
- **Learning rate:** 1e-5 (standard for LoRA)
- **LoRA rank:** 16 (balance between capacity and speed)
- **Batch size:** 4 (fits in 32GB RAM)

**Monitoring:**
- Watch training loss (should decrease)
- Evaluate every 25 iterations
- Stop if validation loss increases (overfitting)

## Success Criteria

### Evaluation Metrics

**Target Scores (post-training):**
- Overall: ≥ 92.9% (maintain baseline)
- Tool calling: ≥ 95% (improvement from 83.3%)
- Code generation: ≥ 100% (maintain)
- Reasoning: ≥ 100% (maintain)

**Red Flags:**
- Overall score drops below 85% (regression)
- Tool calling doesn't improve (training not working)
- Model outputs wrong format (templates misaligned)

### Output Format Verification

After training, verify output format with diagnostic tool:
```bash
uv run python test_1.5b_tool_format.py
```

**Expected:** Model should output `<tool_call>` tags (matching templates), not code fences.

**If still code fences:** Training didn't override base model behavior. Options:
- Increase LoRA rank (16 → 32)
- Increase training iterations (100 → 200)
- Add more training examples
- Increase learning rate cautiously (1e-5 → 2e-5)

## Next Immediate Actions

1. **Evaluate existing adapters** (Option 1)
   - Quick check if training already achieved goal
   - Compare against 83.3% baseline

2. **If not satisfactory:**
   - Create focused tool-calling dataset (Option 2)
   - Train new adapter (Option 3)
   - Evaluate and iterate

3. **Document results:**
   - Update training-journal.md with results
   - Record adapter performance in cumulative table
   - Note which approach worked best

## Risk Assessment

### Low Risk
- Evaluation pipeline is verified (can trust metrics)
- Model selection backed by data (1.5B outperforms 30B)
- Training templates aligned with parser

### Medium Risk
- Dataset quality matters (garbage in, garbage out)
- Overfitting possible with small datasets
- Format alignment needs verification post-training

### Mitigation
- Start with existing adapters (low cost)
- Use validation set to detect overfitting early
- Run format diagnostic after training
- Keep training iterations conservative initially

## Files Ready for Use

**Test Scripts:**
- `test_tool_calling_deep.py` - Full pipeline verification
- `test_1.5b_tool_format.py` - Output format diagnostic

**Documentation:**
- `docs/research/deep-test-findings.md` - Complete analysis
- `docs/research/training-journal.md` - Phase 18 documented
- `docs/research/tool-call-parsing-restoration.md` - Parser restoration record

**Training Infrastructure:**
- `src/punie/training/tool_call_parser.py` - Multi-format parser
- `src/punie/training/tool_calling_templates.py` - Aligned templates
- `src/punie/cli.py` - train/eval commands ready

**Baseline Reports:**
- `eval_20260212-164452.html` - 30B baseline (75.0%)
- `eval_20260212-164709.html` - 1.5B baseline (92.9%)

## Conclusion

🎯 **All systems ready for LoRA training.**

The evaluation pipeline is verified, baseline metrics are established, and the path forward is clear. Start with evaluating existing adapters (quick wins), then proceed to focused training if needed.

**Confidence: HIGH** ✅
