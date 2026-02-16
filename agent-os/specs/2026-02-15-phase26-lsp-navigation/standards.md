# Phase 26: LSP Navigation Tools - Standards

## Testing Standards

### 1. Fakes Over Mocks

**DO:**
```python
class FakeLSPClient:
    def __init__(self, responses: dict):
        self.responses = responses
        self.requests = []

    async def goto_definition(self, file, line, col):
        self.requests.append(("goto_definition", file, line, col))
        return self.responses.get("goto_definition", None)
```

**DON'T:**
```python
from unittest.mock import Mock

mock_client = Mock()
mock_client.goto_definition.return_value = {...}
```

**Why:** Fakes are testable themselves, easier to debug, and document expected behavior.

### 2. Test Coverage Requirements

**Every module must have:**
- Unit tests for pure functions (parsers, validators)
- Integration tests with fakes (LSP client with fake transport)
- Error path tests (null responses, malformed data, timeouts)

**Example test structure:**
```python
def test_parse_definition_response_success():
    """Should parse LSP Location into GotoDefinitionResult."""
    ...

def test_parse_definition_response_null():
    """Should handle null result gracefully."""
    ...

def test_parse_definition_response_malformed():
    """Should set parse_error on malformed data."""
    ...
```

### 3. Docstring Requirements

**Every public function:**
```python
def parse_definition_response(response: dict, symbol: str) -> GotoDefinitionResult:
    """Parse LSP textDocument/definition response into structured result.

    Args:
        response: LSP response dict with 'result' field (Location | Location[] | null)
        symbol: Symbol name being searched (for error messages)

    Returns:
        GotoDefinitionResult with locations (or parse_error if parsing fails)

    Note:
        Handles both single Location and array of Locations.
        Converts LSP 0-based line/column to 1-based for human readability.
    """
```

## Code Quality Standards

### 1. Type Annotations

**All functions must have types:**
```python
async def goto_definition(
    self,
    file_path: str,
    line: int,
    column: int
) -> dict[str, Any]:
    """..."""
```

**Use TYPE_CHECKING for circular imports:**
```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from punie.agent.typed_tools import GotoDefinitionResult
```

### 2. Error Handling

**All LSP operations must handle:**
- Server not running (subprocess spawn failure)
- Timeout (long-running type inference)
- Malformed response (protocol violation)
- Symbol not found (null result)

**Pattern:**
```python
try:
    response = await self._send_request("textDocument/definition", params)
    return response
except LSPError as e:
    logger.error(f"goto_definition failed: {e}")
    raise
except asyncio.TimeoutError:
    logger.error(f"goto_definition timed out after 30s")
    raise
```

### 3. Logging

**All LSP operations must log:**
```python
logger.info(f"LSP: goto_definition({file_path}:{line}:{column})")
logger.debug(f"LSP request: {json.dumps(params)}")
logger.debug(f"LSP response: {json.dumps(response)}")
```

**Use appropriate log levels:**
- `DEBUG` — LSP messages, request/response bodies
- `INFO` — Tool calls, high-level operations
- `WARNING` — Recoverable errors (null results)
- `ERROR` — Unrecoverable errors (server crash)

## Pydantic Model Standards

### 1. Consistent Field Names

**Follow existing typed_tools.py conventions:**
- `success: bool` — True if operation succeeded
- `parse_error: str | None = None` — Set if parsing failed
- `*_count: int` — Aggregate counts (error_count, reference_count)
- `file: str` — File paths (not `path` or `filename`)
- `line: int` — 1-based line numbers (not 0-based)
- `column: int` — 1-based column numbers (not 0-based)

### 2. Model Hierarchy

**Location models (nested):**
```python
class DefinitionLocation(BaseModel):
    """A single definition location."""
    file: str
    line: int
    column: int
    # ... other fields
```

**Result models (top-level):**
```python
class GotoDefinitionResult(BaseModel):
    """Result of goto_definition tool."""
    success: bool
    symbol: str
    locations: list[DefinitionLocation]
    parse_error: str | None = None
```

### 3. Parser Function Signature

**Consistent pattern:**
```python
def parse_<tool>_output(output: str | dict) -> <Tool>Result:
    """Parse <tool> output into <Tool>Result.

    Args:
        output: Raw output from <tool> command

    Returns:
        <Tool>Result with parsed data (or parse_error if parsing fails)
    """
```

## LSP Client Standards

### 1. Protocol Compliance

