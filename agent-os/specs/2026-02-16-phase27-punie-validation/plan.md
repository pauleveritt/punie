# Phase 27: Return to Punie - CLI Validation

## Context

Phase 27 validates that recent model work (Phases 22-26) still functions correctly in the Punie CLI before building server infrastructure (Phases 28-31). This is "Server Buildout Step 0" - ensuring the foundation works before scaling up.

**What prompted this:** Phases 22-26 added significant functionality:
- Code Mode (Python code generation)
- 14 typed tools (LSP + git + code quality)
- Field access training (92% accuracy)
- 100% validation accuracy on 40-query suite

**The problem:** All this work was validated against the fine-tuned model directly, not through the `punie ask` CLI command. We need to verify the full end-to-end pipeline works.

**Intended outcome:** A working `punie ask` command that loads the Phase 27 model and successfully executes representative queries across all tool categories.

## Scope

**What we're building:** A basic smoke test suite that verifies `punie ask` end-to-end functionality.

**Priorities (all selected):**
1. ✅ Model loads correctly (Phase 27 cleaned 5-bit model)
2. ✅ Tool calling works (2-3 representative tools)
3. ✅ ACP integration (permissions, logging, session behavior)
4. ✅ Performance baseline (compare to benchmark results)

**What we're NOT building:**
- Comprehensive 40-query validation (that's `scripts/validate_model.py`)
- Server infrastructure (that's Phase 28)
- New tools or features (just validating existing)

## Reference Implementations

### `punie ask` Command Architecture

**Entry point:** `src/punie/cli.py` lines 528-629
- Parses CLI args (prompt, model, workspace, debug, perf)
- Calls `_run_ask()` async function
- Creates agent with `create_local_agent("local", workspace)`
- Runs `agent.run(prompt, deps=ACPDeps(...))`
- Displays response

**Agent factory:** `src/punie/agent/factory.py`
- `create_local_agent()` returns (Agent, LocalClient)
- Uses `PUNIE_LOCAL_INSTRUCTIONS` (5 tools) for CLI mode
- Uses `PUNIE_INSTRUCTIONS` (14 tools) for ACP mode
- LocalClient provides filesystem + subprocess access

**Key distinction:**
- **Local mode** (CLI): 5 tools (read_file, write_file, run_command, terminal)
- **ACP mode** (PyCharm): 14 tools (LSP + git + code quality)

### Validation Patterns

**Comprehensive validation:** `scripts/validate_model.py` (1773 lines)
- 6-layer validation engine
- 40-query test suite
- **CRITICAL:** Always uses `format_prompt()` utility (60-point accuracy impact!)

**Simple validation:** `scripts/test_phase27_validation_fixed.py` (403 lines)
- String matching for tool detection
- Category-based scoring
- Soft (structural) vs strict (full compliance)

**Real tool testing:** `scripts/test_real_lsp_tools.py`, `scripts/test_real_git_tools.py`
- Integration tests with real LSP servers and git repos
- Async test patterns

## Implementation Plan

### Task 1: Save Spec Documentation

Create `agent-os/specs/2026-02-16-phase27-punie-validation/` with:
- **plan.md** - This full plan
- **shape.md** - Shaping notes (scope, decisions, context)
- **standards.md** - agent-verification + function-based-tests standards
- **references.md** - Pointers to punie ask implementation and validation patterns

### Task 2: Create Basic Smoke Test Script

Create `scripts/smoke_test_punie_ask.py` with 10 queries:

**5 Model/Tool Initialization Checks:**
1. Model loads without error
2. Agent created with correct configuration
3. Toolset registered (5 tools for local mode)
4. Simple prompt executes (no tool calls)
5. Tool-calling prompt works (calls at least one tool)

**5 Representative Tool Queries:**
6. File reading (read_file tool)
7. Command execution (run_command tool)
8. Terminal operations (create_terminal + get_output)
9. Code execution (execute_code tool)
10. Performance baseline (measure response time)

**Pattern to follow:**
```python
from punie.agent.prompt_utils import format_prompt  # CRITICAL!

async def test_model_loads():
    """Verify Phase 27 model loads in local mode."""
    agent, client = create_local_agent("local", workspace=tmp_dir)
    assert agent is not None
    assert isinstance(client, LocalClient)

async def test_simple_query():
    """Test non-tool query execution."""
    agent, client = create_local_agent("test", workspace=tmp_dir)  # TestModel
    deps = ACPDeps(client_conn=client, session_id="test")
    result = await agent.run("What is Python?", deps=deps)
    assert result.output
    assert len(result.output) > 0

async def test_tool_calling():
    """Test that tool infrastructure works."""
    # Uses TestModel to avoid actual tool execution
    # Verifies tool calls are formatted correctly
```

### Task 3: Run Smoke Test Against Phase 27 Model

Execute the smoke test:
```bash
uv run python scripts/smoke_test_punie_ask.py
```

Expected results:
- All 10 queries pass
- Model loads in <10s
- Response times match benchmark (2-5s steady-state)
- No exceptions or errors

### Task 4: Document Smoke Test Results

Create `docs/phase27-punie-validation-results.md` with:
- Smoke test results (10/10 pass expected)
- Performance metrics (load time, response times)
- Comparison to Phase 27 benchmark (2.33s avg)
- Any issues discovered and resolutions

## Verification

1. Use `astral:ty` skill to check types
2. Use `astral:ruff` skill to check and fix linting
3. Run `uv run pytest tests/` to verify all tests pass
4. Run smoke test: `uv run python scripts/smoke_test_punie_ask.py`
5. Verify 10/10 queries pass
6. Compare performance to Phase 27 benchmark (2.33s avg)

## Critical Files

**To create:**
- `agent-os/specs/2026-02-16-phase27-punie-validation/plan.md`
- `agent-os/specs/2026-02-16-phase27-punie-validation/shape.md`
- `agent-os/specs/2026-02-16-phase27-punie-validation/standards.md`
- `agent-os/specs/2026-02-16-phase27-punie-validation/references.md`
- `scripts/smoke_test_punie_ask.py`
- `docs/phase27-punie-validation-results.md`

**To reference:**
- `src/punie/cli.py` (ask command, lines 528-629)
- `src/punie/agent/factory.py` (create_local_agent, lines 267-307)
- `src/punie/agent/prompt_utils.py` (format_prompt - CRITICAL!)
- `scripts/validate_model.py` (validation patterns, 1773 lines)
- `scripts/test_phase27_validation_fixed.py` (simple validation, 403 lines)

## Success Criteria

- ✅ Smoke test script runs without errors
- ✅ 10/10 queries pass
- ✅ Model loads successfully in local mode
- ✅ Tool calling works for at least 2 representative tools
- ✅ Performance matches Phase 27 benchmark (±20%)
- ✅ Documentation created showing validation results
- ✅ Spec folder created with complete context

## Next Steps (Post-Phase 27)

After Phase 27 validation confirms CLI works:
- **Phase 28:** Add `punie server` with WebSocket
- **Phase 29:** Integrate Toad frontend
- **Phase 30:** Thin ACP router
- **Phase 31:** Multi-project support
