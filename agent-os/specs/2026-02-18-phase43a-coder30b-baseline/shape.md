# Phase 43a Shaping Notes

## Scope Decision

**In scope:**
- Re-run Phase 33b training pipeline under Phase 43a naming
- Same model: `mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit`
- Same data: `data/phase33_merged` (1,159 train / 123 valid)
- Same hyperparams: 800 iters, lr=1e-4, 8 LoRA layers, grad-accum=4
- Evaluate against 27-prompt Phase 33b eval suite
- Document per-category results vs Phase 33b baseline
- Provide clean Phase 43 checkpoint for future experiment comparison

**Out of scope:**
- New training data (reuses Phase 33b data unchanged)
- New hyperparameter changes (pure baseline confirmation)
- New eval prompts (reuses Phase 33b 27-prompt suite)
- Experiment B (Qwen3-14B dense) — separate script and results doc

---

## Key Design Decisions

### Why re-run Phase 33b with same settings?

Phase 33b's 82.4% may have variance across runs (stochastic training, random seeds). Running
Experiment A establishes:

1. **Reproducibility bound**: Does 82.4% hold across identical runs, or is there ±5% variance?
2. **Phase 43 baseline**: Future experiments (Experiment B: 14B dense, potential Phase 44
   data improvements) need a same-phase baseline to compare against.
3. **Domain/multi_tool improvement chance**: Randomness in training may give different emphasis
   to the weak categories (domain 60%, multi_tool 35%).

### Why same 8 LoRA layers?

The 30B MoE model has 94 total transformer layers but each token activates only ~3B params via
routing. LoRA at 8/94 ≈ 8.5% targets the most active attention layers — confirmed working
at 82.4%. No reason to change a proven configuration.

### Why no new training data?

Isolating variables: any score change vs Phase 33b is attributed to run-to-run variance or
randomness, not data quality changes. Phase 43b data improvements (if needed) come after
establishing the baseline.

---

## Risk Register

| Risk | Mitigation |
|------|-----------|
| Score <82.4% (regression) | Still informative — documents variance; stay on Phase 33b production model |
| Domain/multi_tool no improvement | Expected — they may improve only with data changes |
| Disk space (77 GB temp) | Check before run; clean up float16 intermediate automatically |
| Training time >40 min | Script logs elapsed time; run in background if needed |

---

## Phase 43b Preview

Experiment B (separate script) will test `mlx-community/Qwen3-14B-4bit` with:
- --num-layers 12 (dense needs more LoRA coverage than MoE)
- Same data and hyperparams otherwise
- Hypothesis: if ≥80%, total-params hypothesis confirmed; if <50%, MoE routing is structural

Experiments A and B run sequentially (disk constraint — 30B takes 77 GB temp, 14B takes ~40 GB).
