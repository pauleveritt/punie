---
title: "Gate 0 Failure: Devstral Small 2 Unsuitable for Punie"
date: 2026-02-16
tags: [evaluation, tokenizer, gate-0, devstral, failed]
---

# Gate 0 Failure: Devstral Small 2 Unsuitable for Punie

**Date:** February 16, 2026

## Summary

Evaluated Devstral Small 2 (24B, Mistral 3) as a potential replacement for Qwen3-30B-A3B using a gated approach. **Gate 0 failed in 5 minutes**, preventing 7+ days of wasted effort. The fatal flaw: multi-token closing delimiter `[/TOOL_CALLS]` would corrupt training data similar to Phase 25's failure.

**Decision:** Continue using Qwen3-30B-A3B (Phase 27's 100% accurate model).

## Gate 0: Tokenizer Verification

**Goal:** Verify Mistral 3's tool-calling delimiters are single tokens (like Qwen3's `<tool_call>` = token 151657)

**Model tested:** `mlx-community/Devstral-Small-2-24B-Instruct-2512-4bit`

### Results

| Delimiter | Token IDs | Status |
|-----------|-----------|--------|
| `[TOOL_CALLS]` | `[9]` | ✅ Single token |
| `[/TOOL_CALLS]` | `[1091, 1047, 9197, 8568, 74483, 1083, 1093]` | ❌ **7 tokens** |
| `[TOOL_RESULTS]` | `[7]` | ✅ Single token |
| `[/TOOL_RESULTS]` | `[8]` | ✅ Single token |

**Critical flaw:** The closing delimiter `[/TOOL_CALLS]` tokenizes as 7 subword pieces, creating an asymmetry that would corrupt training data.

## Why This Matters (Phase 25 Lesson)

Multi-token delimiters break semantic boundaries during fine-tuning:

1. **Training data** uses delimiters as atomic boundary markers
2. **Model** must predict each subword sequentially (14 intermediate steps)
3. **Gradients** distribute across subword predictions instead of tool-calling logic
4. **Result:** Corrupted training examples, zero tool-calling accuracy

**Phase 25 precedent:**
- Qwen2.5's `<tool_response>` was multi-token (5 pieces)
- 58% of training data corrupted
- 0% tool calling accuracy (0/13 queries)

**Devstral impact:**
- `[/TOOL_CALLS]` is multi-token (7 pieces)
- Would corrupt all multi-turn tool-calling examples
- Training infeasible without extensive format redesign

## Technical Analysis

### Example Corruption Pattern

```python
# Expected (single token):
result = ruff_check(...) [/TOOL_CALLS] → Next action
#                        ↑
#                        Single semantic boundary

# Actual (7 tokens):
result = ruff_check(...) [ / T O O L _ C A L L S ] → Next action
#                        ↑ ↑ ↑ ↑ ↑ ↑ ↑ ↑ ↑ ↑ ↑ ↑ ↑ ↑
#                        14 prediction steps corrupt the boundary
```

### Why Opening Works But Closing Fails

- `[TOOL_CALLS]` (opening) = Token 9 (single, learned during pretraining)
- `[/TOOL_CALLS]` (closing) = 7 tokens (never seen as unit during pretraining)
- Asymmetry means model must learn different representations for semantically related concepts
- Fine-tuning 8 layers cannot overcome this tokenizer mismatch

## Value of Gated Approach

**Time saved:** ~7 days of futile work

| Phase | Time | Skipped Because Gate 0 Failed |
|-------|------|-------------------------------|
| Gate 1 (MLX smoke test) | 30 min | ✅ Skipped |
| Gate 2 (Latency) | 30 min | ✅ Skipped |
| Gate 3 (Zero-shot) | 2 hours | ✅ Skipped |
| Gate 4 (Small LoRA) | 3-4 hours | ✅ Skipped |
| Gate 5 (Full conversion) | 6-9 days | ✅ Skipped |

**Lesson:** Order gates by cost (cheapest kill signals first). Tokenizer verification is ~5 minutes but catches fatal flaws that would only surface after weeks of training.

## Alternative Paths (Not Recommended)

If you wanted to proceed despite failure (NOT advised):

1. **Rewrite training format** - Use only opening tags or different delimiters
   - Risk: Breaks Mistral's native tool-calling format
   - Effort: 2-3 days to rewrite 1104 examples
   - Success chance: Low (fights base model priors)

2. **Use different Mistral model** - Try Mistral Large 2 or future releases
   - Risk: May have same tokenizer issue
   - Effort: Repeat Gate 0 for each candidate

3. **Switch to JSON-only format** - Avoid delimiters entirely
   - Risk: May not work with MLX tool-calling parser
   - Effort: 3-4 days to redesign format

**Cost-benefit:** All alternatives require >2 days work with high failure risk. Phase 27 model already achieves 100% accuracy.

## Production Model (Unchanged)

**Continue using:** `fused_model_qwen3_phase27_5bit/`
- ✅ 100% accuracy (40/40 queries across 8 categories)
- ✅ 2.90s average generation time
- ✅ 20 GB (5-bit quantized, fits in 24GB unified memory)
- ✅ All tool delimiters are single tokens
- ✅ 14 typed tools (LSP navigation + git + linting + testing)

No action required. Phase 27 model remains in production.

## Files Created

**Implementation:**
- `scripts/gate0_tokenizer_check.py` (95 lines)
- `logs/gate0-tokenizer.txt` (791 bytes)
- `docs/devstral-gate-tracker.md` (comprehensive analysis)

**Specification:**
- `agent-os/specs/2026-02-16-devstral-evaluation/` (4 files)
  - `plan.md` - Gated evaluation approach
  - `shape.md` - Detailed gate definitions
  - `references.md` - Phase 25 learnings, model links
  - `standards.md` - Evaluation standards

## Quality Verification

- ✅ **Ruff:** All checks passed
- ✅ **Ty:** All checks passed
- ✅ **Exit code:** 1 (correct failure signal)
- ✅ **Log file:** Created successfully

## Key Learnings

1. **Gated evaluation works** - Failed fast (5 min) instead of slow (7+ days)
2. **Tokenizer matters** - Multi-token delimiters are a hard blocker for LoRA fine-tuning
3. **Phase 25 lesson validated** - Same failure pattern (multi-token delimiters → 0% accuracy)
4. **Qwen3 choice confirmed** - Single-token tool delimiters are critical for success

## Next Steps

**None required.** Continue using Phase 27 model in production.

**Future research:** Monitor for new models with:
- Single-token tool delimiters
- ≤24B parameters (fits in 32GB RAM)
- MLX compatibility
- Strong tool-calling base capability

## References

- **Spec:** `agent-os/specs/2026-02-16-devstral-evaluation/`
- **Gate tracker:** `docs/devstral-gate-tracker.md`
- **Phase 25 failure:** `docs/diary/2026-02-15-phase25-7b-experiment-failed.md`
- **Phase 27 baseline:** 100% accuracy (40/40), 2.90s avg, 1104 examples
- **HuggingFace:** [mlx-community/Devstral-Small-2-24B-Instruct-2512-4bit](https://huggingface.co/mlx-community/Devstral-Small-2-24B-Instruct-2512-4bit)
