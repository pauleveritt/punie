# Phase 27 Augmented Model: Validation Analysis

**Date:** 2026-02-16
**Model:** `fused_model_qwen3_phase27_augmented_5bit/`
**Validation Suite:** 57 queries (45 single-turn + 12 multi-turn)
**Overall Strict Accuracy:** 46% (26/57) ❌ **FAILED** (Target: ≥80%)

---

## Executive Summary

The Phase 27 augmented model shows **significant regression** from the Phase 27 production baseline (100% on 40 queries). The new 57-query validation suite (including 12 multi-turn queries) reveals **critical failures** in:

1. **Git tools** - 0% accuracy (all queries give direct answers instead of tool calls)
2. **Some LSP tools** - document_symbols, workspace_symbols broken
3. **Cross-tool chaining** - 0/4 multi-turn cross-tool queries pass
4. **Field access** - Only 30% strict accuracy (missing field accesses)

**Verdict:** ❌ **NOT PRODUCTION READY** - Do not deploy this model

---

## Overall Results

| Metric | Result | Target | Status |
|--------|--------|--------|--------|
| Strict Accuracy | 26/57 (46%) | ≥80% | ❌ FAIL |
| Soft Accuracy | 40/57 (70%) | - | - |
| Average Generation Time | ~2.5s | - | ✅ OK |

---

## Category-Level Results

| Category | Queries | Soft | Strict | Target | Status | Gap |
|----------|---------|------|--------|--------|--------|-----|
| direct_answers | 5 | 5/5 (100%) | 5/5 (100%) | 100% | ✅ PASS | - |
| edge_cases | 5 | 4/5 (80%) | 4/5 (80%) | 80% | ✅ PASS | - |
| tool_identity | 5 | 4/5 (80%) | 4/5 (80%) | 80% | ✅ PASS | - |
| **single_tool** | 10 | 5/10 (50%) | **3/10 (30%)** | 90% | ❌ FAIL | **-60%** |
| **field_access** | 10 | 8/10 (80%) | **3/10 (30%)** | 80% | ❌ FAIL | **-50%** |
| **cross_tool** | 10 | 7/10 (70%) | **2/10 (20%)** | 60% | ❌ FAIL | **-40%** |
| **multi_turn** | 12 | 7/12 (58%) | **5/12 (42%)** | 70% | ❌ FAIL | **-28%** |

### Key Findings

✅ **What Works:**
- Direct answers: 100% (concept explanations, comparisons)
- Tool discrimination: Model correctly chooses between tools vs answers
- Basic tool calling: typecheck, ruff_check, pytest_run work well

❌ **What's Broken:**
- **Git tools completely broken** (0% accuracy)
- **Some LSP tools broken** (document_symbols, workspace_symbols)
- **Cross-tool workflows weak** (only 20%)
- **Multi-turn cross-tool chaining fails** (0/4)

---

## Detailed Failure Analysis

### 1. Git Tools - Complete Failure (0/8 queries, 0% accuracy)

**Affected Queries:**
- #6: "Check types in src/punie/agent/" → Direct answer (expected: typecheck)
- #14: "Show the current git status" → Direct answer (expected: git_status)
- #15: "Show the last 5 commits" → Direct answer (expected: git_log)
- #19: "Check git working tree for uncommitted changes" → Direct answer (expected: git_status)
- #33: "Check git status and diff the staged files" → Direct answer (expected: git_status)
- #38: "Check git status and read the content of modified files" → Direct answer (expected: git_status)
- #49: Multi-turn "Show the current git status" → Direct answer (expected: git_status)
- #57: Multi-turn "Check git status and diff the staged files" → Direct answer (expected: git_status)

**Pattern:** Model ALWAYS gives direct answer for git_status, git_log queries
**Root Cause Hypothesis:** Insufficient git tool training examples OR conflicting training data

### 2. LSP Tools - Partial Failure (3/8 queries, 38% accuracy)

**Broken:**
- #12: "List all symbols in src/punie/agent/typed_tools.py" → Direct answer (expected: document_symbols)
- #13: "Search the workspace for classes named GitStatusResult" → Direct answer (expected: workspace_symbols)
- #27: "Count all symbols in src/punie/agent/config.py" → Direct answer (expected: document_symbols)

**Working:**
- #9: "Where is TypeCheckResult defined?" → goto_definition ✓
- #11: "Show hover info for BaseModel" → hover ✓

**Pattern:** New Phase 27 tools (document_symbols, workspace_symbols) fail; existing tools (goto_definition, hover) work
**Root Cause Hypothesis:** New tools need more training examples with diverse query phrasing

### 3. Cross-Tool Workflows - Severe Weakness (2/10 queries, 20% accuracy)

**Working:**
- #31: "Run full quality check: ruff, typecheck, and pytest" ✓
- #35: "Run tests and if any fail, show the ruff violations" ✓

**Broken:**
- #32: "Find the definition of UserService and then read that file" → Missing read_file
- #34: "Find all references to TypeCheckResult and show hover info" → Missing find_references, hover
- #36: "Check types and show errors only in files with ruff violations" → Missing typecheck
- #37: "Get document symbols for config.py and hover on the first class" → Missing document_symbols, hover
- #39: "Run ruff check and write a summary report to report.txt" → Missing write_file

**Pattern:** Sequential tool chaining fails (tool1 → then tool2); parallel tool calling works (tool1 + tool2 + tool3)
**Root Cause Hypothesis:** Training data emphasizes parallel tool calling, not sequential workflows

### 4. Multi-Turn - Cross-Tool Chaining Complete Failure (0/4 queries, 0% accuracy)

