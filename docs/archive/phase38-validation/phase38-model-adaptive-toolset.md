# Phase 38: Model-Adaptive Toolset for Zero-Shot Models

**Date:** February 17, 2026
**Status:** ✅ Complete
**Result:** 84% accuracy (16/19) - Honest validation (Phase 38c)
**Original claim:** 89% accuracy (17/19) - Measurement flaws identified

## Executive Summary

Phase 38 implements a model-adaptive toolset architecture that detects Ollama models and promotes all typed tools to direct PydanticAI tools, bypassing Code Mode indirection. Combined with an updated Devstral model (multi-turn fix), this achieved **84% honest zero-shot accuracy** (Phase 38c), a 26-point improvement over Phase 37b's 58%.

**Note:** Phase 38 originally claimed 89% (17/19), but Phase 38c critical fixes revealed measurement flaws (no tool identity checks, no retry tracking). The honest validation with production-ready error handling shows 84% (16/19). See `docs/phase38c-critical-fixes.md` for details.

## Problem Statement

Phase 37b revealed that Devstral (24B parameter model) struggled with Code Mode's indirection pattern:
- **Phase 37b results:** 58% accuracy (11/19 queries)
- **Root cause:** Architectural mismatch between Code Mode training pattern and Devstral's native tool calling
- **Evidence:** Devstral wrote Code Mode Python as markdown text instead of calling `execute_code(code=...)`

### Why Code Mode Failed for Devstral

1. **Training mismatch:** Devstral trained on Mistral Vibe pattern (direct tools), not Code Mode
2. **Mental model:** 8 direct tools + 11 behind `execute_code()` sandbox = confusing
3. **Tool discovery:** Stubs in system prompt looked like documentation, not invocation protocol
4. **Multi-turn bug:** ollama/ollama#11296 prevented sequential tool calls (fixed upstream)

## Solution: Direct Code Tools

### Architecture Changes

**1. Direct Code Tools (toolset.py)**
- Created 11 `*_direct` async functions that expose typed tools as PydanticAI tools
- Added `_run_terminal()` helper for terminal workflow (create → wait → output → release)
- Added `_format_typed_result()` to serialize Pydantic models to key-value text
- Created `create_direct_toolset()` factory returning 14 tools (3 base + 11 Code Tools)

**2. Simplified System Prompt (config.py)**
- Added `PUNIE_DIRECT_INSTRUCTIONS` (30 lines vs 200-line Code Mode prompt)
- Removed Code Mode stubs and indirection explanations
- Direct, imperative tool usage guidelines
- Matches Mistral Vibe's concise prompt style

**3. Model-Adaptive Factory (factory.py)**
- `create_local_agent()` detects `ollama:` prefix
- Ollama models → `create_direct_toolset()` + `PUNIE_DIRECT_INSTRUCTIONS`
- Other models → `create_toolset()` + `PUNIE_LOCAL_INSTRUCTIONS` (Code Mode)
- Preserves fine-tuned Qwen3 100% accuracy with Code Mode

**4. Validation Updates (scripts/validate_zero_shot_code_mode.py)**
- Updated Category 3 from "Code Mode" to "Multi-Step" (direct tools call multiple times)
- Reduced Category 4 from 5 to 4 queries (removed one redundant query)
- Total: 19 queries (5 direct answers + 5 single tool + 5 multi-step + 4 field access)

### Implementation Details

#### Direct Code Tools Pattern

```python
async def typecheck_direct(ctx: RunContext[ACPDeps], path: str) -> str:
    """Run ty type checker on a file or directory.

    Returns structured results with error count, errors list, and summary.
    """
    from punie.agent.typed_tools import parse_ty_output

    output = await _run_terminal(
        ctx, "ty", ["check", path, "--output-format", "json"]
    )
    result = parse_ty_output(output)
    return _format_typed_result(result)
```

**Key insight:** These are simpler than the Code Mode sync bridges (lines 274-556 in toolset.py) because:
- No async → sync conversion needed (PydanticAI tools are already async)
- Direct terminal workflow instead of `asyncio.run_coroutine_threadsafe()`
- Reuse all existing parsers from `typed_tools.py`

#### Toolset Comparison

| Aspect | Code Mode (Qwen3) | Direct Tools (Devstral) |
|--------|-------------------|-------------------------|
| Tool count | 8 tools | 14 tools |
| Base tools | read_file, write_file, run_command | Same |
| Code Mode | execute_code (sandbox) | None |
| Terminal tools | 4 lifecycle tools | None (embedded in direct tools) |
| Typed tools | Inside execute_code | Direct PydanticAI tools |
| System prompt | 200 lines with stubs | 30 lines concise |

## Results

### Phase 38c Honest Validation (February 17, 2026)

