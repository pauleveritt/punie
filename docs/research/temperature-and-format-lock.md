# Temperature and Format Lock: Rethinking the MoE Hypothesis

**Date:** 2026-02-19
**Status:** Active research question — informs Phase 43b go/no-go decision
**Related:** `lora-degradation-and-model-variants.md`, `phase44-deep-dive.md`

---

## Summary

Phase 44's overnight deep dive found that the model scores **1.0 on all 5 probed prompts at
temperature=0.0**, while the same model scores 0.0–0.5 at default temperature (overall 16.7%).
This introduces a confounding variable that must be resolved before the MoE hypothesis test
(Phase 43b) can be interpreted cleanly.

---

## The Temperature Finding

Phase 44's consistency check ran 5 prompts × 3 times at `temperature=0.0`:

| Prompt | Run 1 | Run 2 | Run 3 | Main eval (default temp) |
|--------|-------|-------|-------|--------------------------|
| git-01 | 1.0 | 1.0 | 1.0 | 0.5 |
| valid-01 | 1.0 | 1.0 | 1.0 | 0.5 |
| cst-01 | 1.0 | 1.0 | 1.0 | 0.0 |
| dom-01 | 1.0 | 1.0 | 1.0 | 0.0 |
| multi-01 | 1.0 | 1.0 | 1.0 | 0.0 |

At temperature=0, the model reliably produces the `execute_code` wrapper format. At default
temperature, it produces either direct tool calls (0.5) or conversational prose (0.0).

**The implication:** Phase 44's model has learned the execute_code format but holds it
fragile — it only fires consistently at low temperature where the model takes the highest-
probability path.

---

## Two Kinds of Format Lock

This finding reveals a distinction that was invisible in earlier phases:

### Robust Format Lock (Phase 33b)
The Phase 33b model scored 82.4% at **default temperature**. It holds the execute_code format
even when temperature introduces randomness. The base instruction-tuning priors are overridden
strongly enough that format adherence survives stochastic sampling.

### Fragile Format Lock (Phases 43a, 44)
Phases 43a and 44 use identical data and hyperparameters but produce models that:
- Score well at temperature=0 (the format is present in the weights)
- Drift to direct calls (0.5) or prose (0.0) at default temperature

The format was learned but not *strongly* enough to override the base model's conversational
priors when sampling is non-deterministic.

---

## What This Means for the MoE Hypothesis

Phase 43b was designed to test:
- **Hypothesis A:** Total parameter count decides (14B dense would pass)
- **Hypothesis B:** MoE routing is structurally required (14B dense would fail)

The temperature finding introduces a new dimension:

| Scenario | Implication |
|----------|-------------|
| 14B dense at default temp fails, but passes at temp=0 | Fragile lock — same as 44; ambiguous result |
| 14B dense fails even at temp=0 | Capacity hypothesis confirmed: model can't learn format at all |
| 14B dense passes at default temp | Strong format lock despite dense architecture; total params hypothesis |
| 30B MoE (Phase 44) passes full eval at temp=0 | Temperature is the fix; MoE question becomes an optimization question |

Without controlling for temperature, the 43b result would be uninterpretable.

---

## Unresolved Question: What Made Phase 33b Different?

Phase 33b (82.4% at default temp) used the same model, data, and hyperparameters as phases 43a
and 44 that produced fragile lock. The difference must be one of:

1. **Lucky training trajectory** — stochastic gradient descent hit a basin where format lock
   is robust. Phases 43a/44 hit shallower basins. Multiple seeds would measure this.

2. **Specific iteration count/checkpoint** — Phase 33b's checkpoint (produced by a different
   run, possibly different effective iteration) landed in a different weight-space region.

3. **Data ordering effects** — same data, different shuffle order (if seed differs). Early
   examples of execute_code format seen more prominently could bootstrap stronger format priors.

4. **Quantization interaction** — if the robust checkpoint was at a slightly different val loss,
   5-bit quantization may preserve format signals differently.

Until this is understood, reproducing Phase 33b is partially luck. The "multiple seeds"
experiment would measure the distribution of outcomes.

---

