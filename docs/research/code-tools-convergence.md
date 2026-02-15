# Research: Converging Code Tools + Training Data + Monty

## Context

Three industry players (Anthropic, Cloudflare, Pydantic) have converged on the same insight: instead of LLMs making sequential tool calls via JSON, let them write code that calls tools as functions. Punie has a unique advantage here: **we control the training data**. We can train our Qwen model to output Python code instead of JSON tool calls, and use Monty (Pydantic's Rust-based Python sandbox with ty included) to execute it.

This isn't just a nice-to-have — it solves a **documented architectural problem** where tool calling is fundamentally broken in our production agent loop.

---

## The Problem Code Mode Solves

### The Documented Architectural Incompatibility

From `docs/research/tool-calling-investigation.md`:

> **Root Cause:** Architectural incompatibility between mlx_lm.server and PydanticAI's tool calling expectations.
> - **mlx_lm.server:** Returns raw text
> - **PydanticAI:** Expects structured `tool_calls` objects
> - **The model:** Generates JSON in markdown code blocks, which isn't parsed

The model already outputs tool calls as **text** (```json code fences). PydanticAI ignores this text and looks for structured `tool_calls` objects that mlx_lm.server never provides. Tool calling only works in our eval pipeline (which has a custom text parser), not in production.

### Phase 21's Ongoing Format Battle

Phase 21 (Inference Speed Optimization) confirmed this problem in production. Profiling the 5-bit fused model revealed **40% accuracy (2/5 queries)** — the model gives direct answers instead of calling tools. Root cause: a **second format mismatch** on top of the architectural one:

- Training data used ```json code fence format
- mlx_lm.server expects Qwen3's native XML format (`<tool_call><function=name>...</function></tool_call>`)
- Server checks for `<tool_call>` token (ID 151657) at the token level — JSON fences never trigger this

Phase 21 has prepared an XML format fix (`scripts/convert_to_xml_format.py`, `scripts/train_phase21_xml.sh`) converting all 683 training examples to XML. This fix aligns training data with the server's parser. But it's still fragile — it adds yet another format-specific layer that breaks when any component changes.

**The format history illustrates the fragility:**
1. Phase 8: Trained on ```json code fences → worked in eval (custom parser) but not in production
2. Phase 21 fix: Converting to XML `<tool_call>` → aligns with mlx_lm.server parser
3. Future risk: Any server update, model change, or Pydantic AI update could break the format chain again

### Code Mode: The Fundamental Fix

**Code mode flips this from a bug into a feature.** Instead of fighting text-based output through format-specific parsers, we lean into it: the model outputs Python code (text), and Monty executes it. No structured API needed. The mlx_lm.server "limitation" of returning raw text becomes irrelevant.

This isn't just cleaner — it eliminates an entire category of bugs (format mismatches) that have plagued every phase of development.

---

## The Convergence: What Changes in Training Data

### Current Training Format (JSON tool calls)

System prompt lists tools as prose descriptions:
```
Available tools:
- read_file(path): Read a file's contents
- run_command(command, args, cwd): Run a shell command
```

Assistant outputs JSON in a code fence:
```
I'll use the read_file tool.

‍```json
{"name": "read_file", "arguments": {"path": "src/main.py"}}
‍```
```

Then a separate "Tool result:" user message, then another assistant turn to interpret.

**Each tool call = one full model inference turn (~14s on 5-bit local model).**

### New Training Format (Python code)

System prompt lists tools as **typed Python function stubs** (generated from our existing tool definitions in `src/punie/agent/toolset.py`):

```
You have access to the following Python functions. When you need to use tools,
write Python code in a ```python code fence. Your code will be executed in a
sandbox with these functions available:

‍```python
async def read_file(*, path: str) -> str:
    """Read a file's contents from the workspace."""
    ...

async def write_file(*, path: str, content: str) -> str:
    """Write content to a file (creates or overwrites)."""
    ...

async def run_command(*, command: str, args: list[str] | None = None, cwd: str | None = None) -> str:
    """Run a shell command in the workspace."""
    ...
‍```
```

Assistant outputs Python in a code fence:
```python
content = await read_file(path="src/main.py")
print(content)
```

### Why This Is Better For Local Models

**Single tool call** — same cost either way (1 model turn).

**Multi-step workflow** — the massive win:

| Task: "Find test files using pytest, count test functions in each" |
|---|
| **JSON format**: model turn → `find` → result → model turn → `read_file` on file 1 → result → model turn → `read_file` on file 2 → ... → model turn → summarize. **N+2 model turns.** At 14s each, a 10-file task takes **2+ minutes** just in inference. |
| **Code format**: model writes one Python block that loops, reads, counts, prints. **1 model turn.** The tool calls still happen (Monty pauses at each `await`), but the model doesn't need to re-reason between them. **14 seconds total inference.** |

This is the single most impactful optimization for local model latency.

---

## The ty Safety Net

Monty embeds Astral's `ty` type checker. Before executing LLM-generated code:

```python
m = pydantic_monty.Monty(
    code,
    external_functions=['read_file', 'run_command', 'write_file'],
    type_check=True,
    type_check_stubs=tool_stubs,  # Our typed function signatures
)
```

If the model writes `read_file(pat="foo.py")` (typo in `path`), ty catches it **before execution**. This is especially valuable for our smaller local model which is more error-prone than Claude/GPT.

The stubs we'd provide to ty are the same function signatures shown to the model in the system prompt — a single source of truth for both the model's understanding and the type checker's validation.

---

## How Training Data Generation Changes

### Source of truth: `src/punie/agent/toolset.py`

Our 7 tools are already defined as typed async Python functions. We use `inspect.signature()` (like CodeModeToolset's `_python_signature` module does) to generate stubs automatically. This means the training data stays in sync with the actual tool definitions.

### Three example categories (same discrimination as Phase 5)

**1. Single tool call (~40% of examples)**
```
User: Show me the contents of config.py
Assistant:
‍```python
content = await read_file(path="config.py")
print(content)
‍```
Code output: [file contents]
Assistant: The config file contains...
```

**2. Multi-step tool workflow (~30% of examples) — NEW category**
```
User: Find all Python files that import asyncio and show their first 5 lines
Assistant:
‍```python
result = await run_command(command="grep", args=["-rl", "import asyncio", "--include=*.py", "."])
files = [f for f in result.strip().split("\n") if f]
for filepath in files:
    content = await read_file(path=filepath)
    lines = content.split("\n")[:5]
    print(f"--- {filepath} ---")
    print("\n".join(lines))
    print()
‍```
Code output: [multi-file output]
Assistant: Found 8 files importing asyncio...
```

**3. Direct answer (~30% of examples) — UNCHANGED**
```
User: What is dependency injection?
Assistant: Dependency injection is a design pattern where...
```

### Conversion from existing examples

Most existing training examples can be mechanically converted:
- `{"name": "read_file", "arguments": {"path": "X"}}` → `await read_file(path="X")`
- `{"name": "run_command", "arguments": {"command": "grep ..."}}` → `await run_command(command="grep", args=[...])`
- "Tool result: ..." → "Code output: ..."

The new multi-step examples need to be authored fresh — they demonstrate the unique value of code mode.

---

## Connection to Existing Research

Our `docs/research/tool-calling-and-agent-models.md` already describes the "Skills" pattern:

```python
class FixTypeErrors:
    async def run(self, file_path: str):
        diagnostics = await self.lsp.get_diagnostics(file_path)      # Deterministic
        plan = await self.agent.think(f"Fix: {diagnostics}")          # Fuzzy
        edits = await self.code_tools.apply_edits(plan.edits)        # Deterministic
        new_diagnostics = await self.lsp.get_diagnostics(file_path)  # Deterministic
```

With code mode, **the model writes this kind of code itself**. Instead of us hard-coding skill classes, the model composes tools dynamically based on the user's request. The "skill layer" becomes the model's ability to write Python that orchestrates tools.

This connects to Anthropic's vision too: "Claude writes code that calls multiple tools, processes their outputs, and controls what information actually enters its context window."

---

## What Pydantic AI's CodeModeToolset Does For Us

PR [#4153](https://github.com/pydantic/pydantic-ai/pull/4153) implements exactly this pattern. When it ships:

1. `CodeModeToolset` wraps our existing `FunctionToolset` (no tool rewrite needed)
2. It auto-generates Python stubs from our tool definitions
3. The model sees a single `run_code_with_tools` function
4. Monty executes with ty validation
5. External function calls pause → we provide results → execution continues

Our training data would need to match what CodeModeToolset presents to the model. The stubs it generates (keyword-only params, full type hints) become the format our training examples use.

---

## Maturity Assessment

| Component | Status | Blocker? |
|-----------|--------|----------|
| Monty interpreter | v0.0.3 released | No classes, limited stdlib — but sufficient for tool-calling code |
| ty type checking | Embedded in Monty | Works |
| CodeModeToolset | PR #4153 (WIP) | Not merged yet — could use Monty directly |
| Our training pipeline | Established (Phase 8) | Ready to generate new format |
| Qwen3-Coder as code generator | Production | It's a Coder model — Python generation is its strength |
| Phase 21 XML format fix | Ready for training | Short-term fix; code mode is the long-term solution |
| Production tool calling | **Broken** (40% accuracy) | Code mode bypasses the entire format chain |

The main risk is Monty's limited Python subset. But tool-calling code is simple: `await` calls, string processing, `if/for/print`. No classes or complex stdlib needed.

### Relationship to Phase 21

Phase 21's XML format fix should proceed — it's the short-term path to working tool calls. But code mode is the long-term solution that eliminates format fragility entirely. The two efforts are complementary:

- **Phase 21 (short-term):** Fix XML format → get tool calling working in current architecture
- **Code mode phase (long-term):** Replace JSON/XML tool calls with Python code → eliminate format issues permanently + gain multi-step workflow efficiency

---

## Implementation Steps

1. **Generate Python stubs** from `src/punie/agent/toolset.py` using `inspect.signature()`
2. **Convert existing training data** (683 examples) to Python code format:
   - Replace JSON tool calls with `await function_name(args)`
   - Update "Tool result:" → "Code output:"
   - Keep direct-answer examples unchanged
3. **Author 150-200 multi-step workflow examples** showing Python loops/conditionals that call multiple tools
4. **Train Phase 22 model** with code-mode format (same LoRA pipeline as Phase 8/21)
5. **Integrate Monty execution**:
   - Option A: Wait for `CodeModeToolset` PR merge → drop-in replacement
   - Option B: Use Monty directly with custom tool registration
6. **Update eval suite** to expect Python code output instead of JSON
7. **Benchmark against Phase 21 XML format** (latency + accuracy on multi-step tasks)

### Success Criteria

- **Accuracy:** ≥90% on single-tool discrimination (Phase 5 baseline)
- **Multi-step latency:** 1 model turn for N-tool workflows (vs N+2 turns in JSON format)
- **Type safety:** ty catches malformed tool calls before execution
- **Production compatibility:** Works with mlx_lm.server (no format parsing needed)

---

## Summary

The convergence is: **train the model to output Python instead of JSON, execute with Monty, validate with ty.** This:

1. **Solves the production tool-calling gap** (no structured API needed)
2. **Eliminates multi-turn overhead** (one code block = N tool calls)
3. **Adds type safety** (ty catches errors before execution)
4. **Plays to the model's strength** (Qwen3-Coder is trained on Python)
5. **Aligns with Pydantic AI's direction** (CodeModeToolset when it ships)
6. **Reuses our existing infrastructure** (same tools, same LoRA pipeline, same eval suite)

---

## Sources

- [Anthropic Programmatic Tool Calling](https://platform.claude.com/docs/en/agents-and-tools/tool-use/programmatic-tool-calling)
- [Anthropic Advanced Tool Use](https://www.anthropic.com/engineering/advanced-tool-use)
- [Anthropic Code Execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp)
- [Cloudflare Code Mode](https://blog.cloudflare.com/code-mode/)
- [Pydantic Monty GitHub](https://github.com/pydantic/monty)
- [Pydantic AI CodeModeToolset PR #4153](https://github.com/pydantic/pydantic-ai/pull/4153)
- [Simon Willison on Monty](https://simonwillison.net/2026/Feb/6/pydantic-monty/)
