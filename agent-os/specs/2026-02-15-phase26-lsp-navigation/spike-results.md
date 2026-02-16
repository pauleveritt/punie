# Phase 26: LSP Navigation Tools - Spike Results

**Date:** 2026-02-15
**Script:** `scripts/spike_ty_lsp.py`
**Status:** ✅ SUCCESS

## Summary

ty server **fully supports** the LSP methods needed for Phase 26 navigation tools.

## Server Capabilities

**Supported (from initialize response):**
- ✅ `definitionProvider`: True
- ✅ `referencesProvider`: True
- ✅ `hoverProvider`: True (future)
- ✅ `renameProvider`: True (future)
- ✅ `documentSymbolProvider`: True (future)

**Phase 26 verdict:** ✅ All requirements met!

## Performance Metrics

| Operation | Latency | Notes |
|-----------|---------|-------|
| initialize | ~100ms | One-time handshake cost |
| textDocument/didOpen | <10ms | Notification (no response) |
| textDocument/definition | 62ms | Array of 1 Location |
| textDocument/references | 80ms | Array of 10 Locations |

**Verdict:** Performance is excellent (<100ms for navigation operations).

## Response Format Analysis

### goto_definition Response

**Format:** Array of Location objects (LSP standard)

**Example:**
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": [
    {
      "uri": "file:///path/to/pydantic/main.py",
      "range": {
        "start": {"line": 117, "character": 6},
        "end": {"line": 117, "character": 15}
      }
    }
  ]
}
```

**Test case:** `BaseModel` at `typed_tools.py:36:24`
- ✅ Correctly found definition in pydantic's main.py
- ✅ Returned array with 1 Location
- ✅ Range is 0-based (LSP standard)

### find_references Response

**Format:** Array of Location objects (LSP standard)

**Example:**
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": [
    {
      "uri": "file:///path/to/typed_tools.py",
      "range": {
        "start": {"line": 53, "character": 4},
        "end": {"line": 53, "character": 19}
      }
    },
    // ... 9 more locations
  ]
}
```

**Test case:** `parse_ty_output` at `typed_tools.py:54:9`
- ✅ Found 10 references across typed_tools.py and test files
- ✅ Returned array of Location objects
- ✅ Includes both definition and usage sites

## Protocol Quirks Discovered

### 1. Notifications Before Responses

**Issue:** ty server sends `textDocument/publishDiagnostics` notifications before responding to `textDocument/definition` requests.

**Impact:** Client must read multiple messages until it finds the response with matching ID.

**Solution implemented:**
```python
def _send_request(self, method: str, params: dict) -> dict:
    request_id = self.next_id
    self.next_id += 1

    self._send_message({...})

    # Read messages until we get response with matching ID
    for attempt in range(max_attempts):
        message = self._read_message()
        if message.get("id") == request_id:
            return message
        # Continue reading (notification)
```

### 2. shutdown Params

**Issue:** ty server expects `params: null` for shutdown, not `params: {}`.

**Error if using `{}`:**
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "error": {
    "code": -32602,
    "message": "JSON parsing failure: invalid type: map, expected unit"
  }
}
```

**Solution:** Use `None` in Python (serializes to `null`).

### 3. Response Format

**Both operations return arrays:**
- `textDocument/definition` → `Location[]` (not single Location)
- `textDocument/references` → `Location[]`

**Implication:** Parser must handle arrays, even if only 1 Location.

## Decision: Custom JSON-RPC (No lsprotocol Dependency)

**Rationale:**

✅ **Simple protocol:**
- Only need 6 methods (initialize, initialized, didOpen, definition, references, shutdown)
- No advanced features needed (cancellation, partial results, workspaces)

✅ **Quirks are manageable:**
- Notification handling: 10 lines of code
- Param types: Known from spike

✅ **Zero dependencies:**
- Keeps Punie lightweight
- ~200 lines of custom code vs ~50 KB library

❌ **lsprotocol not needed because:**
- We're not implementing a full LSP client
- No need for type safety on all LSP structures
- Spike validated exact response shapes we'll receive

## Code Patterns for LSP Client

### URI Conversion

```python
def _file_uri(self, file_path: str) -> str:
    """Convert file path to LSP file:// URI."""
    from pathlib import Path
    return Path(file_path).resolve().as_uri()  # file:///absolute/path
```

### Position Conversion (1-based ↔ 0-based)

```python
def _to_lsp_position(self, line: int, column: int) -> dict:
    """Convert 1-based line/col to LSP 0-based Position."""
    return {"line": line - 1, "character": column - 1}

def _from_lsp_position(self, pos: dict) -> tuple[int, int]:
    """Convert LSP 0-based Position to 1-based line/col."""
    return (pos["line"] + 1, pos["character"] + 1)
```

### Message Sending (with Content-Length header)

```python
def _send_message(self, message: dict) -> None:
    body = json.dumps(message)
    content = f"Content-Length: {len(body)}\r\n\r\n{body}"
    self.process.stdin.write(content.encode("utf-8"))
    self.process.stdin.flush()
```

### Message Reading (with header parsing)

```python
def _read_message(self, timeout: float = 10.0) -> dict:
    # Read headers until \r\n
    headers = {}
    while True:
        line = self.process.stdout.readline().decode("utf-8")
        if line == "\r\n":
            break
        if ":" in line:
            key, value = line.split(":", 1)
            headers[key.strip()] = value.strip()

    # Read body based on Content-Length
    content_length = int(headers["Content-Length"])
    body = self.process.stdout.read(content_length).decode("utf-8")
    return json.loads(body)
```

## Next Steps

✅ **Task 2 complete** — ty server validated

**Task 3:** Create `src/punie/agent/lsp_client.py` based on spike patterns
- Use module-level singleton (persistent connection)
- Implement 6 LSP methods (initialize, initialized, didOpen, definition, references, shutdown)
- Handle notifications before responses
- Convert paths ↔ URIs, positions (1-based ↔ 0-based)

**No blockers** — All risks mitigated by spike.
