# Model Performance Tracker

**Purpose:** Track model size, memory usage, and performance improvements across training phases.

**Last Updated:** February 13, 2026 - Phase 1 Complete

---

## Quick Reference Table - All Phases

| System | Model Size | Memory (Inference) | Speed | Autonomous Tools? | Accuracy | Status |
|--------|------------|-------------------|-------|-------------------|----------|--------|
| **Claude Code** | 0 (cloud) | 0 GB local | **2.41s** ⚡ | ✅ Yes | 100% | Baseline |
| **30B Baseline** | ~60 GB | ~16 GB | **~27s** | ✅ Yes | 100% | Too slow |
| **7B Phase 0** | 14 GB + 44MB adapter | ~6-8 GB | **21.06s** | ❌ No (memorized) | 100% | Broken |
| **7B Phase 1** | 14 GB + 44MB adapter | Unknown | **N/A** (infinite loop) | ✅ **Yes!** (but loops) | N/A (no answer) | Progress! |

### Phase 0 Baseline (Original Training)

### Detailed Metrics

#### **Model Size**
- **30B:** ~60 GB (full model)
- **7B + LoRA:** 14.044 GB total (77% smaller than 30B)
  - 7B base: 14 GB (4-bit quantized)
  - LoRA adapter: 44 MB
- **Claude Code:** 0 GB local (cloud-based)

#### **Memory Usage**
- **30B:** ~16 GB RAM (❌ **crashed system**)
- **7B Distilled:** ~6-8 GB RAM (50-60% reduction vs 30B)
  - Training peak: 23.63 GB
  - Inference: ~6-8 GB
- **Claude Code:** 0 GB local

#### **Speed Performance** (Protocol search query)
- **Claude Code:** 2.41s (baseline) - **11.2x faster than 30B**
- **7B Distilled:** 21.06s - 1.3x faster than 30B, but 8.7x slower than Claude
- **30B:** ~27s

#### **Training Costs**
- **7B LoRA Training:**
  - Duration: 11 minutes (50 iterations)
  - Dataset: 69 examples
  - Loss reduction: 81% (1.269 → 0.246)
  - Peak memory: 23.63 GB
  - Adapter size: 44 MB

### Key Findings

**Claude Code:**
- ✅ Fastest (2.41s)
- ✅ No local resources
- ✅ Fully autonomous tool use
- ✅ Works on any codebase
- ❌ Requires API key/internet

**7B Distilled Model:**
- ✅ 77% smaller than 30B
- ✅ 50-60% less memory than 30B
- ✅ Accurate (100%)
- ❌ **Memorized patterns** instead of learning autonomous tool use
- ❌ Only works on familiar codebases
- ❌ Training data too small (69 examples from one codebase)

**30B Model:**
- ✅ Autonomous tool use
- ✅ Works on any codebase
- ❌ 11.2x slower than Claude Code
- ❌ 16GB RAM (system crash risk)
- ❌ Not production viable

### Critical Issue Discovered

**The 7B model memorized instead of learning:**
- Gave correct answers directly without calling tools
- Learned "this codebase has these protocols" not "how to search any codebase"
- Root cause: Insufficient training data (need 1,000-5,000 examples from 20+ codebases)

### Test Query Used
"Which classes in this codebase subclass from Protocol?"

**Expected behavior:** Search codebase with grep/find tools, analyze results, provide answer
**Actual 7B behavior:** Direct answer without tool calls (memorization)

---

## Phase 1: Training Data Pipeline Fix ✅ COMPLETED (With Issues)

**Date:** February 13, 2026
**Goal:** Fix critical tool-call format mismatch and prepare for proper tool-calling training
**Status:** Training successful, but discovered new critical bug

### Changes Made

1. **Fixed tool-call format:**
   - Changed from `"tool"` key to `"name"` key (matches parser)
   - Updated 30 hand-authored examples
   - Regenerated 69 converted examples

2. **Added converter to training pipeline:**
   - `train_lora.sh` now runs converter before training
   - `run_full_distillation.sh` includes converter step
   - Ensures correct format reaches mlx_lm.lora

3. **Wired stop_sequences:**
   - Local agents default to QWEN_STOP_SEQUENCES
   - Added to config and factory
   - (Results: NOT working - still generating garbage tokens)

4. **Memory requirements:**
   - Had to use batch_size=1 (not 2) to avoid OOM
   - Actual peak: 18.902 GB
   - batch_size=2 crashed with "Insufficient Memory" error

### Actual Results

| Metric | Phase 0 | Phase 1 Actual | Change | Status |
|--------|---------|----------------|--------|--------|
| Training loss | 1.269 → 0.246 | 1.077 → 0.096 | Better (91% vs 81%) | ✅ Improved |
| Training peak memory | 23.63 GB | 18.902 GB | -20% (not -40%) | ⚠️ Less than expected |
| Batch size | 4 | 1 (not 2!) | -75% | ❌ Slower training |
| Training iterations | 50 | 206 | 4x more | ⚠️ Took longer |
| **Autonomous tools?** | ❌ No (memorized) | ✅ **YES!** | Fixed! | 🎉 **BREAKTHROUGH** |
| Tool execution | Direct answer | 20+ tool calls | Works but loops | ⚠️ New bug |
| Stop sequences | N/A | Not working | No improvement | ❌ Failed |

### 🎉 BREAKTHROUGH: Model Uses Tools!

