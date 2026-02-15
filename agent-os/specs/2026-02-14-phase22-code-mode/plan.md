# Phase 22: Code Mode — Python Tool Calls

## Context

Phase 21 achieved 100% tool-calling accuracy (5/5) with ~6.6s per tool query. However, multi-tool queries require N+2 model turns (user → model → execute → model → execute → ... → model → answer). Code Mode collapses this: the model generates a Python script that calls multiple tools in ONE turn, executed in Monty (Pydantic's Rust-based sandbox).

**Primary success metric:** Multi-step latency reduction (e.g., "Find all tests and count functions" drops from 5 turns/~20s to 2 turns/~8s).

**Architecture decision:** Option A — XML wrapper. The model generates `<tool_call><function=execute_code><parameter=code>...</parameter></function></tool_call>`. This reuses the existing mlx_lm.server XML parser unchanged. Punie extracts the code string and runs it in Monty.

## Task 1: Save Spec Documentation

Create `agent-os/specs/2026-02-14-phase22-code-mode/` with:
- `plan.md` — This plan
- `shape.md` — Shaping notes (scope, decisions, architecture choice)
- `standards.md` — agent-verification, frozen-dataclass-services, function-based-tests, fakes-over-mocks
- `references.md` — Pointers to toolset.py, convert_to_xml_format.py, Monty docs, PR #4153

## Task 2: Generate Typed Stubs from Toolset

Create `src/punie/agent/stubs.py` — auto-generates Python function stubs from the existing toolset using `inspect.signature`.

**What it does:**
- Reads the 3 core tools from `toolset.py`: `read_file`, `write_file`, `run_command`
- Generates stub strings like:
  ```python
  def read_file(path: str) -> str:
      """Read contents of a text file from the IDE workspace."""
      ...

  def run_command(command: str, args: list[str] | None = None, cwd: str | None = None) -> str:
      """Run a shell command in the IDE terminal."""
      ...
  ```
- Strips `ctx: RunContext[ACPDeps]` parameter (model shouldn't see it)
- Output: A string that gets injected into the system prompt so the model knows what functions are available

**Key files:**
- Read: `src/punie/agent/toolset.py` (source signatures)
- Create: `src/punie/agent/stubs.py`
- Test: `tests/test_stubs.py`

## Task 3: Implement Monty Runner

Create `src/punie/agent/monty_runner.py` — executes model-generated Python code in Monty sandbox with registered external functions.

**What it does:**
- Takes a code string from the model's `execute_code` tool call
- Registers external functions (`read_file`, `write_file`, `run_command`) that bridge back to ACP
- Uses Monty's `start()` / `resume()` pattern for async external calls
- Returns the execution result (stdout, return value, or error)

**Monty constraints (v0.0.3):**
- No classes allowed in sandbox
- Limited stdlib (no `os`, `pathlib`, `subprocess`)
- External functions must be registered before execution
- start/resume pattern for async operations
- Embeds ty type checker (bonus: validates model-generated code)

**Key files:**
- Create: `src/punie/agent/monty_runner.py`
- Read: Monty docs/source for API reference
- Test: `tests/test_monty_runner.py`
- Dependency: `uv add monty-python` (or whatever the package name is)

**Risk:** Monty is v0.0.3 and may have API instability. If Monty integration proves too fragile, fallback to a simpler `exec()` sandbox with restricted builtins (less safe but functional for training validation).

## Task 4: Add execute_code Tool to Toolset

Add `execute_code` as a new tool in `src/punie/agent/toolset.py`.

**What it does:**
- New async function: `execute_code(ctx, code: str) -> str`
- Calls `monty_runner.run(code, external_functions)` with ACP-bridged functions
- Returns execution output to the model
- Reports tool lifecycle to IDE (start/progress tracking, same pattern as existing tools)

**Key files:**
- Edit: `src/punie/agent/toolset.py` — add `execute_code` function
- Edit: `src/punie/agent/config.py` — update PUNIE_INSTRUCTIONS to mention code mode
- Edit: `create_toolset()` — add `execute_code` to the tool list
- Test: `tests/test_toolset.py` (or existing toolset tests)

## Task 5: Convert Existing Training Data to Code Mode Format

Create `scripts/convert_to_code_format.py` — converts the 683 Phase 21 XML examples to Code Mode format.

**What it does:**
- Reads existing XML tool calls from `data/phase8_xml_format/`
- Converts single-tool XML calls to `execute_code(code="...")` XML calls
- Example conversion:
  ```
  # Before (Phase 21):
  <tool_call><function=run_command><parameter=command>grep</parameter><parameter=args>["-r", "class.*View", "."]</parameter></function></tool_call>

  # After (Phase 22):
  <tool_call><function=execute_code><parameter=code>
  result = run_command("grep", args=["-r", "class.*View", "."])
  print(result)
  </parameter></function></tool_call>
  ```
- Direct-answer examples remain unchanged (no tool call needed)
- Tool responses converted to code execution results

**Key files:**
- Read: `scripts/convert_to_xml_format.py` (pattern to follow)
- Read: `data/phase8_xml_format/` (source data)
- Create: `scripts/convert_to_code_format.py`
- Output: `data/phase22_code_format/`

## Task 6: Generate Multi-Step Workflow Examples

Create `scripts/generate_code_workflows.py` — generates 150-200 NEW training examples that demonstrate multi-step Python workflows.

**What it does:**
- Generates examples where the model writes Python code with loops, conditionals, and multiple tool calls
- Categories:
  - **Multi-file operations** (30): "Read all Python files and find imports" → `for f in run_command("find", ["-name", "*.py"]): content = read_file(f); ...`
  - **Search-and-analyze** (30): "Find all test files and count assertions" → loop + grep + count
  - **Conditional workflows** (25): "If config exists, read it; otherwise create default" → if/else
  - **Aggregation** (25): "Count lines of code per directory" → loop + accumulate
  - **Transform** (20): "Rename all snake_case functions to camelCase in file X" → read + transform + write
  - **Direct answers** (50): Concept/comparison questions (maintain ~30% direct-answer ratio)

**Key files:**
- Read: `scripts/generate_domain_examples.py` (pattern to follow)
- Create: `scripts/generate_code_workflows.py`
- Output: merged into `data/phase22_code_format/`

## Task 7: Merge and Split Training Data

Combine Task 5 (converted) + Task 6 (new workflows) into final training splits.

**What it does:**
- Merge converted single-tool examples with new multi-step examples
- Target: ~850 total examples
- Split: 80% train / 10% valid / 10% test
- Verify distribution: ~70% tool-calling / ~30% direct answers
- Output: `data/phase22_code_format/{train,valid,test}.jsonl`

**Key files:**
- Edit or create: `scripts/merge_training_data.py`
- Output: `data/phase22_code_format/`

## Task 8: Train Phase 22 Model

Train with LoRA, fuse, and quantize to 5-bit.

**Pipeline (proven from Phase 21):**
1. LoRA training: 500 iters, batch_size 1, lr 1e-4, 8 layers
2. Base model: `mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit`
3. Fuse to float16: `mlx_lm.fuse --dequantize`
4. Quantize to 5-bit: `mlx_lm.convert --q-bits 5`

**Key files:**
- Create: `scripts/train_phase22.sh`
- Output: `fused_model_qwen3_phase22_code_5bit/` (~20GB)

## Task 9: Test and Benchmark vs Phase 21

Validate accuracy and measure latency improvement.

**Tests:**
1. **Single-tool accuracy** (5 queries): Same Phase 21 discrimination test
2. **Multi-step accuracy** (5 queries): New multi-tool queries
3. **Latency comparison**: Phase 21 (N+2 turns) vs Phase 22 (1-2 turns) for multi-step queries

**Expected results:**
- Single-tool: 100% (5/5) — parity with Phase 21
- Multi-step: 80%+ (new capability)
- Latency: 40-60% reduction on multi-step queries

**Key files:**
- Create: `scripts/test_phase22_model.py`
- Create: `scripts/benchmark_phase22_vs_21.py`

## Verification

1. Use `astral:ty` skill to check types on all new/modified files
2. Use `astral:ruff` skill to check and fix linting
3. Run `uv run pytest tests/` to verify all tests pass
4. Manual end-to-end test: start mlx_lm.server with Phase 22 model, run multi-step query through pipeline
5. Compare latency numbers against Phase 21 baseline

## Dependencies

- Tasks 2, 3 are independent (parallel)
- Task 4 depends on Tasks 2 + 3
- Tasks 5, 6 are independent (parallel)
- Task 7 depends on Tasks 5 + 6
- Task 8 depends on Task 7
- Task 9 depends on Tasks 4 + 8

## Risk Mitigation

- **Monty instability:** If v0.0.3 API is too fragile, use restricted `exec()` as fallback
- **Training data quality:** Validate code examples are syntactically correct before training
- **Quantization:** 5-bit proven to preserve LoRA signal (Phase 21 confirmed)
- **Disk space:** Need ~77GB for float16 intermediate + 20GB final. Currently 72GB available — delete float16 immediately after quantization.
