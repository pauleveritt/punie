# Knowledge Distillation Experiment: 30B → 7B

**Date:** February 12-13, 2026
**Status:** ✅ Complete
**Goal:** Distill autonomous tool-using behavior from 30B model into 7B model

---

## Executive Summary

Successfully trained a 7B model using knowledge distillation from a 30B teacher model. The experiment validated that smaller models CAN learn from larger models, though with important limitations discovered.

### Key Results

| Metric | Result | Target | Status |
|--------|--------|--------|--------|
| Training completed | ✅ Yes | Yes | ✅ Met |
| Training loss reduction | 81% (1.269→0.246) | Decreasing | ✅ Met |
| Model size | 44MB adapter | <100MB | ✅ Met |
| Inference time | 21.06s | <30s | ✅ Met |
| Accuracy | 100% (on training codebase) | >75% | ✅ Exceeded |
| **Autonomous tool use** | ❌ No (memorization) | Yes | ❌ **Failed** |

**Critical Finding:** Model learned to answer correctly but by **memorizing patterns** rather than **using tools autonomously**.

---

## The Journey

### Phase 1: Data Generation (Completed: 00:37 AM)

**Goal:** Generate 100 training examples using 30B as teacher
**Result:** 69 examples generated (stopped early due to quality/time constraints)

**Challenges Faced:**
1. **Initial hang:** Script had no timeout on queries → Added 90s timeout per query
2. **Slow generation:** 5 concurrent queries → Reduced to 2 for stability
3. **Rate:** ~1 example/minute → Total time ~70 minutes

**Training Data Scope:**
- ✅ **Python only** (Protocol searches, imports, functions, dataclasses)
- ❌ HTML/CSS/JS removed (insufficient examples generated)

**Files Generated:**
- `data/training_examples_1k.jsonl` - 69 raw examples
- `data/mlx_format/train.jsonl` - 62 training examples (90%)
- `data/mlx_format/valid.jsonl` - 7 validation examples (10%)
- `data/mlx_format/test.jsonl` - 7 test examples (copy of valid)

---

### Phase 2: LoRA Training (Completed: 07:20 AM)

**Goal:** Fine-tune 7B model with LoRA adapters
**Duration:** 11 minutes (50 iterations)

**Configuration:**
```yaml
Model: Qwen2.5-Coder-7B-Instruct-4bit
Training examples: 62
Validation examples: 7
Batch size: 4
Learning rate: 1e-4
LoRA layers: 16
Epochs: 3
Iterations: 50
```

**Challenges Faced:**
1. **Wrong argument:** `--lora-layers` → Fixed to `--num-layers`
2. **Wrong data format:** Custom JSON → Converted to MLX instruction format
3. **Missing test set:** Added test.jsonl (copied from valid)

**Training Results:**
- Training loss: 1.269 → 0.246 (81% improvement) ✅
- Validation loss: 2.182 → 1.835 (16% improvement) ✅
- Test loss: 1.762, Test perplexity: 5.821 ✅
- Peak memory: 23.63 GB
- Training speed: 0.075-0.093 iter/sec

**Adapter Size:** 44MB (0.151% of model parameters - 11.5M trainable)

---

### Phase 3: Evaluation (Completed: 07:34 AM)

**Test Query:** "Which classes in this codebase subclass from Protocol?"

**7B Distilled Results:**
- Time: 21.06s
- Accuracy: 100% (found all 7 Protocol classes)
- Autonomous tool use: ❌ **NO** - Gave correct answer but didn't use tools
- Method: Appeared to memorize codebase patterns from training

**Comparison:**

| System | Time | Autonomous? | Method | Accuracy |
|--------|------|-------------|--------|----------|
| **Claude Code** | **2.41s** ⚡ | ✅ Yes | Direct tool use (Grep) | 100% |
| **7B Distilled** | **21.06s** | ❌ No | Memorization | 100% |
| **30B Baseline** | **~27s** | ✅ Yes | Tool calls (search+read) | 100% |

---

## Technical Analysis

### What Worked ✅

1. **Training pipeline:** Successfully trained LoRA adapter on local hardware
2. **Loss reduction:** Model clearly learned patterns (81% loss reduction)
3. **Accuracy:** 100% correct on the specific test query
4. **Speed:** 21s is faster than 30B's 27s baseline
5. **Size:** 44MB adapter is highly portable and efficient

### What Didn't Work ❌

1. **Autonomous tool use:** Model didn't learn to call tools
2. **Generalization:** Memorized this codebase instead of learning to search
3. **Stop tokens:** Generated garbage tokens at end of response
4. **Training scope:** Only 69 examples from one codebase (insufficient)

### Root Cause Analysis

**Why the model memorized instead of learning tool use:**

1. **Dataset too small:** 69 examples insufficient for generalization
   - Need: 1,000+ examples from diverse codebases

2. **Dataset too narrow:** All from same codebase
   - Model learned "this codebase has these protocols"
   - Didn't learn "how to search any codebase for protocols"

3. **Training format:** Included answers but not tool execution flow
   - Model saw: Query → Answer
   - Needed: Query → Tool calls → Results → Answer

4. **Model capacity:** 7B may be too small for complex reasoning
   - 30B has 4x more parameters
   - Reasoning ability may not compress to 7B

---

## Performance Metrics

### File Size Comparison