**Phase 0 behavior (broken):**
```
User: "Which classes subclass from Protocol?"
Model: "Found 6 protocols: HttpAppFactory, Client, Agent..." [Direct answer - memorized]
```

**Phase 1 behavior (fixed but looping):**
```
User: "Which classes subclass from Protocol?"
Model: run_command(grep -r 'class.*Protocol' .)
Model: run_command(grep -r 'class.*Protocol' .)  [Repeats 20+ times]
Model: run_command({})  [Empty args]
Model: [Never gives final answer - stuck in loop]
```

### Critical Issues Discovered

1. **✅ FIXED: Memorization → Tool Usage**
   - Model now calls tools instead of memorizing
   - Uses appropriate commands (`find`, `grep`)
   - Correctly formatted tool calls with `"name"` key

2. **❌ NEW BUG: Infinite Tool Loop**
   - Model calls same tool 20+ times
   - Doesn't process tool results
   - Never stops to give final answer
   - Some calls have empty arguments `{}`

3. **❌ Stop Sequences Don't Work**
   - Still generating `<|im_end|>` garbage tokens
   - No speedup observed
   - Need to investigate why stop_sequences aren't being applied

4. **❌ Memory Higher Than Expected**
   - Needed batch_size=1 instead of 2
   - Peak 18.9 GB instead of target 12-14 GB
   - 7B model + training might need more optimization

### Root Cause Analysis

**Why infinite loop?**

The training data uses **placeholder tool results**:
```
Tool result: [Tool execution completed]
```

The model learned:
1. ✅ When to call tools
2. ✅ How to format tool calls
3. ❌ How to interpret results
4. ❌ When to stop and give answer

**Evidence:** Converter warning we ignored:
```
⚠️  Note: Current data uses placeholder tool results.
   Run generate_training_data.py with updated capture logic for real results.
```

### Training Details

**Configuration:**
- Model: Qwen2.5-Coder-7B-Instruct-4bit
- Batch size: 1 (down from planned 2)
- Learning rate: 1e-4
- LoRA rank: 16
- Iterations: 206 (up from 50)
- Training time: ~20 minutes

**Loss Progression:**
- Train loss: 1.077 → 0.096 (91% reduction)
- Val loss: 2.267 → 0.436 (81% reduction)
- Test loss: 0.899, Test ppl: 2.458

**Memory:**
- Peak: 18.902 GB
- Training tokens: 117,940

### Next Steps (Phase 2)

**Fix the infinite loop:**
1. Generate training data with REAL tool results (not placeholders)
2. Update `generate_training_data.py` to capture actual outputs
3. Train model to recognize when tools have provided sufficient info
4. Add examples of "now I have enough info, here's the answer" pattern

**Fix stop sequences:**
5. Debug why QWEN_STOP_SEQUENCES aren't being applied
6. Verify they're passed to model inference correctly
7. Test with simple example to confirm they work

**Optimize memory:**
8. Investigate why batch_size=2 causes OOM
9. Try reducing sequence length or other parameters
10. Consider using 3-bit quantization

---

## Future Phases (Planned)

### Phase 2: Scale Up Training Data (TODO)
- **Goal:** Generate 1,000+ examples from 10+ diverse codebases
- **Target:** Achieve autonomous tool use (not memorization)
- **Expected:** Slower than Claude, but works on new codebases

### Phase 3: Optimize Inference Speed (TODO)
- **Optimizations to try:**
  - Fix stop token handling (~15s, 1.4x speedup)
  - Speculative decoding (~8s, 2.6x speedup)
  - KV cache optimization (~7s, 3x speedup)
  - Train for conciseness (~5s, 4.2x speedup)
- **Target:** 6-8 seconds (still slower than Claude's 2.4s, but acceptable)

### Phase 4: Hybrid Architecture (TODO)
- **Goal:** Match Claude Code speed while staying offline
- **Approach:**
  - Intent classifier (<0.1s)
  - Direct tool executor (~0.5s)
  - Response formatter with 7B (~2s)
  - Total: ~3s
- **Target:** <3 seconds, fully autonomous, offline

---

## Metrics to Track Each Phase

For consistency, measure each phase with the same test suite:

### Standard Test Query
"Which classes in this codebase subclass from Protocol?"

### Metrics to Record
1. **Speed:** Time from query to final answer
2. **Tool calls:** Number and type of tools used
3. **Autonomous:** Did model decide to use tools? (Yes/No)
4. **Accuracy:** Found all protocol classes? (%)
5. **Memory:** Peak inference memory (GB)
6. **Model size:** Total disk space (GB)
7. **Training cost:** Time, peak memory, examples used

### Additional Test Queries (For Phase 2+)
1. "Find all async functions in this codebase"
2. "What files import the requests library?"
3. "Show me all dataclasses"
4. "List TODO comments in the source code"

---

## Version History

- **2026-02-13:** Phase 0 baseline established, Phase 1 fixes in progress
- **2026-02-12:** Initial knowledge distillation experiment (7B from 30B)
- **2026-02-12:** 30B vs Claude Code benchmark completed

---

## Related Documentation

- `KNOWLEDGE_DISTILLATION_SUMMARY.md` - Full Phase 0 experiment details
- `BENCHMARK_COMPARISON.md` - Initial 30B vs Claude Code analysis
- `TRAINING_SUMMARY.md` - 1.5B model evaluation results
- `docs/research/training-journal.md` - Detailed training history
