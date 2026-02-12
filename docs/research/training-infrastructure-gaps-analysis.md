# Training Infrastructure - Gaps & Issues Analysis

**Date:** 2026-02-11
**Status:** Critical Review

## Executive Summary

We've built **comprehensive infrastructure** (156 tests, 21 modules) but there are **critical gaps** between what we built and what's actually needed for production use.

---

## ✅ What Works Well

### Strong Foundation
1. **Clean architecture** - Frozen dataclasses, pure functions, async subprocess management
2. **Comprehensive testing** - 156 tests, all passing, good coverage
3. **Type safety** - All code passes ty type checking
4. **CLI usability** - Clear commands, helpful output, good UX
5. **Documentation** - Well-documented with examples and demos

### Core Capabilities Present
- Server lifecycle management ✅
- Dataset validation and filtering ✅
- Training command building ✅
- Evaluation framework ✅
- HTML report generation ✅

---

## 🔴 Critical Gaps

### 1. **LoRA Rank Not Actually Configured**

**Issue:** We accept `lora_rank` in `LoRAConfig` but never pass it to the training command.

```python
# In lora_config.py:
lora_rank: int = 8  # Defined but...

# In train_runner.py:
# Note: LoRA rank is set via config file or defaults
# Can be extended later with --config flag
```

**Impact:** Can't actually tune LoRA rank, one of the most important hyperparameters.

**Fix needed:**
```python
# Option 1: Add --lora-rank flag to command
cmd.extend(["--lora-rank", str(config.lora_rank)])

# Option 2: Create adapter config file and pass --config
```

---

### 2. **30B Model Never Benchmarked**

**Issue:** Original plan said to benchmark Qwen3-Coder-30B-A3B-Instruct-4bit (the model that actually does tool calling), but we only tested with 1.5B.

**Why it matters:**
- 1.5B model is 1GB, easy to train
- 30B model is 15GB, may be too slow on M1 32GB
- **We don't know if the target model is trainable**

**Risk:** Build entire infrastructure for a model we can't actually train.

**Fix needed:** Run the benchmark:
```python
result = await run_training_benchmark(
    model_path="mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit",
    num_iters=10,
)
# Decision: <5 sec/iter = proceed, >60 sec/iter = pivot to 7B
```

---

### 3. **Temperature/Top-p Not Actually Configurable**

**Issue:** `InferenceGrid` defines temperature/top-p but we don't actually set them.

```python
# inference_tuning.py:
# Note: Temperature and top_p are typically set via model generation
# config, not server config. In a full implementation, these would
# be passed to the model during inference.
```

**Impact:** Can't actually tune these critical inference parameters.

**Fix needed:**
- Research mlx_lm.server generation config
- OR pass parameters via API calls (if supported)
- OR document as future work and remove from grid

---

### 4. **No Real Training Validation**

**Issue:** All our demos show 0% or negative scores because we use minimal iterations (10-20).

**Why it matters:**
- Haven't proven training actually works
- Haven't shown adapters improve performance
- Users might think the infrastructure is broken

**Fix needed:**
- Run ONE real training experiment:
  - 100+ examples
  - 100-200 iterations
  - Real evaluation suite
  - Demonstrate actual improvement

---

### 5. **Toucan Dataset Never Implemented**

**Issue:** Phase 16 plan mentioned Toucan (tool-calling trajectories) but we never built the downloader.

**Impact:** Missing a potentially valuable tool-calling dataset.

**Decision needed:**
- Implement Toucan downloader (requires ethical verification)
- OR remove from plan and stick with hand-authored examples
- OR document as future work

---

### 6. **Hand-Authored Examples Too Small**

**Issue:** Only 10 tool-calling examples generated.

**Training split:** 8 train / 1 valid / 1 test

**Why it matters:**
- Minimum for training is ~40 examples
- 8 examples is likely insufficient
- Can't meaningfully train on this data

**Fix needed:**
- Generate 50-100 hand-authored examples
- OR merge with general data (current approach)
- OR document limitation clearly

---

### 7. **No Adapter Fusion/Requantization**

**Issue:** Phase 16 mentioned fusing adapters and re-quantizing but never implemented.

```python
# Planned but not built:
# mlx_lm.fuse --model <base> --adapter-path <adapter> --output <fused>
# mlx_lm.convert --quantize --model <fused>
```

**Why it matters:**
- Fused adapters = faster inference (no overhead)
- Re-quantization = smaller size
- Production deployment would want this

**Fix needed:**
- Implement `fuse.py` with `run_fuse()` and `run_quantize()`
- OR document as future optimization

---

### 8. **No Integration with Punie Agent**

**Issue:** We built standalone training infrastructure but never integrated with the actual Punie agent.

**Current state:**
- Evaluation runs against `mlx_lm.server` (separate process)
- Training creates adapters
- **No way to actually use adapters in running Punie agent**

**Why it matters:**
- Can't test adapters in real agent workflows
- Can't measure real-world improvements
- Missing the actual use case

