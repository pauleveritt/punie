# Phase 22 Code Mode — Shaping Notes

## Problem Statement

**Multi-tool queries are slow.** Phase 21 requires N+2 model turns for N tool calls:
1. User → Model (generates first tool call)
2. Model → Tool → Model (generates second tool call)
3. Model → Tool → Model (generates final answer)

Example: "Find all test files and count assertions"
- Turn 1: Model generates `run_command("find", ["-name", "*test*.py"])`
- Turn 2: Tool returns file list → Model generates `read_file("test_foo.py")`
- Turn 3: Tool returns content → Model generates `read_file("test_bar.py")`
- Turn 4+: More reads...
- Final turn: Model counts assertions and answers

**Total latency:** ~20s (5 turns × ~4s/turn)

## Desired Outcome

**One turn with Python code:**
```python
files = run_command("find", args=["-name", "*test*.py"]).splitlines()
total = 0
for file in files:
    content = read_file(file)
    total += content.count("assert ")
print(f"Found {total} assertions")
```

**Total latency:** ~8s (2 turns: user → model → execute → answer)

## Scope

**In scope:**
- Add `execute_code` tool to existing toolset
- Generate Python function stubs from toolset for system prompt
- Implement Monty runner for sandboxed execution
- Convert existing 683 Phase 21 examples to code mode format
- Generate 150-200 new multi-step workflow examples
- Train Phase 22 model with LoRA + 5-bit quantization
- Benchmark latency improvement vs Phase 21

**Out of scope:**
- Changing XML format (we keep `<tool_call>` wrapper for mlx_lm.server compatibility)
- Modifying ACP protocol (external functions just call existing ACP tools)
- Adding new tools beyond the 3 core tools (read_file, write_file, run_command)
- Production deployment (this is training validation only)
- Error recovery strategies (if code fails, model sees error and can retry)

## Architecture Decision

**Considered 3 options:**

### Option A: XML wrapper (CHOSEN)
- Model generates: `<tool_call><function=execute_code><parameter=code>PYTHON_CODE</parameter></function></tool_call>`
- Pros: Reuses mlx_lm.server XML parser unchanged, minimal integration effort
- Cons: Extra XML wrapping overhead (minor)

### Option B: Direct Python (rejected)
- Model generates Python directly, no XML
- Pros: Cleaner format, less overhead
- Cons: Requires patching mlx_lm.server's parser, breaks compatibility with base Qwen3 tool format

### Option C: Hybrid (rejected)
- Model chooses between XML (single tool) and Python (multi-tool)
- Pros: Flexible
- Cons: Model must learn two formats, more complex training data, higher error rate

**Decision rationale:** Option A minimizes risk and integration complexity. We're validating latency improvements, not optimizing serialization overhead.

## Key Constraints

1. **Monty v0.0.3 limitations:**
   - No classes in sandbox (functions only)
   - Limited stdlib (no `os`, `pathlib`, `subprocess`)
   - External function registration required
   - start/resume pattern for async calls

2. **Training data quality:**
   - Generated Python code must be syntactically correct
   - Must validate with `ast.parse()` before adding to training set
   - Need diverse examples (loops, conditionals, error handling)

3. **Disk space:**
   - Float16 intermediate: ~57GB
   - 5-bit final: ~20GB
   - Currently available: ~72GB (tight but feasible if we delete float16 immediately)

4. **Backwards compatibility:**
   - Phase 22 model must still handle single-tool queries (Phase 21 capability)
   - Direct-answer queries remain unchanged (no code execution)
   - Maintain ~30% direct-answer ratio in training data

## Success Criteria

1. **Accuracy:**
   - Single-tool queries: 100% (5/5) — parity with Phase 21
   - Multi-step queries: 80%+ (4/5) — new capability

2. **Latency:**
   - Multi-step queries: 40-60% reduction vs Phase 21 (target: ~8s vs ~20s)
   - Single-tool queries: No regression (maintain ~6.6s)
   - Direct answers: No regression (maintain ~1.8s)

3. **Quality:**
   - Generated Python code passes `ast.parse()` (syntactically valid)
   - No type errors from ty checker
   - All external function calls use correct signatures

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Monty API instability (v0.0.3) | Medium | High | Fallback to restricted `exec()` sandbox |
| Training data quality (syntactic errors) | Medium | Medium | Validate all generated code with `ast.parse()` |
| Disk space exhaustion | Low | High | Delete float16 immediately after quantization |
| Model forgets single-tool capability | Low | High | Maintain 683 Phase 21 examples in training set |
| Latency improvement < 40% | Medium | Medium | Acceptable if accuracy is 80%+; iterate on training data |

## Timeline Estimate

- Tasks 1-4 (infrastructure): 4-6 hours
- Tasks 5-7 (training data): 3-4 hours
- Task 8 (training): 2-3 hours (mostly unattended)
- Task 9 (testing): 1-2 hours
- **Total:** ~10-15 hours

## Open Questions

1. **Should we add error handling examples to training data?**
   - Hypothesis: Model will learn to wrap risky calls in try/except
   - Decision: Add 10-15 error handling examples (file not found, command failed)

2. **How many multi-step examples are enough?**
   - Phase 21: 683 total (70% tool-calling)
   - Phase 22: 683 converted + 150-200 new = ~850 total
   - Decision: Start with 150 new, add more if accuracy < 80%

3. **Should we train on Monty constraints?**
   - Hypothesis: Model learns to avoid `os`, `pathlib`, etc.
   - Decision: Add system prompt constraint documentation, don't rely on training data

## References

- [Phase 21 results](../../../docs/diary/2026-02-14-phase21-xml-format-fix.md)
- [Monty documentation](https://github.com/pydantic/monty)
- [mlx_lm.server XML parser](https://github.com/ml-explore/mlx-examples/blob/main/llms/mlx_lm/server.py)
- [ACP tool lifecycle](../../standards/pydantic-agent-communication-protocol.md)
