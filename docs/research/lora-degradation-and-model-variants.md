# LoRA Degradation Patterns and Model Variant Analysis

**Date:** 2026-02-18
**Branch:** `phase43-model-variants`
**Context:** Phase 40 failure post-mortem + Phase 43 experiment design

---

## Executive Summary

Phase 40 (Qwen3-8B, 18.5%) revealed a clean failure mode: the 8B model learned *which* tool to
call but could not override its base instruction-tuning to adopt the `execute_code` wrapper format.
All four known LoRA degradation patterns have now manifested in Punie's training history. This
document captures that analysis and motivates Phase 43's two competing experiments.

**Two hypotheses remain unresolved:**

| Hypothesis | Prediction |
|------------|-----------|
| A: **Total parameter count** decides capacity | 14B dense (14B active) ≥ threshold → ≥80% |
| B: **MoE routing specialization** decides capacity | 14B dense fails; only MoE succeeds |

Phase 43 tests both. Experiment A re-confirms the Coder-30B MoE baseline (and checks whether
any hyperparameter changes improve domain/multi_tool). Experiment B tests Qwen3-14B dense as a
clean probe of the MoE hypothesis.

---

## Section 1: The Four LoRA Degradation Patterns

Research on LoRA fine-tuning identifies four common failure modes. All four have manifested in
Punie's training history.

### Pattern 1: Quantization Signal Loss

**What it is:** LoRA adapters encode weight *deltas* (small perturbations) that shift the base
model's behavior. If post-fusion quantization uses too few bits, the delta values are rounded away
— the model reverts to base behavior.

**Manifestation in Punie (Phase 5c):**
- During fusion, re-quantization to 4-bit (16 quantization levels) destroyed all LoRA deltas
- 13% of weight bytes changed, but the behavioral signal was erased
- Model produced correct outputs in float16, near-zero accuracy in 4-bit

**Resolution:** 5-bit quantization (32 levels) preserves LoRA deltas. This became a production
standard: fuse → dequantize to float16 → re-quantize to 5-bit.

```
4-bit: 16 levels → rounds LoRA delta ±0.01 to 0 → signal lost  ❌
5-bit: 32 levels → preserves LoRA delta ±0.01                   ✅
```

---

### Pattern 2: Tokenizer/Format Mismatch

**What it is:** Fine-tuning learns to generate tokens in a specific sequence. If the tokenizer
used during training differs from inference, or if the prompt format differs, the learned patterns
don't transfer.

**Manifestation in Punie (Phase 25 + Phase 26.1):**

**Phase 25:** Training data used Qwen3 XML format (`<function=...>`) on a Qwen2.5 base model.
The `<tool_response>` token doesn't exist in Qwen2.5 — it tokenizes as 5 subword pieces instead
of a single token. The multi-turn tool-call pattern was corrupted at the tokenizer level. Result:
0% tool calling accuracy.

**Phase 26.1:** Validation script used plain text prompts (`f"User: {query}\nAssistant:"`) instead
of `tokenizer.apply_chat_template()`. The model was trained on ChatML tokens; the eval used
plaintext. Result: 60-point accuracy drop (88% → 28%).

**Resolution:** Strict requirement to always use `format_prompt()` (which calls
`apply_chat_template`). Documented in CLAUDE.md and enforced via code review.

---

### Pattern 3: Base Model Alignment Override Failure

**What it is:** The base model's instruction-tuning (RLHF/DPO) creates strong priors toward
conversational prose. LoRA must override these priors with the new behavior. If the model lacks
sufficient capacity, the base priors dominate and the LoRA signal doesn't generalize.

**Manifestation in Punie (Phase 40 — 8B dense):**

Val loss of 0.083 at 800 iterations — the 8B model *learned* the training data. But on novel
prompts, it defaulted to conversational prose ("I'll help you...") rather than emitting
`execute_code` wrappers. The fine-tuning signal generalized from training distribution but the
base prose alignment re-emerged on out-of-distribution queries.