## Recommended Next Phases

These should be completed in order before committing to Phase 43b.

### Phase 45: Temperature Sweep (highest priority)

**Goal:** Determine whether temperature=0 produces acceptable accuracy on the Phase 44 model,
and characterize Phase 33b's temperature sensitivity for comparison.

**Method:**
- Run full 27-prompt eval on Phase 44 at temperatures: 0.0, 0.2, 0.5, 0.7 (default)
- Run same sweep on Phase 33b (production model)
- Record per-category scores at each temperature

**Success criteria:**
- If Phase 44 at temp=0 scores ≥80%: temperature is the fix; 43b is deprioritized
- If Phase 44 at temp=0 scores <80%: format lock is genuinely fragile even at temp=0;
  return to training improvements

**Script changes needed:**
- Add `--temperature` flag to `scripts/run_phase33_direct_eval.py`
- Write `scripts/run_phase45_temperature_sweep.sh` to iterate

**Time estimate:** ~3h unattended (4 temps × 2 models × ~25 min/eval)

---

### Phase 46: Multiple Seeds (if Phase 45 shows temp=0 is insufficient)

**Goal:** Measure the distribution of Phase 33b-like outcomes. Is 82.4% reproducible or was
it a rare event?

**Method:**
- Train 5 runs with seeds 0, 1, 2, 3, 42 using Phase 33b exact settings
- Eval each at default temperature
- Record score distribution: mean, std, min, max

**Success criteria:**
- If 3+/5 seeds score ≥80%: Phase 33b is reproducible; identify common training trajectory
  features (checkpoint, val loss curve shape)
- If 0-1/5 seeds score ≥80%: Phase 33b was a rare event; training data augmentation needed

**Time estimate:** ~3h per seed × 5 seeds = 15h unattended overnight

---

### Phase 43b: 14B Dense (deprioritized — run after Phase 45)

**Goal:** MoE vs dense architecture hypothesis test.

**Revised framing after temperature finding:**
Phase 43b should be run at **temperature=0** to control for the format-fragility variable.
The question becomes: does 14B dense achieve format lock (even fragile lock) at temp=0?

- If yes (≥80% at temp=0): 14B dense is viable for size/latency reduction
- If no (<50% at temp=0): MoE routing is required for format learning itself

**When to run:** After Phase 45 confirms whether temperature=0 is a sufficient fix for the
production system. If temp=0 is shipped as the production config, 43b becomes a size/latency
optimization experiment rather than a blocking architecture question.

**Script:** `scripts/run_phase43b_14b_dense.sh` (already written)

---

## Performance Note

Phase 44 overnight benchmark (warm queries, 5 prompts × 5 runs):

| Prompt | Phase 44 p50 | Phase 33b p50 | Delta |
|--------|-------------|--------------|-------|
| git-01 | 2.6s | 2.4s | +0.2s |
| valid-01 | 2.9s | 2.8s | +0.2s |
| cst-01 | 3.0s | 2.9s | +0.1s |
| dom-01 | 4.7s | 2.9s | **+1.8s** |
| multi-01 | 4.1s | 2.5s | **+1.6s** |

Phase 44's slower complex-query times (dom, multi) reflect prose generation — longer token
output than a direct tool call. At temperature=0 where execute_code fires, these times
would likely match or beat Phase 33b (execute_code output is similarly short).

Both models: ~21 GB GPU memory, ~21 GB on disk.

---

## Decision Tree

```
Current state: Phase 44 at 16.7% (default temp), 100% on 5/5 probes at temp=0

→ Run Phase 45 (temperature sweep)
   │
   ├── Phase 44 scores ≥80% at temp=0
   │   → Ship temperature=0 as production config
   │   → Phase 43b = optional size/latency optimization
   │
   └── Phase 44 scores <80% at temp=0
       → Run Phase 46 (multiple seeds)
           │
           ├── 3+/5 seeds reproduce ≥80%
           │   → Fix: correct seed/training dynamics; then run 43b
           │
           └── 0-1/5 seeds hit ≥80%
               → Fix: training data augmentation
               → Phase 43b: deprioritize until training is reliable
```