**Fix needed:**
- Document how to load adapter in Punie's `LocalClient`
- OR add `--adapter-path` flag to `punie serve`
- OR create integration test that runs agent with adapter

---

### 9. **Missing Real Datasets**

**Issue:** Phase 15.2 planned to download Dolma Wiki, RedPajama, KodCode but we never did.

**Current state:**
- Synthetic examples (testing only)
- CodeSearchNet Python (real but small samples)
- Hand-authored tool calling (10 examples)

**Impact:** Can't run real experiments with production datasets.

**Fix needed:**
- Implement real dataset downloaders
- OR document as user action
- OR pivot to smaller scope (hand-authored only)

---

### 10. **No Checkpoint/Resume Support**

**Issue:** Training runs to completion or fails. Can't resume interrupted training.

**Why it matters:**
- Long training runs (100+ iters) can be interrupted
- Hyperparameter search might crash partway through
- Waste of compute if can't resume

**Fix needed:**
- Add checkpoint saving to training
- OR accept limitation for MVP
- OR add retry logic

---

### 11. **No Early Stopping**

**Issue:** We parse training logs after completion but don't monitor during training.

**Why it matters:**
- Can't stop training when val loss plateaus
- Waste compute on unnecessary iterations
- No automated convergence detection

**Fix needed:**
- Stream training output during execution
- Monitor val loss in real-time
- Stop when val loss increases (overfitting)

---

### 12. **No Automated Validation**

**Issue:** All testing is manual (run demo scripts, check output).

**Why it matters:**
- Can't catch regressions
- Can't validate training works on CI
- Manual testing doesn't scale

**Fix needed:**
- Add integration tests that actually train (marked @slow)
- OR document manual testing procedure
- OR create smoke tests with tiny models

---

## 🟡 Minor Issues

### 13. **Evaluation Suite is Generic**

**Issue:** `create_baseline_suite()` has generic prompts, not Punie-specific.

**Impact:** Evaluation doesn't test what Punie actually does.

**Fix:** Create Punie-specific eval suite (PyCharm integration tasks).

---

### 14. **No Loss Curve Visualization**

**Issue:** We parse training logs but don't plot loss curves.

**Impact:** Can't easily see training progress or overfitting.

**Fix:** Add matplotlib charts to HTML reports (train/val loss vs iteration).

---

### 15. **No Dataset Provenance Tracking**

**Issue:** Don't record where data came from, when downloaded, what filters applied.

**Impact:** Can't reproduce experiments or audit data sources.

**Fix:** Add metadata tracking to datasets (source, download_date, filters_applied).

---

### 16. **No Multi-GPU Support**

**Issue:** Training only uses single GPU.

**Impact:** Slow training on large models.

**Fix:** Not needed for MVP (MLX handles this automatically on Apple Silicon).

---

## 🟢 Nice to Have (Future Work)

17. Self-play data generation
18. Curriculum learning
19. Continuous regression testing
20. A/B testing infrastructure
21. Adapter composition (stack multiple adapters)
22. Distributed training
23. Dataset versioning
24. Experiment tracking (MLflow, W&B)

---

## Priority Assessment

### Must Fix Before Production
1. ✅ **Validate 30B model is trainable** - Run benchmark
2. ✅ **Fix LoRA rank configuration** - Actually pass the parameter
3. ✅ **One successful training run** - Prove it works with real improvement
4. ✅ **Document Punie agent integration** - How to use adapters

### Should Fix Soon
5. **Generate more tool-calling examples** - At least 50
6. **Implement adapter fusion** - For production deployment
7. **Real dataset downloaders** - OR document manual process

### Can Defer
8. Temperature/top-p tuning (if not supported by mlx_lm)
9. Checkpoint/resume support
10. Early stopping
11. Automated validation
12. Loss curve visualization

---

## Recommendations

### Option A: Fix Critical Gaps (1-2 days)
1. Run 30B benchmark → know if target model works
2. Fix LoRA rank → enable full hyperparameter tuning
3. One real training run → prove the system works
4. Document agent integration → show how to use it

**Outcome:** Production-ready infrastructure with validated workflow.

### Option B: Reduce Scope (1 day)
1. Document limitations clearly
2. Mark Toucan/30B as future work
3. Merge to main with current state
4. Iterate based on real usage

**Outcome:** Working MVP, iterate based on user feedback.

### Option C: Full Production (3-5 days)
1. Fix all critical gaps
2. Add 50+ tool-calling examples
3. Implement adapter fusion
4. Real dataset downloaders
5. Integration tests
6. Loss curve visualization

**Outcome:** Production-grade system ready for real training.

---

## Bottom Line

**Infrastructure is solid** (156 tests, clean code, good architecture).

**Critical gaps exist:**
- LoRA rank not configured ❌
- 30B model not benchmarked ❌
- No proof training actually improves performance ❌
- No integration with Punie agent ❌

**Decision needed:** Fix critical gaps, reduce scope, or go for full production?

My recommendation: **Option A** - Fix the 4 critical gaps, then merge. This proves the system works without spending weeks on nice-to-haves.
