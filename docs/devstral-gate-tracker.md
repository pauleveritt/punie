# Devstral Evaluation - Gate Tracker

## Gate 0: Tokenizer Verification ❌ FAILED

**Date:** 2026-02-16
**Time:** 5 minutes
**Result:** Multi-token delimiter detected

### Tokenizer Tested

**Model:** `mlx-community/Devstral-Small-2-24B-Instruct-2512-4bit`
**Tokenizer:** TokenizersBackend (Mistral 3)

### Delimiter Analysis

| Delimiter | Token IDs | Status |
|-----------|-----------|--------|
| `[TOOL_CALLS]` | `[9]` | ✅ Single token |
| `[/TOOL_CALLS]` | `[1091, 1047, 9197, 8568, 74483, 1083, 1093]` | ❌ **7 tokens** |
| `[TOOL_RESULTS]` | `[7]` | ✅ Single token |
| `[/TOOL_RESULTS]` | `[8]` | ✅ Single token |

### Critical Finding

**Failed Delimiter:** `[/TOOL_CALLS]` tokenizes as 7 subword pieces

**Impact:** This asymmetry between opening delimiter (1 token) and closing delimiter (7 tokens) would corrupt training data similar to Phase 25's failure:
- Phase 25: Qwen2.5's `<tool_response>` was multi-token → 58% of training data corrupted → 0% tool calling accuracy
- Devstral: `[/TOOL_CALLS]` is multi-token → Would corrupt all multi-turn tool-calling examples

### Technical Details

**Why multi-token delimiters corrupt training:**
1. Training data uses delimiter as atomic boundary marker
2. Model learns to predict entire delimiter as single step
3. Multi-token delimiters require predicting each subword sequentially
4. Breaks the semantic boundary between tool call and response
5. Gradients get distributed across subword predictions instead of tool-calling logic

**Example corruption:**
```
# Expected (single token):
result = ruff_check(...) [/TOOL_CALLS] → Next step

# Actual (7 tokens):
result = ruff_check(...) [ / T O O L _ C A L L S ] → Next step
                         ↑ ↑ ↑ ↑ ↑ ↑ ↑ ↑ ↑ ↑ ↑ ↑ ↑ ↑
                         14 intermediate prediction steps corrupt the boundary
```

### Decision: ❌ **NO-GO - STOP EVALUATION**

**Verdict:** Devstral Small 2 is **not suitable** for Punie's fine-tuning approach.

**Reason:** Multi-token closing delimiter makes training infeasible. Even with workarounds (e.g., training data without closing tags), the asymmetry would require extensive format changes and likely degrade accuracy.

**Recommendation:** Stick with **Qwen3-30B-A3B** (Phase 27's 100% accurate model) which has symmetric single-token delimiters.

### Alternative Paths (Not Recommended)

If you wanted to proceed despite this failure (NOT advised):

1. **Rewrite training format** - Use only opening tags or different delimiters
   - Risk: Breaks Mistral's native tool-calling format
   - Risk: May confuse base model's priors
   - Effort: 2-3 days to rewrite 1104 examples

2. **Use different Mistral model** - Try Mistral Large 2 or future releases
   - Risk: May have same tokenizer issue
   - Effort: Repeat Gate 0 for each candidate

3. **Switch to JSON-only format** - Avoid delimiters entirely
   - Risk: May not work with MLX tool-calling parser
   - Effort: 3-4 days to redesign format

**Cost-benefit:** All alternatives require >2 days work with high failure risk. Phase 27 model already achieves 100% accuracy.

---

## Evaluation Summary

| Gate | Status | Time Invested | Decision |
|------|--------|---------------|----------|
| Gate 0 | ❌ FAILED | 5 minutes | **STOP** |
| Gate 1 | — | — | Skipped |
| Gate 2 | — | — | Skipped |
| Gate 3 | — | — | Skipped |
| Gate 4 | — | — | Skipped |
| Gate 5 | — | — | Skipped |

**Total time saved:** ~4-7 hours (Gates 1-4) + 6-9 days (Gate 5) = **~7 days**

**Value of gated approach:** Gate 0 caught a fatal flaw in 5 minutes that would have been discovered after weeks of work in a linear approach.

---

## References

- **Implementation:** `scripts/gate0_tokenizer_check.py`
- **Raw output:** `logs/gate0-tokenizer.txt`
- **Spec:** `agent-os/specs/2026-02-16-devstral-evaluation/plan.md`
- **Phase 25 lesson:** `docs/diary/2026-02-15-phase25-7b-experiment-failed.md` (lines 90-100)
- **HuggingFace models:**
  - [mlx-community/Devstral-Small-2-24B-Instruct-2512-4bit](https://huggingface.co/mlx-community/Devstral-Small-2-24B-Instruct-2512-4bit)
  - [mistralai/Devstral-Small-2-24B-Instruct-2512](https://huggingface.co/mistralai/Devstral-Small-2-24B-Instruct-2512)

---

## Production Model (Unchanged)

**Continue using:** `fused_model_qwen3_phase27_5bit/`
- **Accuracy:** 100% (40/40 queries)
- **Speed:** 2.90s average generation
- **Size:** 20 GB (5-bit quantized)
- **Tool delimiters:** All single tokens ✅

No action required. Phase 27 model remains in production.