**All 4 cross-tool chaining queries failed:**
- #54: "Check types and if errors exist, show ruff violations too" → Turn 2: Direct answer (expected: ruff_check)
- #55: "Find where UserService is defined and read that file" → Turn 2: Direct answer (expected: read_file)
- #56: "Run tests. If any fail, check types in those files" → Turn 2: Direct answer (expected: typecheck)
- #57: "Check git status and diff the staged files" → Turn 1: FAIL (git_status), Turn 2: Direct answer

**Pattern:** Turn 1 works (makes first tool call), Turn 2 fails (summarizes instead of making second tool call)
**Root Cause Hypothesis:** No multi-turn cross-tool chaining examples in training data

**Multi-Turn Summary Queries: 5/8 (63% strict accuracy)**
- Working: typecheck, ruff_check, git_diff, goto_definition, find_references
- Broken: pytest (keyword mismatch), git_status (turn 1 fails)

---

## Root Cause Analysis

### Hypothesis 1: Git Tools Never Trained
**Evidence:**
- 0% accuracy on git_status, git_log queries
- Consistent pattern: always direct answer
- Even simple queries like "Show the current git status" fail

**Check:** Audit `data/phase27_augmented/train.jsonl` for git tool examples

### Hypothesis 2: New LSP Tools Undertrained
**Evidence:**
- document_symbols, workspace_symbols fail (30% accuracy)
- goto_definition, hover work (100% accuracy on working queries)

**Check:** Count document_symbols/workspace_symbols examples vs goto_definition/hover

### Hypothesis 3: No Multi-Turn Cross-Tool Chaining Examples
**Evidence:**
- 0/4 cross-tool chaining queries pass
- All turn 1 calls work, all turn 2 calls fail
- Model defaults to summarizing instead of chaining

**Check:** Search training data for multi-turn tool → tool patterns

### Hypothesis 4: Sequential Tool Workflow Underrepresented
**Evidence:**
- Parallel tool calling works: "Run ruff, typecheck, and pytest" ✓
- Sequential fails: "Find definition and then read that file" ✗

**Check:** Compare "tool1 AND tool2" vs "tool1 THEN tool2" example counts

---

## Comparison with Phase 27 Production Baseline

| Model | Queries | Strict Accuracy | Notes |
|-------|---------|-----------------|-------|
| Phase 27 Production | 40 | 40/40 (100%) | Original validation suite (no multi-turn) |
| Phase 27 Augmented | 57 | 26/57 (46%) | Added 12 multi-turn + 5 new single-turn queries |

**Note:** Direct comparison not possible due to different query sets. However, the augmented model fails on queries that should work (git tools, LSP tools).

---

## Recommendations

### Immediate Actions

1. **Do NOT deploy Phase 27 augmented model** - 46% accuracy is unacceptable
2. **Audit training data** - Check for git tool examples, multi-turn patterns
3. **Roll back to Phase 27 production** - If it still exists

### Data Generation Priorities (Phase 28)

Based on failure analysis, prioritize training data generation in this order:

#### Priority 1: Git Tools (Critical) 🔴
- Generate 50+ examples for git_status, git_diff, git_log
- Cover diverse query phrasings:
  - "Show the current git status"
  - "Check git working tree"
  - "What files are modified?"
  - "Show uncommitted changes"

#### Priority 2: Multi-Turn Cross-Tool Chaining (Critical) 🔴
- Generate 50+ multi-turn examples with tool → tool pattern
- Format: user → assistant <tool_call> → user <tool_response> → assistant <tool_call>
- Examples:
  - typecheck → ruff_check (if errors, check lint)
  - goto_definition → read_file (find → read)
  - pytest → typecheck (if failures, check types)

#### Priority 3: Sequential Tool Workflows (High) 🟡
- Generate 30+ single-turn examples with "then" phrasing
- Examples:
  - "Find X and then read it"
  - "Check Y and then show Z"

#### Priority 4: New LSP Tools (Medium) 🟢
- Generate 20+ examples for document_symbols, workspace_symbols
- Vary query phrasings

### Validation Before Training

1. **Audit existing data:**
   ```bash
   grep -c "git_status" data/phase27_augmented/train.jsonl
   grep -c "document_symbols" data/phase27_augmented/train.jsonl
   grep -c "<tool_response>" data/phase27_augmented/train.jsonl | # Multi-turn count
   ```

2. **Generate gap-filling data** based on audit results

3. **Run validation on Phase 27 production** (if available) to establish true baseline

---

## Next Steps

### Option A: Fix Phase 27 Augmented
1. Audit `data/phase27_augmented/` for missing patterns
2. Generate gap-filling training data (git, multi-turn, sequential)
3. Retrain from Phase 26 with fixed dataset
4. Re-validate with 57-query suite

### Option B: Start Fresh with Phase 28
1. Use validation results to guide data generation from scratch
2. Target: 57/57 queries (100% strict accuracy)
3. Focus on weak areas: git, multi-turn, sequential workflows

### Option C: Incremental Fix
1. Generate ONLY git tool examples (50)
2. Quick retrain with Phase 27 augmented + git examples
3. Validate - if git fixes, proceed to multi-turn
4. Iterate until 80% threshold met

**Recommendation:** **Option C (Incremental Fix)** - Fastest path to 80% threshold

---

## Files Generated

- `validation_phase27_baseline.json` - Full validation results (57 queries)
- `validation_phase27_baseline.log` - Human-readable output
- This analysis document

---

## Validation Suite Performance

The new 57-query validation suite successfully:
- ✅ Identified critical git tool failures
- ✅ Caught LSP tool regression
- ✅ Revealed multi-turn cross-tool chaining gap
- ✅ Discriminated between working and broken patterns
- ✅ Provided actionable data for next training phase

**Verdict:** Validation suite is working as designed. Multi-turn queries are valuable additions.
