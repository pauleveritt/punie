# Phase 40: Qwen3-8B Smaller Model — Results

**Date:** 2026-02-18
**Branch:** `phase40-smaller-model`
**Model:** `fused_model_qwen3_phase40_8b_5bit/` (5.3 GB)
**Result:** ❌ FAIL — 18.5% (target ≥80%)

---

## Summary

Phase 40 tested whether a Qwen3-8B dense model (8B params, 5.3 GB) could match the Phase 33b
Qwen3-30B MoE result (82.4%) by training on the same 1,282-example dataset with the same
hyperparameters. The hypothesis was that with 26 domain tools handling reasoning, the model only
needs to *route* — and 8B might suffice at 4x lower inference cost.

**The hypothesis is disproved.** 8B achieved 18.5% vs 30B's 82.4%. The failure mode is
instructive: the 8B model learned *which* tool to call but not *how* to format the call. Every
passing score was 0.5 (partial credit for a direct tool call without the `execute_code` wrapper),
never 1.0 (full credit for the correct Code Mode format). The 8B model could not reliably override
its base instruction-tuning with the `execute_code` wrapping pattern.

---

## Pre-Registered Success Criteria vs Actual

| Category | Phase 33b Baseline | Phase 40 Target | Phase 40 Actual | Pass? |
|----------|--------------------|-----------------|-----------------|-------|
| text_tools | 100% | ≥95% | 33.3% | ❌ |
| validation | 100% | ≥95% | 50.0% | ❌ |
| git | 100% | ≥90% | 33.3% | ❌ |
| cst | 100% | ≥90% | 0.0% | ❌ |
| lsp | 90% | ≥80% | 10.0% | ❌ |
| domain | 60% | ≥60% | 11.1% | ❌ |
| multi_tool | 35% | ≥35% | 0.0% | ❌ |
| **Overall** | **82.4%** | **≥80%** | **18.5%** | ❌ |

---

## Per-Prompt Results

| Prompt ID | Query (truncated) | Score | Time | Notes |
|-----------|-------------------|-------|------|-------|
| text-01 | Show contents of config.py | 0.00 | 18.2s | Prose response, no tool call |
| text-02 | Write text to output/summary.txt | 0.50 | 1.8s | Direct call, no execute_code |
| text-03 | Run 'ls src/' | 0.50 | 7.6s | Direct call, no execute_code |
| valid-01 | Run type checking on src/ | 0.50 | 13.4s | Direct call, no execute_code |
| valid-02 | Check src/ with ruff | 0.50 | 1.3s | Direct call, no execute_code |
| valid-03 | Run test suite in tests/ | 0.50 | 2.7s | Direct call, no execute_code |
| lsp-01 | Find definition of AgentConfig | 0.00 | 13.3s | Timeout — prose then no call |
| lsp-02 | Find references to execute_code | 0.00 | 13.4s | Timeout — prose then no call |
| lsp-03 | Type info for LoRAConfig | 0.00 | 13.5s | Timeout — prose then no call |
| lsp-04 | List symbols in lora_config.py | 0.00 | 5.3s | Wrong tool (workspace_symbols prose) |
| lsp-05 | Search for TrainingResult symbol | 0.50 | 57.7s | Direct call eventually, very slow |
| git-01 | Check git status | 0.50 | 5.1s | Direct call, no execute_code |
| git-02 | Show git diff | 0.00 | 2.6s | Prose only, no tool call |
| git-03 | List 5 recent git commits | 0.50 | 1.2s | Direct call, no execute_code |
| cst-01 | Find class definitions in websocket.py | 0.00 | 13.5s | Timeout |
| cst-02 | Rename TrainingResult to FineTuneResult | 0.00 | 13.6s | Timeout |
| cst-03 | Add defaultdict import | 0.00 | 6.3s | Prose only |
| dom-01 | Validate error_page.py as tdom component | 0.50 | 2.1s | Direct call, no execute_code |
| dom-02 | Check service registration | 0.00 | 13.5s | Timeout |
| dom-03 | Check middleware conventions | 0.00 | 13.6s | Timeout |
| dom-04 | Check dependency graph violations | 0.00 | 13.4s | Timeout |
| dom-05 | Check t-string usage in registration.py | 0.00 | 13.6s | Timeout |
| dom-06 | Validate route patterns in api.py | 0.50 | 13.5s | Direct call, no execute_code |
| dom-07 | Verify render tree in checkout.py | 0.00 | 3.8s | Prose only |
| dom-08 | Check Inject[] imports | 0.00 | 13.5s | Timeout |
| dom-09 | Check html() context= in account.py | 0.00 | 13.5s | Timeout |
| multi-01 | Find HomeView, read, validate as tdom | 0.00 | 27.6s | Prose only, no tool chain |

