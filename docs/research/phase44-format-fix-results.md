# Phase 44: Format Lock Fix — Results

**Date:** 2026-02-18
**Branch:** `phase43-model-variants`
**Model:** `fused_model_qwen3_phase44_format_fix_5bit/` (20 GB)
**Result:** ❌ FAIL — 22.2% (target ≥80%)
**Script:** `scripts/run_phase44_format_fix.sh`
**Log:** `logs/phase44_format_fix_training.log`

---

## Hypothesis

Phase 43a (38.9%) failed due to two identified bugs in the eval infrastructure:

1. **Think-mode interference** — `<think>` blocks consumed all tokens (0.0 scores)
2. **System prompt mismatch** — `_direct` suffix in eval but bare names in training data

Phase 44 fixed both bugs and added seed=42 + best-checkpoint selection. Hypothesis: the eval
bugs were responsible for the gap between 38.9% and the 82.4% Phase 33b baseline.

**Outcome:** Hypothesis **partially supported, partially disproved.**
- ✅ Think-mode timeouts eliminated: 0/27 prompts hit `<think>` blocks (down from 10/27)
- ❌ Overall accuracy still failed: **22.2%** — actually worse than Phase 43a (38.9%)

---

## Fixes Applied and Results

| Fix | File | Change | Effect |
|-----|------|--------|--------|
| Think-mode stop seq | `run_phase33_direct_eval.py:339` | Added `"<think>"` | ✅ Eliminated think-mode timeouts |
| Eval system prompt | `run_phase33_direct_eval.py:43-54` | Removed `_direct` suffixes | Unknown (can't isolate) |
| Seed | `run_phase44_format_fix.sh` | `--seed 42` | Different training trajectory |
| Checkpoint granularity | `run_phase44_format_fix.sh` | `--save-every 100` | 8 checkpoints |
| Best checkpoint | `select_best_checkpoint.py` | Auto-selected iter 800 | 0.176 val loss |

---

## Training Configuration

```
Base model:     mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit
Data:           data/phase33_merged (1159 train + 123 valid)
Iterations:     800
Learning rate:  1e-4
LoRA layers:    8
Grad accum:     4
Batch size:     1
Seed:           42
Save every:     100 (8 checkpoints saved)
Mask prompt:    true
Training time:  30 min
Peak memory:    21.302 GB
```

---

## Training Curve

| Iter | Val Loss | Checkpoint | Notes |
|------|----------|-----------|-------|
| 1 | 2.118 | | |
| 50 | 0.696 | | |
| 100 | 0.594 | ✓ | |
| 150 | 0.424 | | |
| 200 | 0.521 | ✓ | Slight spike |
| 250 | 0.491 | | |
| 300 | 0.360 | ✓ | |
| 350 | 0.449 | | Slight spike |
| 400 | 0.291 | ✓ | |
| 450 | 0.304 | | |
| 500 | 0.339 | ✓ | |
| 550 | 0.312 | | |
| 600 | 0.243 | ✓ | |
| 650 | 0.367 | | Spike |
| 700 | 0.259 | ✓ | |
| 750 | 0.216 | | |
| **800** | **0.176** | ✓ | **Best — still decreasing** |

**Best checkpoint:** iter 800 (val_loss = 0.176) — selected by `select_best_checkpoint.py`

Note: Val loss **still decreasing at iter 800**. Suggests training could benefit from more iters.
But Phase 43a's best val loss (0.111) was also excellent and produced only 38.9% eval accuracy.
Val loss is not a reliable predictor of eval accuracy for format-sensitive tasks.

---

## Per-Prompt Results

| Prompt | Score | Time | Notes |
|--------|-------|------|-------|
| text-01 | 0.00 | 66.3s | Timeout — generated Python code block |
| text-02 | 0.50 | 1.9s | Direct write_file call |
| text-03 | 0.50 | 13.7s | Direct run_command call |
| valid-01 | 0.50 | 13.6s | Direct typecheck call |
| valid-02 | 0.50 | 1.6s | Direct ruff_check call |
| valid-03 | 0.50 | 11.5s | Direct pytest_run call |
| lsp-01 | 0.50 | 13.7s | Direct goto_definition call |
| lsp-02 | 0.00 | 13.6s | Prose: "Let me search for all occurrences..." |
| lsp-03 | 0.00 | 13.6s | Prose: "Let me search for LoRAConfig definition..." |
| lsp-04 | 0.00 | 2.7s | Prose: "I need to examine the LoRA config file..." |
| lsp-05 | 0.50 | 97.4s | Direct workspace_symbols call (long) |
| git-01 | 0.50 | 1.3s | Direct git_status call |
| git-02 | 0.50 | 3.7s | Direct git_diff call |
| git-03 | 0.50 | 2.1s | Direct git_log call |
| cst-01 | 0.50 | 8.5s | Direct cst_find_pattern call |
| cst-02 | 0.00 | 23.4s | Prose: "I need to find and rename TrainingResult..." |
| cst-03 | 0.00 | 16.6s | Prose: "I need to add the import statement..." |
| dom-01 | 0.00 | 3.0s | Prose: "Let me first check what's in that file..." |
| dom-02 | 0.00 | 23.5s | Prose: "I need to read that file first..." |
| dom-03 | 0.00 | 23.6s | Prose: "Let me first check the circuit breaker..." |
| dom-04 | 0.00 | 23.3s | Prose: "Let me first examine the file..." |
| dom-05 | 0.00 | 25.2s | Prose: "I need to check the registration.py file..." |
| dom-06 | 0.50 | 25.5s | Direct validate_route_pattern call |
| dom-07 | 0.00 | 12.4s | Prose: "Let me look at the file contents..." |
| dom-08 | 0.00 | 24.0s | Prose: "I need to check the imports..." |
| dom-09 | 0.00 | 23.8s | Prose: "I need to check if html() calls..." |
| multi-01 | 0.00 | 48.0s | Prose: "Let me help you find HomeView..." |

**Score distribution:**
- 1.0 (execute_code + correct keyword): **0 prompts** (0%)
- 0.5 (direct tool call, correct tool): **12 prompts** (44%)
- 0.0 (prose generation, no tool call): **15 prompts** (56%)

---

## Category Breakdown

| Category | Score | vs Phase 33b | vs Phase 43a |
|----------|-------|-------------|-------------|
| text_tools | 33.3% | 100% | 50.0% |
| validation | 50.0% | 100% | 50.0% |
| git | 50.0% | 100% | 33.3% |
| cst | 16.7% | 100% | 16.7% |
| lsp | 20.0% | 90% | 50.0% |
| domain | 5.6% | 60% | 27.8% |
| multi_tool | 0.0% | 35% | 100.0% |
| **Overall** | **22.2%** | **82.4%** | **38.9%** |

---

## Think-Mode Analysis

| Metric | Phase 43a (iter 600) | Phase 44 |
|--------|---------------------|----------|
| Think-mode timeouts | 10/27 (0.0) | **0/27** |
| Direct tool calls (0.5) | 16/27 | 12/27 |
| Prose generation (0.0) | 0/27 | **15/27** |
| execute_code calls (1.0) | 1/27 | 0/27 |

The `<think>` stop sequence successfully prevented think-mode timeouts. However, the model
shifted to a new failure mode: prose reasoning ("I'll help you...", "Let me first check...")
without a tool call. This prose generation is NOT think-mode — it's the model's base
instruction-tuning generating helpful conversational responses.

---

## Failure Mode Analysis

### New Pattern 6: Prose Reasoning Without Tool Calls

Phase 44 introduced a new failure pattern not seen in Phase 43a:

```
"I'll search for all references to `execute_code` across the project.
Let me search for all occurrences..."
```

The model initiates a helpful conversational response but fails to execute a tool call. This
appears when:
- The task requires reasoning about WHERE to look (lsp-02, lsp-03, lsp-04)
- The task involves domain-specific tools (dom-01 through dom-09)
- Multi-step tasks (multi-01)

The pattern is consistent: the model DESCRIBES what it will do instead of DOING it.

### Why Phase 44 Scored Lower Than Phase 43a

Phase 43a (iter 600 model): Direct tool calls (0.5) for 16/27 prompts. The model called the
right tool without the execute_code wrapper — wrong format, right tool.

Phase 44 (seed=42, iter 800): Prose for 15/27 prompts. The model doesn't call any tool —
wrong format, no tool at all. This is strictly worse than direct calls (0.0 vs 0.5).

**Hypothesis:** seed=42 hit a training trajectory that reinforced the model's base
instruction-tuning (conversational prose) more strongly than Phase 43a's random seed. The
lower val loss (0.176 vs 0.260) suggests this seed converged to a different local minimum —
one that fits the training data well but via prose generation rather than tool calling.

### Why Val Loss 0.176 Produced 22.2% Accuracy

This is the most important finding of Phase 44. The model's val loss was excellent (0.176,
still decreasing at iter 800). But accuracy dropped from 38.9% to 22.2%.

