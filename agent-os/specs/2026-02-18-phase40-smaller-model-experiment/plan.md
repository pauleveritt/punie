# Phase 40: Smaller Model Experiment (Qwen3-8B)

## Context

Phase 33b achieved 82.4% eval accuracy on the 30B MoE model (20 GB, 2-5s response). The core
hypothesis: with 26 domain tools handling reasoning, the model only needs to *route* — and an
8B dense model might suffice (6 GB, <1s). Phase 25 tried 7B and got 0%, but that was with
broken tokenization, only 6 tools, and 857 examples. This is the first clean test with
same-family tokenizer, 26 tools, and 1,282 examples.

**Branch:** `phase40-smaller-model`

**Scope:** Milestones 1-3 only (model selection + training + eval). No A/B usage test.

**Success:** Overall ≥80% on 27-prompt eval, with no catastrophic regression in any category.

---

## Task 1: Save Spec Documentation

Create `agent-os/specs/2026-02-18-phase40-smaller-model-experiment/` with:

- **plan.md** — This plan
- **shape.md** — Scope, decisions, Phase 25 lessons
- **standards.md** — agent-verification + function-based-tests
- **references.md** — Pointers to Phase 33b pipeline, Phase 25 failure analysis, Qwen3-8B model

## Task 2: Rename Branch

```bash
git branch -m phase34a-targeted-lora phase40-smaller-model
```

## Task 3: Preflight Tokenizer Check

**Create:** `scripts/phase40_tokenizer_check.py`

Verify Qwen3-8B tokenizer compatibility before investing training time:

1. `<tool_call>` (ID 151657), `</tool_call>` (ID 151658) are single tokens
2. `<tool_response>` (ID 151665), `</tool_response>` (ID 151666) are single tokens
3. `<|im_start|>` (ID 151644), `<|im_end|>` (ID 151645) are single tokens
4. `apply_chat_template()` produces ChatML identical to 30B model
5. Cross-check: encode a sample from `data/phase33_merged/train.jsonl` with both tokenizers,
   verify special token positions match

**Exit gate:** All checks pass, or STOP the experiment.

**Model:** `mlx-community/Qwen3-8B-4bit`

## Task 4: Create Training Pipeline Script

**Create:** `scripts/run_phase40_8b_pipeline.sh`

**Adapted from:** `scripts/run_phase33b_overnight.sh` (same 5-step structure)

Key differences from Phase 33b:

| Parameter | Phase 33b (30B) | Phase 40 (8B) |
|-----------|----------------|---------------|
| BASE_MODEL | `Qwen3-Coder-30B-A3B-Instruct-4bit` | `Qwen3-8B-4bit` |
| ADAPTER_PATH | `adapters_phase33b` | `adapters_phase40_8b` |
| FUSED_F16 | `fused_model_qwen3_phase33b_f16` | `fused_model_qwen3_phase40_8b_f16` |
| FUSED_5BIT | `fused_model_qwen3_phase33b_5bit` | `fused_model_qwen3_phase40_8b_5bit` |
| --num-layers | 8 (8/48 = 17%) | 16 (16/36 = 44%) |
| DATA | `data/phase33_merged` | `data/phase33_merged` (same) |

Dense needs more LoRA coverage (44%) vs MoE's 17% because there's no expert specialization.

**Estimated time:** ~25-40 min total (8B is ~4x faster than 30B).
**Disk:** ~22 GB temp (vs 77 GB for 30B). Final model ~6 GB.

## Task 5: Fix Eval Model ID Detection

**Edit:** `scripts/run_phase33_direct_eval.py` line 400

```python
# Current (hardcoded to phase33):
model_id = next((mid for mid in all_ids if "phase33" in mid), all_ids[0] if all_ids else "default")

# Fix (use first available — we control the server):
model_id = all_ids[0] if all_ids else args.model
```

## Task 6: Run Pipeline and Document Results

1. Run preflight: `uv run python scripts/phase40_tokenizer_check.py`
2. Run pipeline: `bash scripts/run_phase40_8b_pipeline.sh`
3. Create `docs/research/phase40-8b-results.md` with per-category eval breakdown

---

## Pre-Registered Success Criteria

| Category | Phase 33b Baseline | Phase 40 Target |
|----------|-------------------|-----------------|
| text_tools | 100% | ≥95% |
| validation | 100% | ≥95% |
| git | 100% | ≥90% |
| cst | 100% | ≥90% |
| lsp | 90% | ≥80% |
| domain | 60% | ≥60% |
| multi_tool | 35% | ≥35% |
| **Overall** | **82.4%** | **≥80%** |

---

## Verification

1. Use `astral:ruff` skill to check new Python scripts
2. Use `astral:ty` skill to check types
3. Run `uv run pytest tests/` to verify no regressions
4. Preflight tokenizer check passes before training
5. 27-prompt eval produces per-category scores
6. Compare category-by-category against Phase 33b baseline

## Status

Created 2026-02-18. Tasks 1-5 implemented. Tasks 6 (pipeline run + results) pending.
