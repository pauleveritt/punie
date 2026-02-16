# Phase 27.5 Audit Findings

**Date:** 2026-02-16
**Status:** COMPLETE ✅

## Executive Summary

**Claimed accuracy:** 78% (31/40)
**Honest accuracy:** **72% (29/40)**
**Difference:** -6 percentage points (inflated by broken validation)

**Verdict:** Phase 27.5 showed genuine progress in tool selection, but validation was broken and cross-tool workflows are completely broken (0/5).

## Critical Findings

### 1. Cross-Tool Workflows: Completely Broken (0%)

All 5 cross-tool queries failed:
- Model always calls ONLY the first or most obvious tool
- Never combines multiple tools into workflows
- Pattern: Sees "ruff AND pytest" → calls only ruff OR gives direct answer

**Root cause:** Training data has only 12/1104 examples (1.1%) combining tools from different families. 7 of 10 possible cross-family pairs have ZERO training examples.

### 2. Validation Script Was Meaningless

**Original script:**
```python
success = len(response) > 10  # Accepts ANY response!
```

**Fixed script:**
```python
success = all(f"{tool}(" in response for tool in expected_tools)
```

This inflated metrics by 6 percentage points (78% → 72%).

### 3. git_log Critical Bug

**Problem:** Command uses `git log --oneline` which doesn't include author/date

**Impact:**
- All commits have `author=None, date=None`
- 100% of git_log training examples are WRONG (claim these fields exist)
- Model code accessing `commit.author` gets silent `None`

**Fix options:**
1. Use `--format='%h|%an|%ad|%s'` to populate author/date
2. Remove author/date fields entirely (honest approach)

### 4. Training Data Quality Issues (~330/345 examples are junk)

**Junk patterns identified:**
- Vacuous direct answers: "Concept 14 is about..." (45 examples)
- Repetitive diversity: All 28 "Multi-step workflow N" examples identical
- grep negative examples bug: ALL searches use "TODO" regardless of query
- git command bug: `query.split()[1]` produces `run_command("git git")`

**Net impact:** Only ~8-13 of 345 new Phase 27.5 examples are genuinely useful.

## What IS Working ✅

1. **Direct answer discrimination: 100%** - Model knows when NOT to use tools
2. **Git tools: 100%** - git_status and git_diff work perfectly (git_log has bug but parser works)
3. **New LSP tools: 80%** - hover/document_symbols/workspace_symbols work
4. **Existing LSP tools: 80%** - goto_definition/find_references work

## Infrastructure Quality

**Solid:**
- Pydantic models well-designed ✅
- LSP protocol implementation correct ✅
- Git parsers work against real output ✅
- ty supports all LSP capabilities ✅
- Async-to-sync bridging pattern correct ✅

**Broken:**
- Cross-tool training examples ineffective ❌
- git_log command format wrong ❌
- Training data quality issues ❌
- Validation script was meaningless ❌

## Recommendations

### Immediate (Priority: HIGH)

1. **Fix git_log bug** - Use `--format='%h|%an|%ad|%s'` or remove author/date
2. **Fix cross-tool validation** - Use fixed script for all future validation
3. **Document honest accuracy** - Update MEMORY.md to show 72%

### Future Work (Priority: MEDIUM)

4. **Clean training data** - Delete 345 junk examples, write 30-50 good ones
5. **Add cross-tool training** - Dedicated examples showing multi-step workflows
6. **LSP integration tests** - Test against real ty server responses
7. **Fix train/valid split** - Deduplicate by query text before splitting

## Key Learnings

### 1. Validation Must Check Tools, Not Just Responses

Accepting any response >10 chars is meaningless. Must check if correct tools were called.

### 2. Cross-Tool Workflows Need Dedicated Training

Adding more single-tool examples doesn't teach multi-step workflows. Need explicit training showing:
- Call tool1()
- Access result fields
- Use those results to call tool2()
- Repeat

### 3. Real Testing Catches What Unit Tests Miss

- Unit tests with hand-crafted JSON → all passing
- Real git output → git_log bug discovered
- Real ty server → all capabilities confirmed

### 4. Training Data Quality > Quantity

345 new examples but ~330 are junk. Better to have 30 good examples than 345 poor ones.

### 5. Tool Selection vs Tool Usage

The model learned:
- ✅ When to use tools (discrimination)
- ✅ Which tool to use (single-tool selection)
- ❌ How to combine tools (cross-tool workflows)
- ⚠️ How to use result fields (60% accuracy)

## Honest Verdict

**Production readiness:** ⚠️ **70-75% for single-tool queries, 0% for multi-tool workflows**

Phase 27.5 delivered real progress: 72% honest accuracy is genuine improvement. The model can select the right tool most of the time and knows when to give direct answers. But it cannot combine tools into workflows, and training data needs significant cleanup.

**Next phase goal:** Achieve 75-80% honest accuracy with working cross-tool workflows

## Files From Audit

- `scripts/test_real_git_tools.py` - Git parser verification ✅
- `scripts/test_ty_capabilities.py` - LSP capability check ✅
- `scripts/test_phase27_validation_fixed.py` - Honest validation ✅
- `scripts/test_real_lsp_tools.py` - LSP integration tests (partial)
