# Phase 26: LSP Navigation Tools - Shaping Notes

## Scope Decision: Navigation-First Slice

**Why navigation only (goto_definition + find_references)?**

1. **Lower risk than full domain tools** — LSP operations are read-only (no writes, no refactors)
2. **Establishes architecture patterns** — Once LSP client + typed models work, can add hover/rename/symbols
3. **Immediate value** — "Where is X defined?" and "Where is X used?" are high-frequency queries
4. **Manageable training data** — ~70 examples vs ~200+ for full LSP suite

**Deferred to future phases:**
- `textDocument/hover` — type information at cursor
- `textDocument/rename` — refactoring operations (write-heavy, needs more validation)
- `textDocument/documentSymbol` — outline/structure view
- `textDocument/completion` — autocomplete (needs incremental updates)
- `workspace/symbol` — global symbol search

## LSP Client Architecture Decisions

### Decision 1: Persistent vs Per-Request Connection

**Chosen:** Persistent connection (module-level singleton)

**Reasoning:**
- LSP initialize handshake is expensive (~100-500ms)
- ty server maintains incremental state (opened documents, parsed ASTs)
- Models trained on multi-step workflows will call navigation tools multiple times
- Session lifetime aligns with agent session lifetime

**Trade-off:** Adds lifecycle management complexity, but saves 100ms+ per tool call

### Decision 2: Custom JSON-RPC vs pygls/lsprotocol

**To be decided in Task 2 (spike).**

**If ty server's LSP is simple:**
- Custom JSON-RPC (no new deps, 100 lines of code)
- Only need: initialize, didOpen, definition, references
- Pattern: `Content-Length: N\r\n\r\n{json}`

**If ty server has quirks or needs advanced features:**
- Use `lsprotocol` (official LSP types from pygls team)
- ~50 KB dependency, well-maintained
- Handles edge cases (multi-part messages, cancellation, etc.)

**Decision gate:** Spike will reveal which path is pragmatic.

### Decision 3: Error Handling Strategy

**Approach:** Parse errors gracefully, return structured results with `parse_error` field

**LSP errors to handle:**
1. Server not available (ty not installed, spawn failure)
2. Initialize handshake failure (version mismatch, capabilities)
3. Symbol not found (null response, empty array)
4. Timeout (long-running type inference)
5. Malformed response (protocol violation)

**Pattern:**
```python
try:
    response = await client.goto_definition(file, line, col)
    return parse_definition_response(response, symbol)
except LSPError as e:
    return GotoDefinitionResult(
        success=False,
        symbol=symbol,
        locations=[],
        parse_error=f"LSP error: {e}"
    )
```

**Why:** Model can check `result.parse_error` and fall back to grep/read_file

## Training Data Strategy

### Coverage Goals

| Category | Count | Purpose |
|----------|-------|---------|
| Simple goto_definition | 15 | "Where is UserService defined?" |
| Simple find_references | 15 | "Where is calculate_total used?" |
| Navigation + field access | 15 | Access `.file`, `.line`, `.locations[0]` fields |
| Multi-step workflows | 15 | goto_definition → read_file at location → typecheck |
| Direct answers | 10 | "What is LSP?" — discrimination |
| **Total** | **70** | |

### Field Access Patterns to Train

Based on Phase 23 lesson (0% field access without training):

```python
# Pattern 1: Check success first
result = goto_definition("src/app.py", 10, 5, "UserService")
if result.success:
    print(f"Defined at {result.locations[0].file}:{result.locations[0].line}")

# Pattern 2: Iterate locations
result = find_references("src/app.py", 15, 8, "process_order")
print(f"Found {result.reference_count} references:")
for ref in result.references:
    print(f"  {ref.file}:{ref.line} - {ref.preview}")

# Pattern 3: Parse error handling
result = goto_definition("src/app.py", 10, 5, "MissingClass")
if result.parse_error:
    print(f"Error: {result.parse_error}")
```

**Lesson from Phase 26.1:** 22% field access coverage in training → 90% field access in inference.

## Dependencies and Installation

### Runtime Dependencies

**New:**
- `ty` (already required) — provides `ty server` LSP server

**Conditional:**
- `lsprotocol` (only if spike shows custom JSON-RPC insufficient)

**Not needed:**
- `pygls` (LSP server library, Punie is a client)
- `python-lsp-server` (alternative server)

### Development Dependencies

**No new test deps** — use fakes pattern:
```python
class FakeLSPClient:
    async def goto_definition(self, file, line, col):
        return {"result": {"uri": "file:///src/app.py", "range": {...}}}
```

## Risk Assessment

### High Risk Items

1. **ty server LSP support is incomplete** ❌
   - **Mitigation:** Task 2 spike validates capabilities before implementation
   - **Fallback:** Use `basedpyright server` (fully LSP compliant) or defer phase

2. **LSP protocol quirks** ⚠️
   - **Mitigation:** Spike tests real requests/responses on actual codebase
   - **Fallback:** Use lsprotocol library instead of custom JSON-RPC

### Medium Risk Items

3. **Training data quality** ⚠️
   - **Mitigation:** Generate examples from real project files (svcs-di, tdom-svcs)
   - **Target:** 70 examples across 5 categories maintains Phase 26 field access patterns

4. **Model confuses goto_definition with grep** ⚠️
   - **Mitigation:** Add discrimination examples ("Find file containing X" → grep, "Where is X defined?" → goto_definition)

### Low Risk Items

5. **LSP client lifecycle bugs** ✅
   - **Mitigation:** Comprehensive unit tests with fakes
   - **Fallback:** Per-request connection (slower but simpler)

## Success Criteria

### Functional Requirements

- ✅ ty server starts and responds to LSP initialize
- ✅ goto_definition returns structured locations (file, line, column)
- ✅ find_references returns structured reference list
- ✅ Errors are handled gracefully (parse_error field populated)
- ✅ Client survives across multiple tool calls (persistent connection)

### Performance Requirements

- ✅ LSP initialize < 1s (first call overhead)
- ✅ goto_definition < 500ms (subsequent calls)
- ✅ find_references < 1s (may scan multiple files)

### Accuracy Requirements (End-to-End Validation)

- **Overall:** >=80% (20/25 queries)
- **Field access:** >=80% (model accesses `.locations`, `.references`, etc.)
- **Tool discrimination:** >=90% (picks goto_definition vs grep correctly)

### Code Quality Requirements

- ✅ `astral:ruff` passes on all modified files
- ✅ `astral:ty` passes (no type errors)
- ✅ All tests pass (`uv run pytest tests/`)
- ✅ Fakes over mocks (no unittest.mock in tests)

## Timeline Estimate

**Total:** ~4-6 hours (assumes no major blockers)

| Task | Estimate | Risk |
|------|----------|------|
| Task 1: Spec docs | 30 min | Low |
| Task 2: Spike | 1 hour | **High** (may reveal blockers) |
| Task 3: LSP client | 1.5 hours | Medium |
| Task 4: Pydantic models | 1 hour | Low |
| Task 5: Sandbox integration | 1 hour | Low |
| Task 6: System prompt | 30 min | Low |
| Task 7: Training data | 1 hour | Low |
| Task 8: Train + quantize | 2 hours | Low (automated) |
| Task 9: Validation | 1 hour | Medium |
| Task 10: Docs | 30 min | Low |

**Critical path:** Task 2 (spike) → Task 3 (LSP client). If spike fails, reassess approach.