**Must implement minimum LSP lifecycle:**
1. `initialize` — handshake with server capabilities
2. `initialized` — notify server client is ready
3. `textDocument/didOpen` — notify server of opened files
4. `shutdown` — graceful shutdown request
5. `exit` — terminate server process

**Must send correct Content-Type headers:**
```
Content-Length: 123\r\n
\r\n
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{...}}
```

### 2. URI Handling

**Always use file:// URIs (LSP requirement):**
```python
def _file_uri(self, file_path: str) -> str:
    """Convert file path to LSP file:// URI."""
    from pathlib import Path
    abs_path = Path(file_path).resolve()
    return abs_path.as_uri()  # file:///absolute/path
```

**Never use bare paths in LSP requests.**

### 3. Position Conversions

**LSP uses 0-based line/column, humans use 1-based:**
```python
def _to_lsp_position(self, line: int, column: int) -> dict:
    """Convert 1-based line/col to LSP 0-based Position."""
    return {"line": line - 1, "character": column - 1}

def _from_lsp_position(self, pos: dict) -> tuple[int, int]:
    """Convert LSP 0-based Position to 1-based line/col."""
    return (pos["line"] + 1, pos["character"] + 1)
```

**Always convert at LSP client boundary, never in parsers.**

## Training Data Standards

### 1. JSONL Format

**Every example must have:**
```json
{
  "messages": [
    {"role": "user", "content": "Where is UserService defined?"},
    {"role": "assistant", "content": "<tool_call>result = goto_definition(\"src/services/user.py\", 10, 5, \"UserService\")\nprint(f\"Defined at {result.locations[0].file}:{result.locations[0].line}\")</tool_call>"}
  ]
}
```

### 2. Field Access Coverage

**At least 80% of tool call examples must access structured fields:**
- ✅ `result.locations[0].file`
- ✅ `result.reference_count`
- ✅ `if result.success:`
- ❌ Just calling tool without using result

**Why:** Phase 23 validation showed 0% field access without explicit training.

### 3. Multi-Step Workflow Examples

**Must include chained operations:**
```python
# Example: goto_definition → read_file at location
result = goto_definition("src/app.py", 15, 10, "UserService")
if result.success:
    loc = result.locations[0]
    content = read_file(loc.file)
    # Extract class definition around loc.line
```

**Why:** Trains model to use navigation as starting point for deeper analysis.

### 4. Discrimination Examples

**Must include queries that should NOT use LSP:**
```json
{
  "messages": [
    {"role": "user", "content": "What is the Language Server Protocol?"},
    {"role": "assistant", "content": "The Language Server Protocol (LSP) is..."}
  ]
}
```

**Why:** Prevents overfitting where model calls LSP tools for conceptual questions.

## Git Commit Standards

### 1. Atomic Commits

**Each task should be a separate commit:**
- Task 2: Spike ty LSP capabilities
- Task 3: Add LSP client module
- Task 4: Add GotoDefinitionResult and FindReferencesResult models
- Task 5: Integrate LSP tools into sandbox
- Task 6: Update system prompt with navigation stubs
- Task 7: Generate LSP navigation training data
- Task 8: Train Phase 26 LSP model
- Task 9: Validate Phase 26 LSP model
- Task 10: Document Phase 26 LSP results

### 2. Commit Message Format

```
<type>: <summary>

<body>

<footer>
```

**Types:**
- `feat` — new feature (LSP client, new models)
- `test` — add/modify tests
- `docs` — documentation only
- `refactor` — code restructuring (no behavior change)
- `fix` — bug fix

**Example:**
```
feat: add LSP client for ty server navigation

Implements minimal async LSP client with:
- initialize/shutdown lifecycle
- textDocument/didOpen lazy loading
- goto_definition and find_references requests

Uses module-level singleton for persistent connection across tool calls.

Part of Phase 26 LSP Navigation Tools (Task 3)
```

## Agent Verification Standards

### 1. Pre-Commit Checks

**Must pass before commit:**
```bash
# Linting
uv run ruff check src/punie/agent/lsp_client.py

# Type checking
uv run ty check src/punie/agent/lsp_client.py

# Tests
uv run pytest tests/test_lsp_client.py -v
```

**Zero tolerance:**
- No linting errors
- No type errors
- All tests pass

### 2. Post-Integration Checks

**Must pass after integration:**
```bash
# Full test suite
uv run pytest tests/ -v

# End-to-end validation
uv run python scripts/test_phase26_lsp_validation.py
```

**Targets:**
- Overall: >=80% (20/25 queries)
- Field access: >=80%
- Tool discrimination: >=90%
