# Phase 26: LSP Navigation Tools - References

## Related Specs

### Broader Strategy Context

- **`agent-os/specs/2026-02-15-lsp-and-domain-tools-strategy/`** — Full LSP + domain tools roadmap
  - Phase 26 is the navigation-first slice (goto_definition + find_references)
  - Future phases will add hover, rename, symbols, diagnostics
  - Domain tools (ruff fix, uv add) deferred until LSP architecture proven

### Previous Phase Work

- **Phase 22: Code Mode** — Python code format for tool calls (vs XML/JSON)
  - `src/punie/agent/monty_runner.py` — Sandbox with external functions
  - Training data format: `<tool_call>result = tool(...)\nprint(result.field)</tool_call>`

- **Phase 23: ty Integration** — First typed tool (typecheck)
  - `src/punie/agent/typed_tools.py` — TypeCheckResult model + parser
  - Pattern: Pydantic models with `parse_error` field

- **Phase 24: ruff + pytest** — Expanded typed tools
  - RuffResult, TestResult models
  - 857 training examples total

- **Phase 26.1: Field Access Training** — Fixed 0% field access gap
  - Generated 120 field access examples (4 patterns × 3 tools)
  - Result: 92% accuracy, 90% field access rate
  - Lesson: Train/test prompt format consistency critical

## Typed Tools Pattern

### Architecture Overview

**Flow:** User query → Model generates Python → Sandbox executes → External function → Async bridge → ACP tool → Parse → Pydantic model → Model accesses fields

**Components:**

1. **Pydantic models** (`typed_tools.py`) — Structured results
2. **Parser functions** (`typed_tools.py`) — Raw output → Pydantic
3. **External functions** (`monty_runner.py`) — Registry in sandbox namespace
4. **Sync bridges** (`toolset.py`) — Sync sandbox → async ACP
5. **System prompt stubs** (`stubs.py`) — Function signatures + field docs
6. **Training data** (`data/phase*/`) — Examples with field access patterns

### Example: typecheck Tool

**1. Model (`typed_tools.py:36-51`):**
```python
class TypeCheckResult(BaseModel):
    success: bool
    error_count: int
    warning_count: int
    errors: list[TypeCheckError]
    parse_error: str | None = None
```

**2. Parser (`typed_tools.py:54-112`):**
```python
def parse_ty_output(output: str) -> TypeCheckResult:
    """Parse ty check output into TypeCheckResult."""
    if not output.strip():
        return TypeCheckResult(success=True, error_count=0, ...)
    # ... JSON parsing logic
```

**3. External function registry (`monty_runner.py:23-35`):**
```python
@dataclass(frozen=True)
class ExternalFunctions:
    typecheck: Callable[[str], TypeCheckResult]
    # ... other tools
```

**4. Sync bridge (`toolset.py:322-347`):**
```python
def sync_typecheck(path: str):
    """Bridge from sync sandbox to async ty via terminal."""
    async def _run_typecheck() -> TypeCheckResult:
        # ... run ty via terminal, parse output
        return parse_ty_output(output_resp.output)

    future = asyncio.run_coroutine_threadsafe(_run_typecheck(), loop)
    return future.result(timeout=30)
```

**5. System prompt stub (`stubs.py:134-169`):**
```python
def typecheck(path: str) -> TypeCheckResult:
    """Run ty type checker and return structured results.

    Args:
        path: File or directory to type check

    Returns:
        TypeCheckResult with fields:
        - success: bool (True if no errors)
        - error_count: int
        - errors: list[TypeCheckError] with .file, .line, .message

    Example:
        result = typecheck("src/")
        if result.error_count > 0:
            for error in result.errors:
                print(f"{error.file}:{error.line} - {error.message}")
    """
```

**6. Training data (`data/phase23_merged/*.jsonl`):**
```json
{
  "messages": [
    {"role": "user", "content": "Check types in src/services/"},
    {"role": "assistant", "content": "<tool_call>result = typecheck(\"src/services/\")\nif result.error_count > 0:\n    print(f\"Found {result.error_count} type errors\")\n    for error in result.errors[:3]:\n        print(f\"{error.file}:{error.line} - {error.message}\")</tool_call>"}
  ]
}
```

## LSP Protocol References

### Official Specification

- **LSP Spec:** https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/
- **JSON-RPC 2.0:** https://www.jsonrpc.org/specification

### Key LSP Methods (Phase 26 Scope)

**Lifecycle:**
- `initialize` — handshake, exchange capabilities
- `initialized` — notify server client is ready
- `shutdown` — request graceful shutdown
- `exit` — terminate server

**Document Sync:**
- `textDocument/didOpen` — notify server file is open (lazy, first access)
- `textDocument/didChange` — notify server of edits (not needed for read-only navigation)

