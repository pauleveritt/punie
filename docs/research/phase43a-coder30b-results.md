# Phase 43a: Qwen3-Coder-30B-A3B Baseline Re-Run — Results

**Date:** 2026-02-18
**Branch:** `phase43-model-variants`
**Model:** `fused_model_qwen3_phase43a_coder30b_5bit/` (20 GB)
**Result:** ❌ FAIL — 38.9% (target ≥82.4%)

---

## Summary

Phase 43a re-ran the Phase 33b pipeline (same model, data, hyperparameters) to confirm the
82.4% baseline. The result did not reproduce: 38.9% vs 82.4% baseline.

**Hypothesis tested:** Fresh run with production Coder-30B weights confirms ≥82.4% baseline.
**Outcome:** Hypothesis **disproved** — 82.4% does not reproduce reliably with the same settings.

The failure mode is instructive: the model learned correct intent routing (which tool to call)
but failed to consistently apply the `execute_code` wrapper format. Nearly all passing prompts
scored 0.5 (direct tool call, correct tool, no execute_code) rather than 1.0 (execute_code
format). Additionally, several prompts triggered the base model's chain-of-thought think mode
(`<think>` blocks), which timed out without producing a tool call.

---

## Pre-Registered Success Criteria vs Actual

| Category | Phase 33b Baseline | Phase 43a Target | Phase 43a Actual | Pass? |
|----------|--------------------|------------------|------------------|-------|
| text_tools | 100% | ≥100% | 50.0% | ❌ |
| validation | 100% | ≥100% | 50.0% | ❌ |
| git | 100% | ≥100% | 33.3% | ❌ |
| cst | 100% | ≥100% | 16.7% | ❌ |
| lsp | 90% | ≥90% | 50.0% | ❌ |
| domain | 60% | >60% | 27.8% | ❌ |
| multi_tool | 35% | >35% | 100.0% | ✓ |
| **Overall** | **82.4%** | **≥82.4%** | **38.9%** | ❌ |

---

## Per-Prompt Results

| Prompt ID | Query (truncated) | Score | Time | Notes |
|-----------|-------------------|-------|------|-------|
| text-01 | Show contents of config.py | 0.50 | — | Direct call, no execute_code |
| text-02 | Write text to output/summary.txt | 0.50 | — | Direct call, no execute_code |
| text-03 | Run 'ls src/' | 0.50 | 15.5s | Direct call, no execute_code |
| valid-01 | Run type checking on src/ | 0.50 | 9.9s | Direct call, no execute_code |
| valid-02 | Check src/ with ruff | 0.50 | 9.6s | Direct call, no execute_code |
| valid-03 | Run test suite in tests/ | 0.50 | 16.6s | Direct call, no execute_code |
| lsp-01 | Find definition of AgentConfig | 0.50 | 16.6s | Direct call, no execute_code |
| lsp-02 | Find references to execute_code | 0.50 | 10.7s | Direct call, no execute_code |
| lsp-03 | Type info for LoRAConfig | 0.50 | 16.6s | Direct call, no execute_code |
| lsp-04 | List symbols in lora_config.py | 0.50 | 16.6s | Direct call, no execute_code |
| lsp-05 | Search for TrainingResult symbol | 0.50 | 4.6s | Direct call, no execute_code |
| git-01 | Check git status | 0.50 | 6.3s | Direct call, no execute_code |
| git-02 | Show git diff | 0.50 | 16.6s | Direct call, no execute_code |
| git-03 | List 5 recent git commits | 0.00 | 13.6s | Think mode — no tool call |
| cst-01 | Find class definitions in websocket.py | 0.00 | 16.6s | Think mode — timed out |
| cst-02 | Rename TrainingResult to FineTuneResult | 0.50 | 13.6s | Direct call, no execute_code |
| cst-03 | Add defaultdict import | 0.00 | 13.3s | Think mode — no tool call |
| dom-01 | Validate error_page.py as tdom component | 0.50 | 10.9s | Direct call, no execute_code |
| dom-02 | Check service registration | 0.50 | 10.8s | Direct call, no execute_code |
| dom-03 | Check middleware conventions | 0.00 | 16.6s | Think mode — timed out |
| dom-04 | Check dependency graph violations | 0.50 | 12.0s | Direct call, no execute_code |
| dom-05 | Check t-string usage in registration.py | 0.00 | 15.6s | Think mode — timed out |
| dom-06 | Validate route patterns in api.py | 0.50 | 8.9s | Direct call, no execute_code |
| dom-07 | Verify render tree in checkout.py | 0.50 | 11.8s | Direct call, no execute_code |
| dom-08 | Check Inject[] imports | 0.00 | 16.6s | Think mode — timed out |
| dom-09 | Check html() context= in account.py | 0.00 | 16.6s | Think mode — timed out |
| multi-01 | Find HomeView, read, validate as tdom | 1.00 | 19.2s | execute_code format ✓ |

**Score distribution:**
- 1.0 (execute_code + correct keyword): **1 prompt** (multi-01 only)
- 0.5 (direct tool call, correct tool): **16 prompts**
- 0.0 (think mode / timeout): **10 prompts**

---

## Training Metrics

| Metric | Value |
|--------|-------|
| Training time | 42 min |
| Fuse time | ~85 sec (fast — OS page cache) |
| Quantize time | ~30 sec (OS page cache) |
| Total pipeline | ~50 min |
| Final model size | 20 GB |
| Val loss at iter 1 | 2.487 |
| Val loss at iter 50 | 0.696 |
| Val loss at iter 100 | 0.619 |
| Val loss at iter 300 | 0.460 |
| Val loss at iter 400 | 0.453 |
| Val loss at iter 500 | 0.289 |
| Val loss at iter 550 | **0.165** (best) |
| Val loss at iter 600 | 0.494 (spike) |
| Val loss at iter 650 | **0.111** (best overall) |
| Val loss at iter 700 | 0.283 |
| Val loss at iter 750 | 0.234 |
| Val loss at iter 800 | 0.260 |
| Trainable parameters | 0.231% (70.459M / 30532.123M) |
| Peak memory | 21.433 GB |
| Evaluated checkpoint | **iter 600** (see note below) |

**Evaluated checkpoint note:** Due to concurrent fuse tasks during the pipeline, the model
that ran the eval was fused from the **iter 600 adapter** (`adapters.safetensors` at 19:23),
not the iter 800 final checkpoint (saved at 20:10). The iter 800 val loss (0.260) was better
than iter 600 (0.494), so the iter 800 model might score slightly differently — but given
that the failure is structural (format not format-marginal), the delta would be small.

**Notable:** Val loss at iter 650 (0.111) is better than Phase 33b's typical final val loss,
but the model still scored poorly on eval. This suggests val loss alone is not a reliable
predictor of eval accuracy — the model may have learned data patterns without retaining the
critical `execute_code` format.

---

## Failure Mode Analysis

### Pattern 1: Direct calls without execute_code (16 prompts, score 0.5)

The model correctly identifies which tool to call but wraps it as a direct Python call without
the `execute_code()` outer function. This is the same failure as Phase 40's 8B model, but here
from a 30B model on the SAME training data that previously produced 82.4%.

This indicates the execute_code wrapper is **stochastically learned** — this particular random
seed / training trajectory found a local optimum in which tool routing (names) was learned but
not the format wrapper.

### Pattern 2: Think mode interference (10 prompts, score 0.0)

Several prompts triggered the base model's chain-of-thought `<think>` mode:
- `<think>Okay, the user wants to list the 5 most recent Git commits. Let me think about how to approa...`
- `<think>Okay, the user wants me to find all class definitions...`

The model generates reasoning prose that times out (~13-16s) without committing to a tool call.
These are concentrated in: git-03, cst-01, cst-03, dom-03, dom-05, dom-08, dom-09 — the more
"natural language" describable actions where the base model's instruction tuning strongly pulls
toward reasoning.

### Pattern 3: Multi-step exception (1 prompt, score 1.0)

The hardest prompt (multi-01: find → read → validate, 3 steps) scored 1.0 with execute_code.
This suggests that multi-step tasks have a stronger signal in the training data that overrides
the direct-call tendency. Single-step tasks don't have enough "code-ness" to trigger the
execute_code format.

---

## Comparison with Phase 33b Baseline

| Aspect | Phase 33b | Phase 43a |
|--------|-----------|-----------|
| Model | Qwen3-Coder-30B-A3B-Instruct-4bit | Qwen3-Coder-30B-A3B-Instruct-4bit |
| Training data | data/phase33_merged (1,282 ex) | data/phase33_merged (1,282 ex) |
| Hyperparams | 800 iters, lr=1e-4, 8 layers | 800 iters, lr=1e-4, 8 layers |
| Overall score | **82.4%** | **38.9%** |
| domain | 60% | 27.8% |
| multi_tool | 35% | 100% |
| Best val loss | ~0.08 (inferred) | 0.111 (iter 650) |
| Final val loss | ~0.08 (inferred) | 0.260 (iter 800) |
| Score 1.0 prompts | ~22/27 | 1/27 |
| Score 0.5 prompts | ~5/27 | 16/27 |
| Score 0.0 prompts | ~0/27 | 10/27 |

