# Phase 33 Eval Results

**Date:** 2026-02-18
**Model:** `fused_model_qwen3_phase33_5bit` (20 GB, 5-bit quantized Qwen3-30B-A3B)
**Overall:** ✅ **81.9%** (target ≥80%)
**Training dataset:** 1282 examples (1126 Phase 28 + 156 Phase 32 domain tools)
**Training:** 800 iters, 30 min, val loss 0.277

## Category Breakdown

| Category | Score | Notes |
|----------|-------|-------|
| domain | 100% (6/6) | All 9 domain validators working |
| git | 100% (3/3) | git_status, git_diff, git_log |
| lsp | 100% (5/5) | goto_def, find_refs, hover, document_symbols, workspace_symbols |
| text_tools | 70% (2/3) | write_file fails (uses Python open()) |
| validation | 70% (2/3) | typecheck confused with ruff_check |
| cst | 36.7% (1/3) | cst-01 server regression; cst-03 wrong tool |
| multi_tool | 35% (0/1) | Only 1 of 4 expected tools in single call |

## Known Weaknesses (for Phase 34 training)

1. **write_file**: model uses Python `open()` builtin instead of write_file tool
2. **typecheck vs ruff_check**: confused for "type checking" queries
3. **cst_add_import**: confused with cst_rename_direct for import-adding queries
4. **multi-tool**: generates only 1 tool call even when asked to chain 4 operations
5. **cst-01 sensitivity**: with no server `--max-tokens` cap, extended thinking leads to
   XML-format responses instead of native tool_calls for some CST queries

## Eval Infrastructure Lessons

See `MEMORY.md` Phase 33 Eval Notes section for full details.

Key: use short training-matching system prompt, OR-logic for single-tool scoring,
include function name in code body for direct tool calls, per-request max_tokens override.
