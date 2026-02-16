# Phase 27 Punie Validation - Shaping Notes

## Problem Statement

Phases 22-26 validated the fine-tuned model directly using test scripts, but never verified that the full `punie ask` CLI command works end-to-end. Before building server infrastructure (Phases 28-31), we need confidence that the foundation is solid.

## Key Questions

**Q: Why validate through CLI instead of direct model tests?**
A: Direct model tests skip critical infrastructure: agent factory, local client, toolset registration, ACP integration. CLI validation catches integration bugs.

**Q: Why only 10 queries instead of the full 40-query suite?**
A: This is a smoke test, not comprehensive validation. We want fast feedback that the pipeline works. The 40-query suite (`scripts/validate_model.py`) already validates model behavior thoroughly.

**Q: What's the difference between local mode (CLI) and ACP mode (PyCharm)?**
A: Local mode has 5 basic tools (read_file, write_file, run_command, terminal, execute_code). ACP mode has 14 tools (LSP + git + code quality). This validation focuses on local mode.

**Q: Should we test tool execution or just tool calling?**
A: Both. Model initialization checks verify the plumbing (agent factory, toolset). Tool queries verify actual execution (file reading, command running).

## Scope Decisions

### In Scope
- ✅ Model loading in local mode
- ✅ Agent factory configuration
- ✅ Basic tool execution (read_file, run_command, terminal)
- ✅ Performance baseline (load time, response time)
- ✅ Error handling (model not found, tool failures)

### Out of Scope
- ❌ Comprehensive 40-query validation (already done by `validate_model.py`)
- ❌ ACP mode tools (LSP, git) - those need PyCharm running
- ❌ Server infrastructure (Phase 28)
- ❌ Multi-project support (Phase 31)
- ❌ Permission system deep dive (that's for ACP validation)

### Edge Cases
- Model path resolution (absolute vs relative)
- Workspace directory handling (temp dirs, non-existent paths)
- Tool failures (command errors, file not found)
- Async cleanup (agent shutdown, client teardown)

## Architecture Context

### Agent Creation Flow
```
punie ask "query"
  → cli.py:ask_command()
  → _run_ask()
  → create_local_agent("local", workspace)
  → factory.py:create_local_agent()
  → (Agent, LocalClient) with 5 tools
  → agent.run(prompt, deps=ACPDeps(...))
```

### Tool Registration
```
create_local_agent()
  → agent_model = PUNIE_LOCAL_INSTRUCTIONS
  → tools = [read_file, write_file, run_command, terminal, execute_code]
  → LocalClient provides filesystem + subprocess
```

### Critical Pattern: format_prompt()
```python
# CORRECT (60-point accuracy boost!)
from punie.agent.prompt_utils import format_prompt
prompt = format_prompt("Find all classes", model_path)

# WRONG (causes train/test mismatch)
prompt = f"User: {query}\nAssistant:"
```

## Success Metrics

### Quantitative
- **Pass rate:** 10/10 queries (100%)
- **Load time:** <10s (cold start)
- **Response time:** 2-5s (steady-state, matches Phase 27 benchmark)
- **Memory usage:** <20 GB (Phase 27 model is 19.55 GB)

### Qualitative
- No exceptions or errors during execution
- Tool calls formatted correctly (Python code, not XML/JSON)
- Responses are coherent and complete
- Async cleanup succeeds (no hanging tasks)

## Risk Assessment

### High Risk
- **Model path resolution:** Different environments may have different model locations
  - Mitigation: Use relative paths from project root
- **Async cleanup:** Incomplete teardown can leave hanging tasks
  - Mitigation: Use try/finally blocks, explicit cleanup

### Medium Risk
- **Tool execution failures:** Commands may fail in test environments
  - Mitigation: Use safe commands (ls, echo), temp directories
- **Performance variance:** M1/M2 vs x86 may show different timings
  - Mitigation: Use ±20% tolerance for benchmarks

### Low Risk
- **Model compatibility:** Phase 27 model should work unchanged
- **Test isolation:** Each query uses fresh agent instance

## Timeline

- **Task 1:** Spec documentation (30 min) ← Current
- **Task 2:** Smoke test script (1 hour)
- **Task 3:** Run validation (15 min)
- **Task 4:** Document results (30 min)

**Total estimated:** 2-3 hours

## Dependencies

### Required Files
- `fused_model_qwen3_phase27_5bit/` - Phase 27 model (19.55 GB)
- `src/punie/cli.py` - CLI entry point
- `src/punie/agent/factory.py` - Agent creation
- `src/punie/agent/prompt_utils.py` - Prompt formatting

### Required Tools
- `uv` for running scripts
- `pytest` for test framework (optional, could use direct async)
- `astral:ruff` and `astral:ty` for quality checks

## Open Questions

1. **Should we test with TestModel or Phase 27 model?**
   - TestModel: Fast, predictable, no real LLM
   - Phase 27: Real behavior, but slower
   - Decision: Use both - TestModel for initialization, Phase 27 for tool execution

2. **How to handle model not found errors?**
   - Skip gracefully with clear message
   - Or fail loudly to catch CI issues
   - Decision: Fail loudly - we need the model present

3. **Should we add this to CI?**
   - Pros: Catches regressions
   - Cons: CI may not have 20GB model, runs are slow
   - Decision: Manual only for now, revisit in Phase 28

## Future Work

After Phase 27 validation succeeds:
- Phase 28: Add `punie server` command with WebSocket
- Phase 29: Integrate Toad frontend
- Phase 30: Thin ACP router for multi-client
- Phase 31: Multi-project workspace support

This validation is the foundation that makes all future phases possible.