**Navigation (Phase 26 focus):**
- `textDocument/definition` — goto definition
- `textDocument/references` — find all references

### LSP Data Structures

**Position (0-based):**
```typescript
interface Position {
  line: number;       // 0-based
  character: number;  // 0-based (UTF-16 code units)
}
```

**Range:**
```typescript
interface Range {
  start: Position;
  end: Position;
}
```

**Location:**
```typescript
interface Location {
  uri: string;      // file:// URI
  range: Range;
}
```

**textDocument/definition response:**
```typescript
Location | Location[] | null
```

**textDocument/references response:**
```typescript
Location[] | null
```

### ty Server LSP Support

**Documentation:**
- ty CLI: `ty --help`, `ty server --help`
- LSP mode: `ty server` (stdio transport by default)

**Known capabilities (to be verified in spike):**
- ✅ stdio transport (stdin/stdout)
- ❓ WebSocket transport
- ❓ definitionProvider
- ❓ referencesProvider
- ❓ hoverProvider (future)

**Spike will verify:**
1. What ServerCapabilities ty reports in initialize response
2. Whether definition/references return correct shapes
3. Latency (initialize, definition, references)

## Testing Patterns

### Fakes Pattern (Agent OS Standard)

**Fake LSP transport:**
```python
class FakeLSPTransport:
    def __init__(self, responses: dict):
        self.responses = responses
        self.sent = []

    async def send(self, message: dict):
        self.sent.append(message)

    async def receive(self) -> dict:
        method = self.sent[-1]["method"]
        return self.responses[method]
```

**Usage in tests:**
```python
def test_goto_definition_success():
    transport = FakeLSPTransport({
        "initialize": {"result": {"capabilities": {...}}},
        "textDocument/definition": {"result": {"uri": "...", "range": {...}}}
    })
    client = LSPClient(transport)
    result = await client.goto_definition("src/app.py", 10, 5)
    assert result["result"]["uri"] == "file:///src/app.py"
```

### Test Coverage Strategy

**Unit tests (fast, no I/O):**
- Parser functions (LSP response → Pydantic model)
- URI conversion (path → file:// URI)
- Position conversion (1-based ↔ 0-based)

**Integration tests (fake I/O):**
- LSP client with fake transport
- Sandbox with fake external functions
- End-to-end: model code → sandbox → fake LSP → parse

**Validation tests (real I/O, slow):**
- Real ty server on real codebase
- Real model inference on test queries
- Measure accuracy, field access, discrimination

## Research Documents

### Project Documentation

- **`docs/research/prompt-format-consistency.md`** — Phase 26.1 lesson on train/test format
  - Always use `punie.agent.prompt_utils.format_prompt()` in validation scripts
  - Manual string formatting caused 60-point accuracy drop

- **`docs/research/linting.md`** — ruff domain tool research (future phase)
  - Domain tools (ruff fix, uv add) require careful permission design
  - LSP tools are safer (read-only, no code changes)

- **`docs/flywheel.md`** — Flywheel architecture overview
  - Training loop: data → train → validate → deploy → collect feedback
  - Phase 26 fits in "expand tool coverage" flywheel iteration

### Diary Entries

- **`docs/diary/2026-02-15-phase23-task11-validation.md`** — Phase 23 field access gap
  - 73.3% overall, but 0% field access (model never used .errors, .error_count)
  - Led to Phase 26 field access training

- **`docs/diary/2026-02-15-phase26-5bit-validation.md`** — 5-bit vs 6-bit quantization
  - 5-bit is superior: 92% accuracy, 2.53s avg, 19.5 GB
  - Lesson: 32 quantization levels sufficient for LoRA preservation

- **`docs/diary/2026-02-15-phase25-7b-experiment-failed.md`** — 7B model failure analysis
  - Experiment inconclusive (5 setup flaws)
  - Decision: Stick with Qwen3-30B-A3B (proven, 100% accuracy)

## External Resources

### Language Server Protocol

- **LSP Specification:** https://microsoft.github.io/language-server-protocol/
- **pygls (Python LSP framework):** https://github.com/openlawlibrary/pygls
- **lsprotocol (Official LSP types):** https://github.com/microsoft/lsprotocol

### ty Type Checker

- **GitHub:** https://github.com/astral-sh/ty
- **Docs:** https://docs.astral.sh/ty/
- **LSP Server:** `ty server` (stdio mode)

### Pydantic

- **Pydantic v2 Docs:** https://docs.pydantic.dev/latest/
- **BaseModel:** https://docs.pydantic.dev/latest/concepts/models/

### MLX Fine-Tuning

- **MLX LoRA Fine-Tuning:** https://github.com/ml-explore/mlx-examples/tree/main/llms
- **Qwen3 Model Card:** https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct
