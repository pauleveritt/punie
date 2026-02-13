# Model Performance Tracker

**Purpose:** Track model size, memory usage, and performance improvements across training phases.

**Last Updated:** February 13, 2026

---

## Current Baseline (Phase 0)

### Quick Reference Table

| System | Model Size | Memory (Inference) | Speed | Autonomous Tools? | Accuracy |
|--------|------------|-------------------|-------|-------------------|----------|
| **Claude Code** | 0 (cloud) | 0 GB local | **2.41s** ⚡ | ✅ Yes | 100% |
| **7B Distilled** | 14 GB + 44MB adapter | ~6-8 GB | **21.06s** | ❌ No (memorized) | 100% |
| **30B Baseline** | ~60 GB | ~16 GB | **~27s** | ✅ Yes | 100% |

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

## Phase 1: Training Data Pipeline Fix (In Progress)

**Date:** February 13, 2026
**Goal:** Fix critical tool-call format mismatch and prepare for proper tool-calling training

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
   - Should prevent garbage token generation
   - Expected 30% speedup

4. **Reduced memory requirements:**
   - Batch size: 4 → 2
   - Expected peak: ~12-14 GB (down from 23 GB)
   - Should fit on 16GB Mac without swap

### Expected Improvements

| Metric | Phase 0 | Phase 1 Target | Improvement |
|--------|---------|----------------|-------------|
| Training peak memory | 23.63 GB | ~12-14 GB | -40% |
| Inference speed | 21.06s | ~15s | +30% (stop tokens) |
| Tool-call format | Broken | Fixed | ✅ |
| Converter in pipeline | Missing | Added | ✅ |

### Next Steps

1. Re-run training with fixed pipeline
2. Measure actual memory usage
3. Test inference speed with stop sequences
4. Verify tool-call format is preserved
5. Update this tracker with results

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