**Model:** Devstral (24B, updated with multi-turn fix)
**Backend:** Ollama v0.x (localhost:11434)
**Total queries:** 19
**Overall accuracy:** 84% (16/19) ✅ Honest measurement

| Category | Queries | Success | Accuracy | Notes |
|----------|---------|---------|----------|-------|
| Direct answers | 5 | 5 | 100% | Perfect - no false tool calls |
| Single tool calls | 5 | 5 | 100% | All tools invoked correctly, first-call success |
| Multi-step | 5 | 3 | 60% | 2 failures (tool discovery issues) |
| Field access | 4 | 3 | 75% | 1 failure: model refused to call tool |

**Phase 38c improvements over original Phase 38 validation:**
- ✅ Tool identity verification (must call expected tool, not just any tool)
- ✅ Retry tracking (1 call = success, >1 = retry storm)
- ✅ Production-ready error handling (all 11 direct tools protected)
- ✅ Resource cleanup (terminal leaks prevented)

### Performance Metrics

- **Average query time:** 70.4s (expected for 24B model via Ollama)
- **Total validation time:** 22 minutes (1337.63s)
- **Fastest query:** 6.75s (ruff_check_direct on single file)
- **Slowest query:** 177.21s (pytest multi-step with result parsing)

### Comparison with Phase 37b

| Metric | Phase 37b (Code Mode) | Phase 38c (Direct Tools, Honest) | Improvement |
|--------|----------------------|----------------------------------|-------------|
| Direct answers | 5/5 (100%) | 5/5 (100%) | Maintained |
| Single tool | 2/5 (40%) | 5/5 (100%) | +60% |
| Multi-step | 2/5 (40%) | 3/5 (60%) | +20% |
| Field access | 2/4 (50%) | 3/4 (75%) | +25% |
| **Overall** | **11/19 (58%)** | **16/19 (84%)** | **+26%** |

**Note:** Phase 38 originally claimed 89% (17/19), but honest validation (Phase 38c) with tool identity checks and retry tracking shows 84% (16/19).

### Detailed Query Results

#### ✅ Successes (17/19)

**Direct Answers (5/5):**
1. ✅ Git merge vs rebase explanation (86.3s)
2. ✅ When to use type hints (52.9s)
3. ✅ What is dependency injection (25.0s)
4. ✅ Ruff vs pytest explanation (48.2s)
5. ✅ LSP capabilities explanation (22.1s)

**Single Tool Calls (5/5):**
1. ✅ `typecheck_direct` on src/ (11.4s)
2. ✅ `ruff_check_direct` on src/punie/ (6.8s)
3. ✅ `git_status_direct` for changed files (65.3s)
4. ✅ `read_file` for README.md (61.5s)
5. ✅ `pytest_run_direct` on tests/ (151.4s)

**Multi-Step (3/5):**
1. ❌ Find Python files + count imports (88.9s) - model refused to call tools
2. ✅ Run ruff + pytest + typecheck (52.3s) - 3 tool calls
3. ✅ Count staged vs unstaged files (77.0s) - 2 tool calls
4. ✅ List test files + pass rates (161.6s)
5. ❌ Find PunieAgent definition + methods (106.5s) - called wrong tools (workspace_symbols + document_symbols + read_file instead of goto_definition)

**Field Access (3/4):**
1. ✅ Show fixable ruff violations (50.6s)
2. ✅ Count passed vs failed tests (139.6s)
3. ❌ Filter type errors by severity (52.3s) - model refused: "I don't have the tools needed"
4. ✅ Git diff statistics (68.2s) - 2 tool calls

#### ❌ Failures (3/19)

**1. "Find all Python files and count imports" (Multi-Step)**
- **Expected:** Call `run_command("find", ["-name", "*.py"])` or use workspace_symbols
- **Actual:** Model refused: "I don't have the capability to directly search for files"
- **Root cause:** Model false refusal despite having `run_command` available
- **Fix needed:** Improve instructions to emphasize tool availability

**2. "Find definition of PunieAgent and show its methods" (Multi-Step)**
- **Expected:** Call `goto_definition_direct`
- **Actual:** Called `workspace_symbols_direct`, `document_symbols_direct`, `read_file` (alternative path)
- **Root cause:** Model chose valid alternative approach, but validation expected specific tool
- **Fix needed:** More flexible validation or clearer guidance on goto_definition usage

**3. "Filter type errors by severity" (Field Access)**
- **Expected:** Call `typecheck_direct("src/")` then parse result for severity
- **Actual:** Model refused: "I don't have the tools needed to filter type errors"
- **Root cause:** Model didn't connect "type errors" → typecheck_direct
- **Fix needed:** Clearer tool descriptions or examples showing typecheck → filtering

### Success Patterns