Direct calls (no `execute_code`) scored 0.5; no prompt scored 1.0. The model knew *which* tool
to call but not *how* to format the call in Punie's Code Mode.

**30B MoE (Phase 33b, 82.4%):** Same training data, same hyperparameters. The MoE has sufficient
capacity to hold both the base instruction-following priors AND the new Code Mode format — the
LoRA delta is large enough relative to the active parameter space to reliably override.

**Resolution:** Capacity is the binding constraint. The minimum is somewhere between 8B active
parameters (fails) and 3B active parameters via MoE routing (succeeds). This is a paradox that
motivates the MoE hypothesis: 3B active (MoE) beats 8B active (dense).

---

### Pattern 4: Training Distribution Gaps

**What it is:** If training data has systematic gaps — tools, result attributes, or calling
conventions that appear at eval but not in training — the model will hallucinate plausible but
wrong outputs.

**Manifestation in Punie (Phase 33 → 33b audit):**

Phase 33 training data used fabricated domain tool attributes:
- Training used `result.valid_component` (doesn't exist)
- Production code uses `result.valid` / `result.domain` / `result.issues`

The model learned the *structure* of domain tool access but with wrong field names. At eval time,
access patterns like `result.valid_component` raised `AttributeError`. Phase 33b corrected all
tool result attributes to match the actual runtime API.

**Similarly:** CST tools used wrong attribute names (`result.count` instead of
`result.match_count`), and training data included `_direct` suffixes on function names that don't
exist in the tool API.

**Resolution:** All training examples must be validated against the actual runtime API before
training. The Phase 33b audit found and fixed 6 categories of fabricated attributes.

---

## Section 2: Why Code Tools + Flywheel Require LoRA

A natural question after Phase 40's failure: *Why not drop LoRA fine-tuning and use a general
model with prompt engineering?*

### The Code Mode Imperative

Punie's Code Mode uses `execute_code()` as a wrapper for all tool invocations. This is a
Punie-specific convention:

```python
# Code Mode format (required for Punie's execute_code infrastructure):
result = execute_code("""
typecheck(path="src/")
""")

# NOT the model's native tool calling format:
{"name": "typecheck", "arguments": {"path": "src/"}}
```

No base model (pre-trained or instruction-tuned) has priors for Punie's `execute_code` wrapper.
This is always a learned behavior — it cannot be achieved through zero-shot prompting alone.
Fine-tuning is mandatory.

### The Flywheel Dependency

The Flywheel data capture architecture (`docs/research/flywheel-capture.md`) depends on Code Mode:

```
Developer query → Punie generates execute_code() call
                → Monty runner executes it
                → Tool result returned
                → [FLYWHEEL] PunieEvent captures this interaction
                → Post-hoc extraction converts events to training examples
                → Next training cycle improves the model
```

If Punie doesn't use Code Mode (i.e., returns prose answers or native tool calls), the Flywheel
has no structured execution events to capture. The feedback loop breaks.

**Conclusion:** LoRA fine-tuning for Code Mode is not optional — it's what enables the Flywheel.
The alternative (native tool calling format) would require:
1. Regenerating all 1,282 training examples in native format
2. Rebuilding the Monty runner to interpret native calls
3. Rewriting the Flywheel event capture to track native calls
4. Accepting that no base model priors exist for either format

---

## Section 3: MoE vs Dense Capacity Analysis

### The Active Parameter Paradox

Phase 40 produced a counterintuitive result:

| Model | Architecture | Total Params | Active Params/Token | Result |
|-------|-------------|--------------|---------------------|--------|
| Qwen3-8B | Dense | 8B | 8B | ❌ 18.5% |
| Qwen3-30B-A3B | MoE | 30B | ~3B | ✅ 82.4% |

The 8B dense model has **more active parameters per token** than the 30B MoE, yet it fails while
the MoE succeeds. This is the core paradox that motivates Phase 43.

### Hypothesis A: Total Parameter Count

**Claim:** The deciding factor is total parameters, not active parameters per token. MoE models
encode more *knowledge* in their weight matrices even though only a fraction is active per token.

**Evidence for:**
- The 30B MoE has 30B total parameters vs 8B for the dense model
- Even inactive MoE experts contribute to the model's "knowledge capacity"
- Larger models generally have better zero-shot performance on novel formats
- `minimum-model-requirements.md` estimates "20B+ dense minimum"

**Prediction:** Qwen3-14B dense (14B total, 14B active) would succeed (≥80%)

**Against:** 14B < 30B total parameters, and the dense model would only have 14B active vs
30B MoE's full 30B "latent capacity"

### Hypothesis B: MoE Routing Specialization

**Claim:** The MoE architecture provides structural benefits beyond parameter count. Different
experts specialize in different aspects of tool calling:

```
Tool discrimination (which tool?) → Expert set A
Code format generation           → Expert set B
Field access patterns            → Expert set C
Multi-step reasoning             → Expert set D
```

Dense models must encode all capabilities in the same weight matrices, leading to interference.
MoE routes different query types to different expert groups, reducing interference.

**Evidence for:**
- Phase 25b: 7B dense failed even with a perfect experimental setup
- Phase 40: 8B dense has more active params/token but still fails
- The routing mechanism in A3B likely routes tool-calling to code-specialized experts
- Phase 27.5's "cross-tool workflows" failures suggest the MoE still struggles with
  multi-capability tasks

**Prediction:** Qwen3-14B dense (14B total, 14B active) would fail (<80%)

**Against:** No direct evidence that it's routing specifically (vs just total params)

### The Definitive Test

Qwen3-14B dense is the cleanest probe:
- Same model family (same tokenizer, same tool tokens, no format changes needed)
- 14B total params — well above 8B but well below 30B
- All 14B active per token — definitively more than 8B dense

If 14B dense succeeds (≥80%): Hypothesis A wins (total params matter more)
If 14B dense fails (<80%): Hypothesis B wins (MoE routing is structurally important)

---

## Section 4: Qwen3 Think/No_Think Toggle

**Important distinction:** The Qwen3 family includes a "thinking" toggle that is separate from
Instruct alignment.

### What the Toggle Controls

Qwen3 models support two inference modes:

1. **Thinking mode** (`enable_thinking=True`): The model generates `<think>...</think>` tokens
   before the final answer — chain-of-thought reasoning made explicit. This consumes more tokens
   and increases latency.

2. **Non-thinking mode** (`enable_thinking=False`): The model generates a direct answer without
   explicit CoT tokens. Faster, lower latency.

The toggle is activated via the system prompt or model configuration — it is **not** a separate
model variant.

### What the Toggle Does NOT Control

- **Instruct alignment**: Both modes are instruction-tuned. The model doesn't become "base" in
  non-thinking mode.
- **Tool calling capability**: Both modes can generate tool calls.
- **Code Mode learning**: LoRA fine-tuning applies in both modes.

### Implication for Phase 43 Training

**Training data should use non-thinking format.** Punie's Code Mode training data uses:
```python
result = execute_code("""
typecheck(path="src/")
""")
```

This is direct output without `<think>` tokens. Training in thinking mode would:
1. Add `<think>` tokens between the user query and the `execute_code` response
2. Make training examples longer (more tokens)
3. Risk the model generating reasoning prose inside `<think>` blocks instead of executing

**Verification:** When downloading Qwen3-Coder or Qwen3-14B, confirm the model's default
inference behavior with a simple Code Mode prompt. If `<think>` tokens appear, disable thinking:

```python
# In generation config or system prompt:
# System prompt approach: "Think silently. Output only the code."
# Config approach: generation_config.json with enable_thinking: false
```

---

## Section 5: Model Availability Analysis

### Qwen3 Family Landscape

| Model | Architecture | Params | Active | Coder Variant | MLX Available |
|-------|-------------|--------|--------|---------------|---------------|
| Qwen3-1.7B | Dense | 1.7B | 1.7B | No | Yes |
| Qwen3-4B | Dense | 4B | 4B | No | Yes |
| Qwen3-8B | Dense | 8B | 8B | No | Yes (tested: 18.5%) |
| Qwen3-14B | Dense | 14B | 14B | **No** | Yes (untested) |
| Qwen3-32B | Dense | 32B | 32B | No | Yes |
| Qwen3-30B-A3B | MoE | 30B | 3B | **Yes** | Yes (production: 82.4%) |
| Qwen3-235B-A22B | MoE | 235B | 22B | No (yet) | No (too large) |

**Key finding:** Qwen3-Coder only exists in the 30B-A3B MoE variant. There is no 14B Coder,
no 8B Coder, no 32B Coder. The production model (`Qwen3-Coder-30B-A3B-Instruct`) is already the
only available Coder-specialized MoE.

**Implication for Experiment B:** The 14B test uses the general `Qwen3-14B` (not a Coder variant),
which also means it has slightly weaker code-domain priors than the 30B Coder. This is a
confound: if 14B fails, it could be due to capacity OR weaker code pretraining.

### Note on Production Model Naming

Phase 33 and Phase 33b scripts both use `mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit` as
the base model. This is the Coder variant — code-biased pretraining was already applied in the
production training runs. The `minimum-model-requirements.md` lists "Qwen3-Coder-30B-A3B" as
the production model, confirming this.

**Implication for Experiment A:** The Experiment A script (`run_phase43a_coder30b.sh`) runs the
same Coder-30B base model with Phase 33b's hyperparameters but with Phase 43 naming. This serves
as a fresh baseline confirmation and can be used to test any training data improvements (e.g.,
additional domain or multi_tool examples) without confounding with the base model change.

---

## Section 6: Phase 43 Experiment Design

### Experiment A — Qwen3-Coder-30B-A3B (Baseline Confirmation)

**Hypothesis:** Running a fresh training cycle with the Coder-30B base confirms the 82.4%
baseline and may improve domain (60%) and multi_tool (35%) with identical setup.

**Risk:** Low. Same architecture, same tokenizer, same format, same data.

**Variables:** None (same as Phase 33b, different phase number for tracking purposes)

**Success criteria:** Overall ≥82.4% AND (domain >60% OR multi_tool >35%)

**Script:** `scripts/run_phase43a_coder30b.sh`

---

### Experiment B — Qwen3-14B Dense (MoE Hypothesis Test)

**Hypothesis:** 14B dense (14B active) crosses the capacity threshold that 8B (8B active)
could not.

**Risk:** Medium-high. Evidence tilts against success:
- 8B dense failed
- Total params (14B) still below 30B MoE
- No Coder variant (weaker code priors)
- `minimum-model-requirements.md` estimates "20B+ dense minimum"

**Variables:** Architecture (dense vs MoE), base model weights (general vs Coder), total params

**Success criteria:** Overall ≥80%

**Expected outcome matrix:**

| Outcome | Interpretation |
|---------|---------------|
| ≥80% → Hypothesis A | Total params decide; 14B crosses threshold; 10 GB model possible |
| 50-80% → Ambiguous | Capacity and MoE both contribute; 14B partially works |
| <50% → Hypothesis B | MoE routing is structurally necessary beyond param count |
| ~18% → Strong B | 14B failed same way as 8B; MoE is required |

**Script:** `scripts/run_phase43b_14b_dense.sh`

---

## Section 7: LoRA Degradation Prevention Standards

Based on all four degradation patterns, these standards are now mandatory for any Phase 43+
training run:

### Pre-Training Checklist

```bash
# 1. Tokenizer compatibility check (prevents Pattern 2)
uv run python scripts/phase40_tokenizer_check.py --model <new-model>
# Must find: <tool_call> <tool_response> as single tokens

# 2. Training data validation (prevents Pattern 4)
uv run python scripts/validate_training_data.py --data data/phase33_merged
# Must verify: all tool result attributes match runtime API

# 3. Format consistency check (prevents Pattern 2)
uv run python scripts/run_phase33_direct_eval.py --model <base-model> --port 8080
# Zero-shot baseline; confirms format_prompt() works before fine-tuning
```

### Post-Training Checklist

```bash
# 4. Quantization: always fuse → float16 → re-quantize (prevents Pattern 1)
uv run python -m mlx_lm fuse ... --dequantize   # → float16
uv run python -m mlx_lm convert ... --q-bits 5  # → 5-bit (32 levels)
# Never: --q-bits 4 (destroys LoRA signal)

# 5. Eval: use run_phase33_direct_eval.py (prevents Pattern 2)
uv run python scripts/run_phase33_direct_eval.py --model <fused-5bit>
# Never: manual format strings; always format_prompt()
```

---

## Section 8: Results and Next Steps

### Experiment A (Coder-30B) — COMPLETE ❌

**Actual result: 38.9%** (target ≥82.4%)

Phase 43a did NOT reproduce Phase 33b's 82.4%. The failure mode differs from Phase 40 (8B dense)
in one key way: the 30B MoE learned correct tool routing but reverted to direct calls (0.5 score)
instead of execute_code wrappers (1.0 score). Additionally, 10/27 prompts triggered think-mode
interference with no tool call at all.

**Score distribution (Phase 43a vs Phase 33b):**

| Score | Phase 33b | Phase 43a |
|-------|-----------|-----------|
| 1.0 (execute_code ✓) | ~22/27 | 1/27 (multi-01 only) |
| 0.5 (direct call) | ~5/27 | 16/27 |
| 0.0 (prose/timeout) | ~0/27 | 10/27 |

**Key finding:** Phase 33b's 82.4% is NOT a reproducible stable baseline. The execute_code
format wrapper is **stochastically learned** — this training trajectory found a local optimum
that routes correctly but doesn't reliably format. This adds a **5th degradation pattern**:

### Pattern 5: Stochastic Format Lock (NEW — Phase 43a)

**What it is:** With identical model, data, and hyperparameters, different training runs produce
different format adherence. One run reliably uses execute_code (Phase 33b: 82.4%); another uses
direct calls or think mode (Phase 43a: 38.9%). The difference is random mini-batch ordering and
gradient trajectory, not data coverage.

**Manifestation in Punie (Phase 43a):**
- Same Coder-30B base, same 1,282 examples, same 800 iters, same lr/layers
- Phase 33b: 22/27 prompts at 1.0 (execute_code format locked in)
- Phase 43a: 1/27 prompts at 1.0 (execute_code format NOT locked in)
- Val loss 0.111 (better than Phase 33b!) yet eval accuracy crashed

**Implication:** Val loss is NOT a reliable predictor of format adherence. The gradient can
find a lower-loss solution that reproduces tool names but forgets format structure. This is a
form of "format forgetting" during training.

**Resolution candidates:**
1. Multiple seeds — run 3+ times, take best (expensive but simple)
2. Format-weighted loss — upweight execute_code wrapper tokens in training loss
3. Higher LoRA layers — more layers = more format capacity
4. Anti-think examples — explicit training examples that suppress `<think>` tokens
5. Longer training with early stopping on eval accuracy (not val loss)

**Detail:** See `docs/research/phase43a-coder30b-results.md`

### Phase 44 — Format Lock Fix Attempt (COMPLETE ❌)

**Actual result: 22.2%** (target ≥80%) — worse than Phase 43a (38.9%)

Phase 44 applied three infrastructure fixes and re-trained with seed=42:
1. Added `<think>` to eval stop sequences → ✅ eliminated think-mode timeouts
2. Removed `_direct` suffix from eval system prompt → unknown isolated effect
3. seed=42 + best-checkpoint selection → different training trajectory

The think-mode fix worked. But Phase 44's model shifted to a **new failure mode**: prose
generation without any tool call. 15/27 prompts generated "I'll help you..., Let me first
check..." responses scoring 0.0, where Phase 43a had 16/27 direct tool calls scoring 0.5.

This adds a **6th degradation pattern**:

### Pattern 6: Prose Drift Under Seed Variation (NEW — Phase 44)

**What it is:** Different random seeds converge to different failure modes while keeping the
same overall format breakdown. seed=42 produced prose drift (0.0) instead of Phase 43a's
direct-call drift (0.5). Val loss was better (0.176 vs 0.260) but eval was worse (22.2% vs 38.9%).

**Manifestation in Punie (Phase 44):**
- seed=42, save-every=100, best checkpoint at iter 800 (val_loss=0.176, still decreasing)
- 12/27 direct tool calls (0.5) — same intent routing as Phase 43a
- 15/27 prose generation (0.0) — new mode: model describes what to do but doesn't do it
- 0/27 execute_code calls (1.0) — complete failure to apply wrapper format

**Score distribution (all runs with Coder-30B):**

| Score | Phase 33b | Phase 43a | Phase 44 |
|-------|-----------|-----------|---------|
| 1.0 (execute_code ✓) | ~22/27 | 1/27 | 0/27 |
| 0.5 (direct call) | ~5/27 | 16/27 | 12/27 |
| 0.0 (timeout/prose) | ~0/27 | 10/27 | 15/27 |
| **Overall** | **82.4%** | **38.9%** | **22.2%** |

**Key insight:** Best val loss (0.176 at iter 800) selected a local minimum where the model
learned conversational prose patterns from the base model alignment, not the execute_code format.
Val loss optimization leads to different local minima depending on seed.

**Implication:** Best-checkpoint selection by val loss is insufficient for format-sensitive tasks.
Format-aware evaluation during training (scoring execute_code calls, not token loss) is needed.

**Resolution candidates (updated from Pattern 5):**
1. Format-aware early stopping — eval execute_code format during training, not val loss
2. Multiple seeds — run 3+ times; Phase 33b's 82.4% appears to be ~1/3 probability
3. Format-weighted loss — upweight execute_code wrapper tokens in training loss
4. Higher LoRA layers — more layers = more format capacity
5. Anti-think examples + anti-prose examples — explicit training to suppress wrong formats

**Detail:** See `docs/research/phase44-format-fix-results.md`

### After Experiment B (14B Dense)

Three scenarios remain valid despite 43a's failure:

**If ≥80%:**
- The 10 GB production model is feasible (vs current 20 GB)
- Latency estimate: ~1-2s (half of 30B MoE, given dense but smaller)
- AND: demonstrates 14B dense has more reliable format lock-in than 30B MoE stochastic

**If 50-79%:**
- Interesting middle ground; may be improvable with more LoRA layers or more training data
- Not a clear binary outcome; may require Phase 44 investigation

**If <50% (especially ~18% like Phase 40):**
- MoE routing hypothesis confirmed for both capacity AND format learning
- Focus Phase 44+ on improving format reliability with the 30B MoE
- 14B dense is conclusively ruled out for Punie's Code Mode

### Updating the Comparison Table

`docs/research/minimum-model-requirements.md` should be updated with Phase 43 results.

---

## References

- `docs/research/phase40-8b-results.md` — Phase 40 failure analysis (18.5%)
- `docs/research/minimum-model-requirements.md` — Model requirements framework
- `docs/research/flywheel-capture.md` — Flywheel event capture architecture
- `docs/research/prompt-format-consistency.md` — Phase 26.1 format analysis
- `scripts/run_phase33b_overnight.sh` — Production training pipeline template
- `scripts/run_phase33_direct_eval.py` — 27-prompt eval harness
- `CLAUDE.md` — Project standards (prompt format requirement)
