# Phase 40 Shaping Notes

## Scope Decision

**In scope:**
- Preflight tokenizer compatibility check (Qwen3-8B vs Qwen3-30B special tokens)
- Train Qwen3-8B LoRA on same `data/phase33_merged` dataset (1,159 train / 123 valid)
- Fuse, quantize to 5-bit, evaluate against 27-prompt Phase 33b eval suite
- Fix eval model ID detection (hardcoded "phase33" filter removed)
- Document per-category results vs Phase 33b baseline

**Out of scope:**
- A/B live usage test (Milestone 4 — deferred)
- New training data (reuses Phase 33b data unchanged)
- Architecture changes (pure hyperparameter swap)
- New eval prompts (reuses Phase 33b 27-prompt suite)

---

## Key Design Decisions

### Why Qwen3-8B (not Qwen3-1.5B or Mistral-7B)?

1. **Same family tokenizer:** Qwen3-8B shares the exact tokenizer with Qwen3-30B-A3B. Phase 25's
   0% failure was traced to tokenizer mismatch. Same family = identical special token IDs
   (151644-151666), identical ChatML template, zero train/test format mismatch risk.

2. **Instruction-tuned base:** Qwen3-8B is Qwen3's instruction-tuned variant. No separate
   "Instruct" model needed — LoRA fine-tunes directly.

3. **Size sweet spot:** 8B dense ≈ 6 GB at 5-bit. Fits M-series Mac RAM alongside the inference
   server without thrashing. Qwen3-1.5B might underfit 26 tools on 1,282 examples.

### Why 16 LoRA layers (vs 8 for 30B)?

The 30B MoE model has 48 transformer layers but each token activates only ~3B params via routing.
LoRA at 8/48 = 17% covers the routing experts.

Qwen3-8B has 36 dense layers — every param is active on every token. LoRA at 16/36 = 44% gives
comparable gradient signal coverage for learning 26 tool signatures from 1,282 examples.

Underfitting risk is higher for dense models because there's no "expert specialization" to
leverage — the routing signal must be imprinted via higher LoRA coverage.

### Why same iters (800)?

Phase 33b used 800 iters on 1,159 train examples ≈ 2.76 epochs. At ~4x training speed for 8B,
800 iters will complete in ~8-10 min vs 30-40 min for 30B. No reason to reduce — same epoch
count gives fair comparison. If 8B overfits, reduce in Phase 41.

### Why same learning rate (1e-4)?

Phase 33b LR worked well (82.4% eval, no divergence). Starting from the same LR ensures we
isolate the model size effect. If 8B shows training instability, adjust in Phase 41.

### Why not reduce training data?

The 1,282 examples are already curated for 26 tools. Reducing would artificially handicap the
8B model. The hypothesis is that routing (not reasoning) is the bottleneck — smaller data could
mask whether the model learned the routing vs just memorized fewer examples.

---

## Phase 25 Lessons Applied

Phase 25 (7B experiment, 0% accuracy) failures and how Phase 40 avoids them:

| Phase 25 failure | Phase 40 fix |
|-----------------|--------------|
| Mismatched tokenizer (Mistral-7B on Qwen3 data) | Same-family Qwen3-8B tokenizer |
| Only 6 tools in training data | 26 tools, 1,282 examples |
| No preflight tokenizer check | Task 3 mandatory — STOP if check fails |
| Eval format mismatch | `format_prompt()` utility ensures ChatML consistency |
| 857 examples (insufficient for multi-tool) | 1,282 examples (same as Phase 33b) |

---

## Risk Register

| Risk | Mitigation |
|------|-----------|
| Tokenizer mismatch | Task 3 preflight exits hard if IDs differ |
| Underfitting (8B lacks capacity for 26 tools) | Pre-registered ≥80% threshold; proceed to 8B+LoRA-tuning or stay on 30B |
| Overfitting (memorizes 1,282 examples) | Monitor val loss; early-stop if val diverges from train |
| Domain category regression | Domain was 60% on 33b — 8B target is same 60%, not higher |
| Disk space | 8B pipeline uses ~22 GB temp vs 77 GB for 30B — monitor before run |