**Score distribution:**
- 1.0 (execute_code + correct keyword): 0 prompts
- 0.5 (direct tool call, correct tool): 10 prompts
- 0.0 (prose/timeout/wrong): 17 prompts

---

## Failure Mode Analysis

### Pattern 1: Direct calls instead of execute_code (10 prompts, score 0.5)

The model knows *which* tool to use but doesn't wrap it in `execute_code()`. It calls the tool
directly — which is partially correct (hence 0.5) but not the Code Mode format the system is
trained to use.

This indicates the 8B model learned intent routing but couldn't consistently override its base
instruction-tuning to adopt the `execute_code` wrapper pattern. The 30B model has enough capacity
to hold both: "what tool" AND "how to call it."

### Pattern 2: Timeouts at ~13.5s (12 prompts, score 0.0)

Many prompts show ~13.5s response times with prose output ("I'll help you find...", "I need to
check...") but no tool call before the token limit. The model generates reasoning prose in the
style of its instruction tuning and either hits `max_tokens` or runs out of "will" to commit to a
tool call format.

These are concentrated in: lsp (4/5), cst (2/3), domain (7/9) — the more complex/specialized
tools. Simpler tools (validation, git) had more direct calls.

### Pattern 3: Tool-specific knowledge gaps (cst 0.0%, multi_tool 0.0%)

CST tools scored 0% — the model generated prose for all three but never committed to
`cst_find_pattern`, `cst_rename`, or `cst_add_import`. The `multi-01` prompt requiring a
3-step chain (find → read → validate) also scored 0.0. These require the model to both adopt
the execute_code format AND chain multiple calls — two things the 8B model consistently fails.

---

## Training Metrics

| Metric | Value |
|--------|-------|
| Training time | 44 min (from iter 0) |
| Fuse time | <1 min |
| Quantize time | <1 min |
| Total pipeline | 49 min |
| Final model size | 5.3 GB (vs 20 GB for 30B) |
| Val loss at iter 50 | 0.612 |
| Val loss at iter 250 | 0.281 |
| Val loss at iter 650 | 0.083 |
| Peak memory | 9.073 GB |
| LoRA params | 9.699M / 8190.735M = 0.118% |

Val loss of 0.083 at iter 650 is excellent — the model *learned* the training data well. The
failure is not insufficient learning but insufficient model capacity: it can reproduce training
patterns but can't generalize the execute_code wrapper reliably across 26 tools and novel prompts.

---

## Comparison with Phase 25 (Previous 7B Attempt)

| Aspect | Phase 25 (7B, 0%) | Phase 40 (8B, 18.5%) |
|--------|-------------------|----------------------|
| Model | Mistral-7B (wrong family) | Qwen3-8B (same family) |
| Tokenizer | Mismatch with training data | Verified identical (preflight ✓) |
| Tools | 6 | 26 |
| Training examples | 857 | 1,282 |
| Failure mode | Tokenizer corruption | Cannot learn execute_code wrapper |
| Partial credit | None | 10 prompts at 0.5 |

Phase 40 is a genuine improvement over Phase 25 — the model learned intent routing and produced
the right tool name in 10/27 cases. But it still falls far short of the ≥80% target.

---

## Verdict

**The 8B hypothesis is disproved for this task formulation.**

The Code Mode execute_code wrapping pattern requires sufficient model capacity to override strong
base instruction-tuning. Qwen3-8B is too aligned with its base conversational behavior (prose
responses) to consistently adopt the required tool-call format, even after fine-tuning on 1,282
examples.

**Production model remains:** `fused_model_qwen3_phase33b_5bit/` (20 GB, 82.4%)

---

## Next Steps (Options)

1. **Accept the result** — 30B MoE is the right model; 8B cannot route 26 tools in Code Mode.
   Phase 41 should focus on improving weak categories (domain 60%, multi_tool 35%) on the 30B.

2. **Change the format** — If native tool calls (not execute_code) were the target format, 8B's
   direct calls would score 1.0. A format change would require regenerating all 1,282 training
   examples in native tool call format and retraining both models.

3. **Try Qwen3-14B** — A middle point between 8B and 30B. The failure gradient suggests capacity
   is the bottleneck; 14B might cross the threshold. Estimated ~10 GB, ~2s response.