This definitively confirms: **val loss and eval accuracy are not correlated for format-sensitive tasks**.

- Val loss measures how well the model fits the training distribution token-by-token
- Eval accuracy measures whether the model produces the specific format (execute_code wrapper)
- A model can achieve low val loss by fitting conversational prose patterns from the base model
  while still failing to reliably apply the execute_code format

---

## Comparison Table

| Phase | Model | Val Loss | Score | Primary Failure |
|-------|-------|----------|-------|----------------|
| 33b | Coder-30B-A3B | ~0.08 | 82.4% | Production baseline |
| 43a iter-600 | Coder-30B-A3B | 0.494 | 38.9% | Direct calls (0.5), think-mode (0.0) |
| 43a iter-800 | Coder-30B-A3B | 0.260 | 18.5% | Prose (resume made worse) |
| 40 | 8B | 0.083 | 18.5% | Capacity too small |
| **44** | **Coder-30B-A3B** | **0.176** | **22.2%** | **Prose reasoning, no tool calls** |

---

## Key Lessons

1. **Think-mode fix works** — `<think>` in stop sequences eliminates think-mode timeouts.
   This was a real fix for a real bug. It should be kept in all future evals.

2. **Seed affects failure mode, not success rate** — seed=42 hit a trajectory that produces
   prose generation instead of Phase 43a's direct tool calls. Neither trajectory reaches
   execute_code format reliably. Multiple seeds are needed to characterize the distribution.

