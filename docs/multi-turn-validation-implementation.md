# Multi-Turn Validation Implementation Summary

**Date:** 2026-02-16
**Status:** ✅ Complete and Verified

## Overview

Extended `scripts/validate_model.py` with multi-turn validation capability to test the model's ability to:
1. Generate a tool call in turn 1
2. Receive a fake `<tool_response>`
3. Either summarize the result OR make a second tool call in turn 2

This addresses the gap where **39% of training data is multi-turn** (391/993 examples), but no validation existed.

## What Changed

### Single File Modified
- `scripts/validate_model.py` (extended from 1188 to 1561 lines)

### Changes Summary

| Section | Lines Added | Description |
|---------|-------------|-------------|
| Imports | 1 | Added `format_prompt_with_history` |
| Dataclasses | 2 | Added `FakeToolResponse` and `MultiTurnQuerySpec` |
| Fake Responses | 7 | Static tool responses for reproducibility |
| Validation Functions | 2 | `validate_turn2_summary()` and `validate_turn2_tool_call()` |
| Queries | 12 | 8 summary + 4 cross-tool chaining queries |
| Generation Loop | 1 | `run_multi_turn_query()` orchestrator |
| Main Updates | 1 | Extended `run_validation()` to handle both types |
| Help Text | 1 | Updated `--category` to include "multi_turn" |

**Total:** 27 additions across 8 sections

## Query Distribution

| Category | Count | Description |
|----------|-------|-------------|
| Single-turn | 45 | Original validation queries |
| **Multi-turn (summary)** | **8** | Turn 1: tool call → Turn 2: summarize result |
| **Multi-turn (chaining)** | **4** | Turn 1: tool call → Turn 2: second tool call |
| **Total** | **57** | Complete validation suite |

## Fake Tool Responses

7 static, reproducible responses in Pydantic repr format:

1. **typecheck_errors** - 3 errors across 3 files
2. **ruff_violations** - 2 violations, 1 fixable
3. **pytest_failures** - 8 passed, 2 failed
4. **git_status_dirty** - 3 files (staged/unstaged/untracked)
5. **git_diff_changes** - 2 files, 15 additions, 8 deletions
6. **goto_def_found** - UserService at src/services/user.py:15
7. **find_refs_multiple** - 5 references to parse_ty_output

## Multi-Turn Generation Flow

```
Turn 1:  format_prompt(query, model_path)
         → generate()
         → validate layers 1-4

Inject:  Build fake <tool_response> as user message

Turn 2:  format_prompt_with_history(tool_response, model_path, history=[turn1_response])
         → generate()
         → validate turn 2 (summary OR tool call)
```

## Turn 2 Validation

### For Summaries (`turn2_is_tool_call=False`)
- **T2-Gate**: Response is NOT a tool call ✓
- **T2-Keywords**: Response contains ≥50% of expected keywords ✓

### For Cross-Tool Chaining (`turn2_is_tool_call=True`)
- **T2-Gate**: Response IS a tool call ✓
- **T2-Extract**: Code can be extracted ✓
- **T2-AST**: Code is syntactically valid ✓
- **T2-Identity**: Correct second tool is called ✓

## Dual Scoring

Both turns must pass for the query to pass:

- **Soft:** Turn 1 gate passes AND turn 2 gate passes
- **Strict:** Turn 1 passes layers 1-4 AND turn 2 passes all applicable layers

## Verification Results

```
✓ Script imports successfully
✓ Single-turn queries: 45
✓ Multi-turn queries: 12
✓ Fake responses: 7
✓ Total queries: 57
✓ All validation functions callable
✓ Help text includes "multi_turn" category
✓ 670 tests passed (1 pre-existing failure unrelated to changes)
✓ End-to-end test: PASS (Turn 1: tool call, Turn 2: summary)
```

## Bug Fixed During Implementation

**Issue:** Initial implementation used `temp=0.0` parameter for `generate()` calls, but MLX-LM doesn't support this parameter.

**Fix:** Removed temperature parameter entirely (MLX-LM uses default behavior, which is sufficient for validation).

**Affected Lines:** 3 generate() calls in `run_validation()` and `run_multi_turn_query()`

## Usage Examples

### Run all 57 queries (45 single + 12 multi)
```bash
uv run python scripts/validate_model.py fused_model_qwen3_phase27_5bit/
```

### Run only multi-turn queries (12 queries)
```bash
uv run python scripts/validate_model.py fused_model_qwen3_phase27_5bit/ --category multi_turn
```

### Run with verbose output and save results
```bash
uv run python scripts/validate_model.py fused_model_qwen3_phase27_5bit/ \
  --category multi_turn \
  --verbose \
  --output multi_turn_results.json
```

## Sample Output

```
[46/57] multi_turn | How many type errors are in src/?
  Turn 1: Soft: PASS  Strict: PASS  (2.34s)
    Layers: [gate:OK] [extract:OK] [ast:OK] [identity:OK]
  Turn 2: Soft: PASS  Strict: PASS  (1.87s)
    Layers: [t2-gate:OK] [t2-keywords:OK]

[53/57] multi_turn | Check types and if errors exist, show ruff violations too
  Turn 1: Soft: PASS  Strict: PASS  (2.12s)
    Layers: [gate:OK] [extract:OK] [ast:OK] [identity:OK]
  Turn 2: Soft: PASS  Strict: FAIL  (2.45s)
    Layers: [t2-gate:OK] [t2-extract:OK] [t2-ast:OK] [t2-identity:FAIL]
  Issues:
    - Turn 2: Missing tools: ruff_check (model summarized instead of chaining)
```

## Design Decisions

### Why extend validate_model.py instead of creating a new script?
Single unified suite = single score. No confusion about "which script to run."

### Why fake tool responses instead of real tools?
Reproducibility. Real tools depend on codebase state. Fake responses are static and test summarization ability, not tool functionality.

### Why 50% keyword threshold for strict summaries?
Balance tolerance with signal. The model might say "three errors" instead of "3 errors" - too strict = false negatives.

### Why only 12 multi-turn queries?
Each takes ~5s (2 generation passes). 12 queries = ~1 minute. Combined with 45 single-turn (~3 minutes), total runtime stays under 5 minutes.

## Critical Implementation Detail

**MUST use `format_prompt_with_history()` for turn 2** (CLAUDE.md standard). Tool responses in training data use `role: "user"` with `<tool_response>` tags - NOT a separate "tool" role.

## Next Steps

1. Run against current production model to establish baseline
2. Monitor multi-turn accuracy across model iterations
3. Consider expanding to 3+ turn sequences if needed
4. Track cross-tool chaining success rate separately

## References

- Training data: `data/phase27_merged/` (1104 examples, 39% multi-turn)
- Implementation plan: `/plan` message (this conversation)
- Validation script: `scripts/validate_model.py`
- Prompt utilities: `src/punie/agent/prompt_utils.py`