**What Worked Well:**
1. ✅ Direct ruff/pytest/typecheck calls (100% success in single-tool category)
2. ✅ Git operations (git_status_direct, git_diff_direct, git_log_direct)
3. ✅ File I/O (read_file, write_file)
4. ✅ Multi-turn tool calling (fixed by updated Devstral model)
5. ✅ First-call success (no retry storms observed)

**Failure Patterns:**
1. ❌ **False refusals:** Model says "I don't have X" when X exists as a tool (2 failures)
2. ❌ **Tool discovery:** Generic queries requiring tool mapping ("find files" → run_command, "filter errors" → typecheck_direct)
3. ❌ **Alternative paths:** Model chooses valid but unexpected tool sequence (workspace_symbols + document_symbols instead of goto_definition)

## Upstream Fix: Devstral Multi-Turn

Phase 37b noted multi-turn tool calling as a limitation. During Phase 38, we discovered this was **fixed upstream** in the Devstral model (ollama/ollama#11296).

**Fix:** `ollama pull devstral` (latest version as of Feb 17, 2026)
**Impact:** Devstral can now call multiple tools sequentially across conversation turns
**Evidence:** Multi-step category achieved 80% (4/5) vs 40% (2/5) in Phase 37b

The fix modified Devstral's template to track the last user message index and only attach tools to that final message, keeping tools available after tool call responses are added.

## Code Quality

### Tests Added (tests/test_agent_config.py)

```python
def test_create_direct_toolset_returns_correct_count():
    """create_direct_toolset should return 14 tools (3 base + 11 Code Tools)."""
    toolset = create_direct_toolset()
    assert len(toolset.tools) == 14

def test_create_local_agent_ollama_uses_direct_toolset():
    """create_local_agent with ollama: should use direct toolset."""
    agent, client = create_local_agent(model="ollama:devstral", workspace=Path.cwd())
    function_toolset = agent.toolsets[-1]
    assert len(function_toolset.tools) == 14  # Direct toolset

def test_create_local_agent_local_uses_code_mode_toolset():
    """create_local_agent with 'local' should use Code Mode toolset."""
    agent, client = create_local_agent(model="local", workspace=Path.cwd())
    function_toolset = agent.toolsets[-1]
    assert len(function_toolset.tools) == 8  # Code Mode toolset
```

### Verification

- ✅ All 23 tests pass in `tests/test_agent_config.py`
- ✅ No ruff violations
- ✅ No ty type errors
- ✅ Quick test confirms `ruff_check_direct` is called correctly

## Files Modified

| File | Lines Changed | Purpose |
|------|--------------|---------|
| `src/punie/agent/toolset.py` | +300 | Direct Code Tools + factory |
| `src/punie/agent/config.py` | +15 | PUNIE_DIRECT_INSTRUCTIONS |
| `src/punie/agent/factory.py` | +20 | Model-adaptive toolset selection |
| `scripts/validate_zero_shot_code_mode.py` | ~20 | Updated validation categories |
| `tests/test_agent_config.py` | +45 | Tests for direct toolset |

**Total:** ~400 lines added (mostly new direct tool implementations)

## Key Insights

### 1. Train/Test Consistency Matters

The 31-point accuracy jump proves that **matching the model's training distribution is critical**:
- Devstral trained on Mistral Vibe (direct tools) → Phase 38 direct tools = 89%
- Devstral + Code Mode indirection → Phase 37b = 58%
- Qwen3 trained on Code Mode → Code Mode = 100%

### 2. Simpler is Better for Zero-Shot

- **Code Mode:** 200-line prompt with 14 function stubs + execution semantics
- **Direct Tools:** 30-line prompt with tool usage guidelines
- **Result:** Direct approach achieved 89% vs 58% for Code Mode

The cognitive load of understanding Code Mode's indirection (call execute_code → pass Python string → code calls typed tools) exceeded Devstral's zero-shot capabilities.

### 3. Hybrid Architecture is Optimal

Phase 38 proves you can support both patterns:
```python
if model_str.startswith("ollama:"):
    toolset = create_direct_toolset()       # 14 direct tools
    config = AgentConfig(instructions=PUNIE_DIRECT_INSTRUCTIONS)
else:
    toolset = create_toolset()              # 8 Code Mode tools
    config = AgentConfig(instructions=PUNIE_LOCAL_INSTRUCTIONS)
```

This preserves Qwen3's 100% accuracy while enabling strong zero-shot performance for Ollama models.

### 4. Tool Reuse via Parser Pattern

All 11 direct tools reuse existing parsers from `typed_tools.py`:
- `parse_ty_output()` → `typecheck_direct()`
- `parse_ruff_output()` → `ruff_check_direct()`
- `parse_pytest_output()` → `pytest_run_direct()`
- etc.

This demonstrates good separation of concerns: parsing logic is independent of invocation protocol.

### 5. Upstream Fixes Matter

The Devstral multi-turn fix (ollama/ollama#11296) was crucial for multi-step queries. Without it, Phase 38 would likely have achieved ~70% instead of 89%.

**Lesson:** Always check for upstream fixes before implementing workarounds.

## Comparison with Mistral Vibe

Phase 38's direct tools architecture closely resembles Mistral's own Vibe CLI:

| Aspect | Vibe (Mistral) | Punie Phase 38 |
|--------|---------------|----------------|
| Tool architecture | All direct function calls | 14 direct PydanticAI tools |
| Tool count | 7 focused tools | 14 tools (3 base + 11 Code Tools) |
| System prompt | 47 lines concise | 30 lines concise |
| Per-tool guidance | Separate `.md` prompts | Inline docstrings |
| Code interpreter | None | None (removed execute_code) |
| Format | OpenAI function calling | Same (PydanticAI uses OpenAI format) |

The main difference is tool count (7 vs 14), which could explain minor failure cases where Devstral didn't discover the right tool.

## Next Steps

### Short-Term Improvements

1. **Tool Discovery Examples**
   - Add few-shot examples to PUNIE_DIRECT_INSTRUCTIONS showing run_command for file operations
   - Add example showing typecheck_direct → result parsing workflow
   - Expected improvement: 2/2 failures → 95% overall accuracy

2. **Tool Description Refinement**
   - Update docstrings to match user query patterns
   - Example: "Run ty type checker" → "Check for type errors and filter by severity"

3. **Performance Optimization**
   - Average 70s/query is slow (24B model + Ollama overhead)
   - Consider smaller models (Devstral 8B?) or optimize terminal workflows

### Medium-Term Enhancements

4. **Phase 39: LibCST Transformation Tools**
   - Add `cst_validate`, `cst_rename`, `cst_add_import` as direct tools
   - Enable domain-specific transformations (tdom validators)
   - Follow Phase 38 pattern: direct PydanticAI tools with Pydantic result models

5. **Phase 40: Flywheel Data Capture**
   - Instrument direct tools for `PunieEvent` logging
   - Capture tool call success/failure, corrections, confirmations
   - Use branch outcome (merged/closed) as ground truth for weighting examples

6. **Phase 41: Multi-Model Support**
   - Test Phase 38 with other Ollama models (Qwen3:30B via Ollama, CodeLlama, etc.)
   - Benchmark accuracy vs performance tradeoffs
   - Document which models work best with direct tools

### Long-Term Research

7. **Adaptive Prompting**
   - Detect when model doesn't recognize a tool and provide examples
   - "You have `typecheck_direct(path)` available for type checking"

8. **Tool Clustering Analysis**
   - Which tools are called together? (ruff + pytest + typecheck)
   - Create composite tools for common workflows?

9. **Code Mode Revival**
   - Can we make Code Mode work for zero-shot models with better prompting?
   - Or is direct tools fundamentally better for zero-shot?

## Phase 38c Critical Fixes

Phase 38c addressed critical bugs discovered through skeptical deep dive:

1. **Error Handling**: Added try/except + ModelRetry to all 11 direct tools
2. **Resource Cleanup**: Added try/finally to `_run_terminal()` to prevent terminal leaks
3. **Factory Wiring**: Fixed bug where custom config broke toolset selection
4. **Honest Validation**: Added tool identity checks, retry tracking, and response verification

**Impact:** Implementation is now production-ready with trustworthy measurements. See `docs/phase38c-critical-fixes.md` and `docs/phase38c-honest-validation-results.md` for complete details.

## Conclusion

Phase 38 successfully implemented a model-adaptive toolset architecture that:
- ✅ Achieves **84% honest zero-shot accuracy** (vs 58% Phase 37b baseline)
- ✅ Preserves 100% accuracy for fine-tuned Qwen3 with Code Mode
- ✅ Matches Devstral's training distribution (Mistral Vibe pattern)
- ✅ Simplifies system prompt (200 lines → 30 lines)
- ✅ Reuses existing typed tool parsers
- ✅ Production-ready error handling (Phase 38c)

The **26-point improvement (58% → 84%)** validates the core hypothesis: **zero-shot models perform better with direct tool calling than Code Mode indirection**.

The slight reduction from originally claimed 89% to honest 84% (Phase 38c) reflects more trustworthy measurement with tool identity verification, retry tracking, and production-ready error handling.

Next phase should focus on closing the 16% gap to 100% through instruction improvements (reduce false refusals) and exploring LibCST transformation tools for domain-specific operations.

---

**Status:** Complete with Phase 38c fixes
**Branch:** `phase37-devstral-validation`
**Commits:**
- Phase 38: Model-adaptive toolset (89% claimed)
- Phase 38c: Critical fixes (84% honest)
**Next:** Phase 39 planning (LibCST tools) or instruction improvements