3. **Val loss and accuracy diverge for format-sensitive tasks** — 0.176 val loss with 22.2%
   accuracy. The model can fit training data token-by-token while learning the wrong format.
   Eval during training must score the FORMAT, not the loss, to guide early stopping.

4. **Best-checkpoint by val loss may select wrong checkpoint** — the iter 800 checkpoint
   (best val loss) produced worse eval than we might have gotten at earlier checkpoints.
   Need format-aware checkpoint selection (eval score, not val loss).

5. **82.4% remains irreproducible** — Three runs with the same model, data, and hyperparams
   produced 38.9%, 18.5%, and 22.2%. Phase 33b's result appears to be a high-variance event
   requiring specific training dynamics to reproduce.

---

## Infrastructure Fixes (From This Experiment)

Two important bugs were found and fixed in `scripts/run_phase33_direct_eval.py`:

### Bug 1: Server collision (silent wrong-model eval)
**Problem:** If port 8080 was already occupied, `wait_for_server` found the existing server
and the eval ran against the wrong model, producing 0.0% with no error.

**Fix:** The server process is checked for early exit after 3s:
```python
await asyncio.sleep(3.0)
if server_proc.poll() is not None:
    print(f"ERROR: Server exited immediately — port {args.port} is likely in use")
    return 1
```

### Bug 2: False model ID guard
**Problem:** A model ID check incorrectly rejected local fused models because mlx_lm reports
the base model ID (`mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit`) from the model's
config.json, not the directory path.

**Fix:** Removed the model ID guard; relies on process exit check instead.

---

## Next Steps

Phase 44's failure strengthens the hypothesis that the execute_code format requires specific
training dynamics, not just infrastructure fixes. Possible paths forward:

1. **Phase 43b: 14B dense model** — test whether MoE routing is structurally necessary
   (as planned). Phase 44's failure doesn't change this experiment's value.

2. **Format-aware training objective** — add eval during training that scores execute_code
   format adherence, not just val loss. Use this for early stopping.

3. **Multiple seeds** — run 3+ seeds to characterize the format-lock probability distribution.
   Phase 33b may have been a 1-in-N lucky training trajectory.

4. **Training data augmentation** — add more execute_code examples, especially multi-step
   examples (multi-01 was the only 1.0 in Phase 43a). Reinforce wrapper format explicitly.

**Production model remains:** `fused_model_qwen3_phase33b_5bit/` (20 GB, 82.4%)
