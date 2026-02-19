# Phase 43 Experiment A: Qwen3-Coder-30B-A3B Baseline Re-Run

## Context

Phase 33b achieved 82.4% on 27-prompt eval using `Qwen3-Coder-30B-A3B-Instruct-4bit` with
1,282 training examples. Weak categories remain: domain (60%) and multi_tool (35%).

Phase 40 proved 8B dense fails (18.5%). The production 30B MoE model stays.

Experiment A re-runs the Phase 33b pipeline under Phase 43 naming to:
1. Confirm the 82.4% baseline reproduces (variance measurement)
2. Provide a clean Phase 43 checkpoint for comparison with future experiments
3. Establish whether domain/multi_tool scores improve with a fresh run

This is a low-risk experiment (~30 min) with the same model, data, and hyperparameters.

## Task 1: Save Spec Documentation

Create `agent-os/specs/2026-02-18-phase43a-coder30b-baseline/` with:

- **plan.md** — This full plan
- **shape.md** — Shaping notes (scope, decisions, context)
- **standards.md** — agent-verification standard (always included)
- **references.md** — Pointers to Phase 33b/40 reference scripts

## Task 2: Verify Training Infrastructure

Before running the pipeline, confirm all prerequisites are in place:

1. Check `data/phase33_merged/train.jsonl` exists and has ≥1000 examples
2. Check `data/phase33_merged/valid.jsonl` exists
3. Verify `mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit` is cached locally
   (or document that it will be downloaded on first run)
4. Verify `scripts/run_phase33_direct_eval.py` is present and runnable

**No code changes needed** — just verification that the existing infrastructure works.

## Task 3: Create Phase 43a Training Script

**File:** `scripts/run_phase43a_coder30b.sh` (already created)

Verify the script exists and matches the Phase 33b template:
- Base model: `mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit`
- Data: `data/phase33_merged`
- Hyperparams: 800 iters, lr=1e-4, 8 LoRA layers, batch=1, grad-accum=4
- Output: `adapters_phase43a/` → `fused_model_qwen3_phase43a_coder30b_5bit/`
- Eval: runs `scripts/run_phase33_direct_eval.py` at the end

## Task 4: Create Results Document Template

**File:** `docs/research/phase43a-coder30b-results.md`

Pre-create a results template (matching the Phase 40 results doc format) with:
- Summary section (fill after run)
- Pre-registered success criteria table
- Per-prompt results table (fill after run)
- Training metrics table (fill after run)
- Comparison with Phase 33b baseline

## Task 5: Run Experiment A

Execute the training pipeline:

```bash
bash scripts/run_phase43a_coder30b.sh
```

Estimated time: ~30-40 minutes total.

Steps (automated by script):
1. LoRA training (800 iters)
2. Fuse adapters → float16
3. Quantize float16 → 5-bit
4. Clean up intermediate float16
5. Run 27-prompt eval

## Task 6: Record Results

After the pipeline completes:
1. Fill in `docs/research/phase43a-coder30b-results.md` with actual scores
2. Update `docs/research/minimum-model-requirements.md` with Phase 43a results
3. Update `docs/research/lora-degradation-and-model-variants.md` Section 8 with outcome
4. Update `MEMORY.md` with phase status

## Verification

1. Use `astral:ruff` skill to check any Python files modified
2. Use `astral:ty` skill to check types on any Python files modified
3. Run `uv run pytest tests/` to verify no regressions
4. Confirm eval output shows per-category scores
5. Compare Phase 43a scores against Phase 33b baseline:
   - text_tools ≥100%, validation ≥100%, git ≥100%, cst ≥100%
   - lsp ≥90%, domain >60% (target), multi_tool >35% (target)
   - Overall ≥82.4%

## Critical Files

- `scripts/run_phase43a_coder30b.sh` — training pipeline
- `scripts/run_phase33_direct_eval.py` — 27-prompt eval harness
- `scripts/run_phase33b_overnight.sh` — reference template
- `src/punie/agent/prompt_utils.py` — format_prompt() (MUST use, never bypass)
- `docs/research/lora-degradation-and-model-variants.md` — Phase 43 research doc
- `docs/research/phase40-8b-results.md` — results doc template reference

---

## Outcome and Follow-On Analysis

**Phase 43a result:** ❌ FAIL — 38.9% at iter 600 (best), 18.5% after resume. Baseline did
not reproduce. See `docs/research/phase43a-coder30b-results.md`.

**Phase 44 (format fix):** ❌ FAIL — 22.2% documented, 16.7% on re-run. But overnight deep
dive found critical new data: at temperature=0.0, all 5 probed prompts scored 1.0 (execute_code
wrapper). At default temperature they scored 0.0–0.5. See `docs/research/phase44-deep-dive.md`.

**Phase 43b (14B dense) — status: DEPRIORITIZED pending Phase 45**

The MoE hypothesis test is still worth running, but cannot be cleanly interpreted until the
temperature variable is resolved. See the analysis in:

→ **`docs/research/temperature-and-format-lock.md`** — full reasoning and decision tree

### Next Phases (in recommended order)

#### Phase 45: Temperature Sweep
Add `--temperature` flag to `scripts/run_phase33_direct_eval.py`. Run full 27-prompt eval
on Phase 44 and Phase 33b at temps 0.0, 0.2, 0.5, 0.7. If Phase 44 scores ≥80% at temp=0,
ship that as the production config and deprioritize 43b further.

**Script to write:** `scripts/run_phase45_temperature_sweep.sh`
**Eval script change:** add `--temperature FLOAT` arg, default 0.7, pass through to HTTP request

#### Phase 46: Multiple Seeds (if Phase 45 insufficient)
Run 5 training seeds (0, 1, 2, 3, 42) with Phase 33b exact settings. Measure the distribution
of outcomes to determine whether 82.4% is reproducible or was a rare training event.

**Script to write:** `scripts/run_phase46_seed_sweep.sh`

#### Phase 43b: 14B Dense (run after Phase 45, at temperature=0)
Use `scripts/run_phase43b_14b_dense.sh` (already written). Eval at temperature=0 to control
for format-fragility. Interpret result as: does 14B dense achieve format lock at all (even
fragile), not whether it matches Phase 33b's robust lock at default temp.
