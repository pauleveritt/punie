# Devstral Small 2 Evaluation - Gated Approach

## Goal

Determine if **Devstral Small 2** (24B dense, Mistral 3) can replace Qwen3-30B-A3B as Punie's local model via a gated evaluation that fails fast and cheap.

## Context

We have a detailed evaluation of Devstral Small 2 in `docs/research/minimum-model-requirements.md` with **9 identified risks**. This spec breaks the evaluation into small, sequential gates ordered by cost (cheapest kill signals first). Each gate has a clear pass/fail criterion.

**Key principle:** Fail fast, fail cheap. Don't invest 6-9 days in full conversion until all low-cost gates pass.

## Gated Evaluation Plan

### Gate 0: Tokenizer Verification (~5 minutes)

**Goal:** Verify that Mistral 3's tool-calling tokens are single tokens in the vocabulary.

**Method:**
1. Download `mistral-community/Devstral-Small-2-instruct-2503-MLX` tokenizer
2. Check tokenization of Mistral's tool delimiters:
   - `[TOOL_CALLS]` → should be single token
   - `[/TOOL_CALLS]` → should be single token
   - `[TOOL_RESULTS]` → should be single token
   - `[/TOOL_RESULTS]` → should be single token

**Pass criterion:** All 4 delimiters are single tokens (like Qwen3's `<tool_call>` = token 151657)

**Fail criterion:** Any delimiter is multi-token (like Qwen2.5's `<tool_response>` = 5 subword pieces)

**Why this gate matters:** Addresses Risk 1 (tokenizer differences). Phase 25 showed that multi-token tool delimiters corrupt training data. This is the fastest kill signal.

**If FAIL:** ❌ **NO-GO** - Stop immediately. Multi-token delimiters make training infeasible (58% of training data would be corrupted).

**If PASS:** ✅ Proceed to Gate 1

---

### Gate 1: Download + MLX Smoke Test (~30 minutes)

**Goal:** Verify that the 5-bit quantized model downloads correctly and runs basic inference on Apple Silicon.

**Method:**
1. Download `mistral-community/Devstral-Small-2-instruct-2503-MLX` (5-bit quantized, ~14 GB)
2. Run basic inference test:
   ```python
   from mlx_lm import load, generate
   model, tokenizer = load("mistral-community/Devstral-Small-2-instruct-2503-MLX")
   prompt = "Write a Python function to check if a number is prime."
   response = generate(model, tokenizer, prompt=prompt, max_tokens=512)
   print(response)
   ```
3. Measure:
   - Load time (target: <10s)
   - Memory usage (target: <20 GB)
   - Does it generate coherent code?

**Pass criterion:**
- Model loads without errors
- Generates coherent code
- Memory usage ≤20 GB (fits in 24 GB unified memory with headroom)

**Fail criterion:**
- Load fails
- Generates gibberish
- Memory usage >20 GB (won't fit with Punie's runtime overhead)

**Why this gate matters:** Addresses Risk 9 (MLX compatibility). If the model doesn't work with MLX at all, no point proceeding.

**If FAIL:** ❌ **NO-GO** - Stop. Model is incompatible with MLX or too large for target hardware.

**If PASS:** ✅ Proceed to Gate 2

---

### Gate 2: Latency Benchmark (~30 minutes)

**Goal:** Verify that generation speed is comparable to Qwen3-30B-A3B (avg 2.9s per query).

**Method:**
1. Run 10 representative queries from Phase 27 validation suite
2. Measure average generation time
3. Compare to Qwen3 baseline (2.9s)

**Pass criterion:** Average generation time ≤15s (5x slower is acceptable for evaluation, but flags performance risk)

**Fail criterion:** Average generation time >15s (too slow for interactive use)

**Why this gate matters:** Addresses Risk 3 (speed). If Devstral is 10x slower than Qwen3, it's not a viable replacement regardless of accuracy.

**If FAIL:** ⚠️ **SOFT NO-GO** - Proceed only if speed is acceptable for your use case. Document as known limitation.

**If PASS:** ✅ Proceed to Gate 3

---

### Gate 3: Zero-Shot Tool Calling (~2 hours)

**Goal:** Test if Devstral can do tool calling in its native Mistral format without any fine-tuning.

**Method:**
1. Create 5 test queries that require tool calls (from Phase 27 validation suite)
2. Format using Mistral's tool-calling format:
   ```
   [TOOL_CALLS]
   [{"name": "read_text_file", "arguments": {"path": "src/foo.py"}}]
   [/TOOL_CALLS]
   ```
3. Run queries with no fine-tuning (base model only)
4. Check if model generates tool calls in correct format

**Pass criterion:** Model generates at least 1 correct tool call (any format, even if not perfect) → shows it understands tool-calling concept

**Fail criterion:** Model generates 0 tool calls, only generates natural language → no tool-calling capability

**Why this gate matters:** Addresses Risk 2 (tool-calling format) and Risk 5 (tool-calling capability). If Devstral has zero tool-calling ability, fine-tuning may not be enough.

**If FAIL:** ⚠️ **PROCEED WITH CAUTION** - Model may need more aggressive fine-tuning or may not be suitable. Proceed to Gate 4 but lower expectations.

**If PASS:** ✅ Proceed to Gate 4 with high confidence

---

### Gate 4: Small-Scale LoRA (~3-4 hours)

**Goal:** Test if LoRA fine-tuning can teach Devstral to use Punie's tool format on a small dataset.

**Method:**
1. **Convert 100 examples** from Phase 27 training data (1104 total) to Mistral format:
   - Replace `<tool_call>` with `[TOOL_CALLS]`
   - Replace `</tool_call>` with `[/TOOL_CALLS]`
   - Convert XML to Mistral JSON: `<function=execute_code>` → `{"name": "execute_code", "arguments": {...}}`
2. **Train for 50 iterations** (10% of Phase 27's 500 iters):
   - Batch size 1, lr 1e-4, 8 layers (same as Phase 27)
3. **Test on 10 queries** from Phase 27 validation suite
4. **Measure accuracy:** How many queries result in correct tool calls?

**Pass criterion:** Accuracy ≥60% (6/10 queries) → shows LoRA can teach tool format

**Fail criterion:** Accuracy <60% → LoRA not effective, or needs much more data

**Why this gate matters:** Addresses Risk 2 (format), Risk 4 (LoRA compatibility), Risk 6 (training convergence). This is the last cheap gate before full commitment.

**If FAIL:** ❌ **NO-GO** - Stop. If 100 examples + 50 iters can't teach basic tool calling, full training is unlikely to succeed.

**If PASS:** ✅ **GREEN LIGHT** - Proceed to Gate 5 (full conversion) as a separate phase

---

### Gate 5: Full Conversion + Training (6-9 days) - SEPARATE PHASE

**Goal:** Full conversion of 1104 Phase 27 examples + 500-iteration training + comprehensive validation.

**Method:**
1. Convert all 1104 examples to Mistral format
2. Train full LoRA adapter (500 iters, same hyperparameters as Phase 27)
3. Fuse + quantize to 5-bit (same as Qwen3)
4. Run full Phase 27 validation suite (40 queries across 8 categories)

**Pass criterion:** Accuracy ≥85% (34/40 queries) - matches Phase 27's 100% target adjusted for new model

**Fail criterion:** Accuracy <85% → Devstral cannot match Qwen3's performance

**Why this is a separate phase:** This is the expensive path. Only attempt if all Gates 0-4 pass.

## Decision Matrix

| Gate | Pass | Fail | Next Action |
|------|------|------|-------------|
| Gate 0 | ✅ Proceed to Gate 1 | ❌ **STOP** - Multi-token delimiters |
| Gate 1 | ✅ Proceed to Gate 2 | ❌ **STOP** - MLX incompatible |
| Gate 2 | ✅ Proceed to Gate 3 | ⚠️ Proceed but flag performance risk |
| Gate 3 | ✅ High confidence → Gate 4 | ⚠️ Low confidence → Gate 4 |
| Gate 4 | ✅ **GREEN LIGHT** → Gate 5 | ❌ **STOP** - LoRA ineffective |
| Gate 5 | ✅ **DEPLOY** | ❌ Stick with Qwen3 |

## Risk Mapping

Each gate addresses specific risks from `docs/research/minimum-model-requirements.md`:

| Gate | Risks Addressed |
|------|-----------------|
| Gate 0 | Risk 1 (tokenizer) |
| Gate 1 | Risk 9 (MLX compatibility) |
| Gate 2 | Risk 3 (speed) |
| Gate 3 | Risk 2 (format), Risk 5 (tool-calling capability) |
| Gate 4 | Risk 2 (format), Risk 4 (LoRA compatibility), Risk 6 (convergence) |
| Gate 5 | Risk 7 (accuracy), Risk 8 (quality) |

## Cost Analysis

| Phase | Time Investment | Can Abort? | Dependencies |
|-------|----------------|------------|--------------|
| Gates 0-1 | ~35 min | Yes | None |
| Gate 2 | ~30 min | Yes | Gate 1 pass |
| Gate 3 | ~2 hours | Yes | Gate 2 pass |
| Gate 4 | ~3-4 hours | Yes | Gate 3 pass |
| **Total (pre-commitment)** | **~4-7 hours** | **Yes** | **All gates pass** |
| Gate 5 | **6-9 days** | Only after full training | **All Gates 0-4 pass** |

**Key insight:** You can explore Devstral with <7 hours of work before committing to the 6-9 day full conversion.

## Success Criteria

### Gates 0-4 (Pre-Commitment)
- ✅ All 4 tool-call tokens are single tokens (Gate 0)
- ✅ Model loads and runs on MLX (Gate 1)
- ✅ Generation speed is acceptable (<15s avg) (Gate 2)
- ✅ Model shows tool-calling capability (Gate 3)
- ✅ Small-scale LoRA achieves ≥60% accuracy (Gate 4)

### Gate 5 (Full Evaluation) - SEPARATE PHASE
- ✅ Full training converges (val loss reduction ≥80%, like Phase 27)
- ✅ Validation accuracy ≥85% (34/40 queries)
- ✅ All 8 validation categories show strong performance
- ✅ Performance comparable to Qwen3 (2-5x variation acceptable)

## References

- **Requirements Analysis:** `docs/research/minimum-model-requirements.md` (9 risks)
- **Phase 27 Baseline:** 100% accuracy (40/40), 2.90s avg generation, 1104 examples
- **Phase 25 Learnings:** Multi-token tool delimiters = training corruption
- **Mistral Format:** `[TOOL_CALLS]` + JSON (not XML)