| Component | Size | Notes |
|-----------|------|-------|
| 30B Model | ~60 GB | Full model |
| 7B Model | ~14 GB | 4-bit quantized |
| LoRA Adapter | **44 MB** | **Only this needed on top of 7B** |
| **Total (7B+LoRA)** | **14.044 GB** | **77% smaller than 30B** |

### Memory Usage

| Model | Training Peak | Inference Est. | Reduction |
|-------|---------------|----------------|-----------|
| 30B | N/A | ~16 GB | Baseline |
| 7B+LoRA | 23.63 GB | ~6-8 GB | **50-60% less** |

### Speed Comparison

| System | Time | Speedup vs 30B | Speedup vs Claude |
|--------|------|----------------|-------------------|
| Claude Code | 2.41s | **11.2x faster** | 1x (baseline) |
| 7B Distilled | 21.06s | 1.3x faster | 8.7x slower |
| 30B Baseline | ~27s | 1x (baseline) | 11.2x slower |

---

## Lessons Learned

### For Future Distillation Attempts

1. **Scale up data:**
   - Generate 1,000-5,000 examples minimum
   - Use diverse codebases (10+ different projects)
   - Include positive AND negative examples (when to use tools vs not)

2. **Better training format:**
   - Capture actual tool execution traces
   - Train model to predict tool calls explicitly
   - Use reinforcement learning from tool feedback

3. **Consider larger base models:**
   - 7B may be too small for autonomous reasoning
   - Try 14B or 20B models
   - Or accept that some capabilities don't compress

4. **Validate differently:**
   - Test on NEW codebases (not training data)
   - Measure tool usage rate, not just accuracy
   - Check for hallucination vs real tool use

### Technical Improvements Identified

1. **Stop token handling:** Fix repeated `<|im_end|>` tokens
2. **Response brevity:** Train for concise answers
3. **Speculative decoding:** Could achieve 2-3x speedup
4. **KV cache optimization:** 10-20% speedup potential

---

## Future Optimization Paths

### Speed Improvements (Estimated)

| Optimization | Estimated Time | Speedup | Difficulty |
|--------------|----------------|---------|------------|
| Current | 21s | 1x | - |
| + Fix stop tokens | ~15s | 1.4x | Easy |
| + Speculative decoding | ~8s | 2.6x | Medium |
| + KV cache optimization | ~7s | 3x | Easy |
| + Train for conciseness | ~5s | 4.2x | Medium |
| + 3-bit quantization | ~4s | 5.3x | Easy |

**Realistic target with quick wins:** 6-8 seconds

### Architectural Improvements

**Hybrid approach** (to match Claude Code speed):
```
User query
  ↓
Intent classifier (tiny model, <0.1s)
  ↓
Tool executor (direct, ~0.5s)
  ↓
Response formatter (7B, ~2s)
  ↓
Total: ~3s
```

---

## Files Created

### Scripts
- ✅ `scripts/generate_training_data.py` - Data generation with 90s timeout
- ✅ `scripts/convert_training_data.py` - Format converter (custom → MLX)
- ✅ `scripts/train_lora.sh` - LoRA training script
- ✅ `scripts/run_full_distillation.sh` - Full pipeline orchestration
- ✅ `scripts/compare_distilled.py` - Evaluation script

### Data
- ✅ `data/training_examples_1k.jsonl` - 69 raw training examples
- ✅ `data/mlx_format/` - MLX-formatted train/valid/test sets

### Models
- ✅ `models/qwen25-7b-distilled/adapters/` - LoRA adapter weights (44MB)

### Documentation
- ✅ `KNOWLEDGE_DISTILLATION_PLAN.md` - Original strategic plan
- ✅ `DATA_GENERATION_STATUS.md` - Phase 1 details
- ✅ `DISTILLATION_WORKFLOW.md` - Operational guide
- ✅ `OVERNIGHT_STATUS.md` - Monitoring guide
- ✅ `KNOWLEDGE_DISTILLATION_SUMMARY.md` - This file (final summary)

### Logs (Not committed)
- `logs/data_generation_*.log`
- `logs/training_*.log`
- `logs/overnight_pipeline_*.log`
- `logs/server_7b_distilled.log`

---

## Conclusion

### What We Proved ✅

1. **Knowledge distillation is viable** - Model learned patterns from 30B
2. **LoRA is efficient** - Only 44MB adapter needed
3. **Training works on M1 Mac** - 11 minutes for 69 examples
4. **Pipeline automation works** - Unattended overnight execution successful

### What We Disproved ❌

1. **Small datasets are sufficient** - 69 examples → memorization, not learning
2. **7B can match 30B reasoning** - May need larger models
3. **Simple format is enough** - Need explicit tool execution traces

### Verdict

**Partial success:** The experiment validated the technique but revealed the need for significantly more scale. The 7B model learned to answer questions about this specific codebase accurately, but didn't generalize to autonomous tool use on new codebases.

**For production use:**
- **Online + Fast:** Use Claude Code (2.4s, fully autonomous)
- **Offline + Familiar codebase:** Use 7B distilled (21s, accurate by memorization)
- **Offline + New codebases:** Use 30B (27s, truly autonomous)

**To achieve true autonomous distillation:**
- Generate 5,000+ examples from 20+ diverse codebases
- Train with explicit tool call prediction
- Consider 14B+ base models
- Validate on completely unseen codebases

---

**Experiment Date:** February 12-13, 2026
**Total Time:** ~16 hours (overnight)
**Final Status:** ✅ Complete, valuable learnings documented