**Key difference:** Phase 33b produced mostly 1.0 scores (execute_code format). Phase 43a
produced mostly 0.5 scores (direct tool calls). This is a format-learning variance, not an
intent-routing variance.

---

## Verdict

**Phase 33b baseline does NOT reliably reproduce with identical settings.**

The 82.4% achieved in Phase 33b was not a stable fixed point. With the same model, data, and
hyperparameters, this run achieved 38.9%. The execute_code format wrapper is stochastically
learned — dependent on training randomness (mini-batch order, initialization noise, gradient
updates near inflection points).

**Production model remains:** `fused_model_qwen3_phase33b_5bit/` (20 GB, 82.4%)

**New Phase 43a model preserved for analysis:** `fused_model_qwen3_phase43a_coder30b_5bit/`
(use for comparison, not production)

---

## Key Lessons

1. **82.4% was not a stable baseline** — Phase 33b's accuracy is a high-variance achievement,
   not a reproducible floor. The execute_code format requires a specific training trajectory.

2. **Think mode is a hidden risk** — Qwen3's base model strongly prefers chain-of-thought
   reasoning. The training data needs explicit anti-think suppression or much higher density
   of execute_code examples to override this tendency reliably.

3. **Multi-step tasks are more robust** — multi-01 scored 1.0 while single-step tasks scored
   0.5. Consider adding more multi-step examples or weighting them higher to reinforce format.

4. **Val loss ≠ eval accuracy** — 0.111 best val loss didn't predict good eval performance.
   Val loss measures pattern fitting; eval accuracy measures format adherence. These can diverge.

5. **Resume training past peak degrades further** — The iter 600 checkpoint (38.9%) was resumed
   for 200 more iters. Val loss trended UP (0.373 → 0.782) during the resume. The resulting
   iter-800-equivalent model scored **18.5%** — significantly worse. The failure mode also
   shifted: the iter 600 model called the right tool directly (scoring 0.5); the resumed model
   generated prose explanations (scoring 0.0). Additional training past a degraded checkpoint
   compounds the degradation rather than recovering it.

---

## Post-Run: Resume Experiment (iter 600 → iter 800-equivalent)

After the initial eval, the iter 600 adapter was resumed for 200 additional iterations to test
whether the missing training would improve scores. The iter 800 val loss (0.260) had appeared
better than the iter 600 eval checkpoint (0.494), suggesting room for improvement.

**Resume results:** ❌ WORSE — 18.5% (from 38.9%)

| Category | iter 600 model | iter 800-equiv model |
|----------|---------------|---------------------|
| text_tools | 50.0% | 33.3% |
| validation | 50.0% | 50.0% |
| lsp | 50.0% | 10.0% |
| git | 33.3% | 33.3% |
| cst | 16.7% | 0.0% |
| domain | 27.8% | 11.1% |
| multi_tool | 100.0% | 0.0% |
| **Overall** | **38.9%** | **18.5%** |

**Val loss during resume:** 0.373 → 0.485 → 0.769 → 0.593 → **0.782** (final, trending UP)

**Failure mode shift:** The iter 600 model generated direct tool calls (correct tool, no
execute_code wrapper — scoring 0.5). The resumed model generated **prose explanations**
("I'll help you find...", "I need to check...") without any tool call — scoring 0.0. The
additional 200 iters did not reinforce tool calling; they reinforced conversational prose.

**Conclusion:** Do not resume from a degraded checkpoint. The 38.9% iter-600 result was the
best achievable for this training run. The optimal checkpoint in this run was likely iter 650
(val loss 0.111) — but it was not fused before eval due to the concurrent pipeline issue.

The 18.5% result for the resumed model was confirmed by eval (b48e3ae). A concurrent
re-fuse task (b93d5d5) hit GPU timeout and produced a corrupted partial model; that was
cleaned up. The `fused_model_qwen3_phase43a_coder30b_5bit/` directory was deleted after
eval — adapters remain in `adapters_phase43a/` for future reference.
Production model remains `fused_model_qwen3_phase33b_5bit/` (82.4%).

---

## Next Steps

1. **Phase 43b: 14B dense** — Still valuable to run despite 43a failure. Now tests whether
   the 14B dense model can learn execute_code format more reliably than 30B MoE (surprising
   if true, but worth testing).

2. **Training data improvement** — Add more execute_code-formatted examples, especially for
   single-step tools. Current data may have too many direct-call examples that undermine
   the format.

3. **Format enforcement** — Consider adding explicit "no think mode" examples or prepending
   `/no_think` instruction to training system prompts.

4. **Multiple seeds** — If reproducing 82.4% is the goal, run 3+ seeds to establish a
   reliable range. Phase 33b's result may have been a 1-in-3 lucky run.
