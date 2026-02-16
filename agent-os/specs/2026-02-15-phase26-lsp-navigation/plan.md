# Phase 26: LSP Navigation Tools (Navigation-First Slice)

## Context

Punie's current tools are text-based (`grep`, `read_file`, `write_file`). Phase 26 adds LSP-based semantic navigation using ty's language server. This is a **navigation-first slice** — only `goto_definition` and `find_references` — to validate the architecture before implementing the full LSP tool suite (hover, rename, symbols, etc.).

**Why:** LSP operations are precise (find actual symbol definitions, not text matches in comments) and safe (semantic understanding of scope, imports, types). This is lower risk than full domain tools and establishes patterns for future LSP operations.

**Prerequisites met:** Phase 23 complete, ty LSP server available via `ty server` (stdio).

**Scope decisions:**
- Navigation only: `goto_definition` + `find_references`
- This spec is a scoped slice of the broader strategy in `agent-os/specs/2026-02-15-lsp-and-domain-tools-strategy/`
- LSP client approach: investigate during spike (pygls vs custom JSON-RPC)

---

## Critical Files

| File | Role | Action |
|------|------|--------|
| `src/punie/agent/typed_tools.py` | Pydantic models + parsers | Add `GotoDefinitionResult`, `FindReferencesResult` |
| `src/punie/agent/monty_runner.py` | Sandbox function registry | Extend `ExternalFunctions` dataclass |
| `src/punie/agent/toolset.py` | Async-to-sync bridge | Add `sync_goto_definition`, `sync_find_references` |
| `src/punie/agent/stubs.py` | System prompt stubs | Add navigation tool stubs |
| `src/punie/agent/config.py` | System prompt config | Add navigation guidance |
| `src/punie/agent/lsp_client.py` | **NEW** — LSP client | Persistent connection to `ty server` |

---

## Tasks

### Task 1: Save spec documentation ✅

Create `agent-os/specs/2026-02-15-phase26-lsp-navigation/` with:
- `plan.md` — This plan
- `shape.md` — Shaping notes (scope, decisions, spike results)
- `standards.md` — agent-verification + testing standards
- `references.md` — Pointers to existing research docs and typed tools pattern

### Task 2: Spike — probe ty server LSP capabilities

**Goal:** Risk reduction. Determine what `ty server` actually supports before building.

**Create:** `scripts/spike_ty_lsp.py` — standalone script (no new dependencies) that:
1. Starts `ty server` as subprocess with stdio transport
2. Sends LSP `initialize` handshake
3. Inspects `ServerCapabilities` for `definitionProvider` and `referencesProvider`
4. Sends `textDocument/didOpen` on a real project file
5. Sends `textDocument/definition` request on a known symbol
6. Sends `textDocument/references` request on a known symbol
7. Records response shapes, latency, and which operations work

Uses raw JSON-RPC over stdin/stdout (`Content-Length: N\r\n\r\n{json}`) — no library dependency.

**Decision gate:** If ty server doesn't support definition/references, fall back to basedpyright or defer phase.

**Also decides:** pygls/lsprotocol vs custom JSON-RPC based on complexity observed.

### Task 3: Create LSP client module

**Create:** `src/punie/agent/lsp_client.py`

Minimal async LSP client for ty server with:
- `start()` — launch `ty server` subprocess, LSP initialize handshake
- `shutdown()` — clean shutdown/exit
- `open_document(file_path)` — send `textDocument/didOpen` (lazy, first-access only)
- `goto_definition(file, line, column)` — send request, return raw response dict
- `find_references(file, line, column)` — send request, return raw response dict
- Internal: `_send_request()`, `_send_notification()`, `_read_response()`, `_file_uri()`

**Lifecycle:** Module-level lazy singleton with `get_lsp_client()` async function. The client starts on first use and stays alive for the session.

**Create tests:** `tests/test_lsp_client.py` — unit tests with a `FakeLSPTransport` (per fakes-over-mocks standard). Tests protocol message formatting, response parsing, error handling.

### Task 4: Create Pydantic models and parsers

**Modify:** `src/punie/agent/typed_tools.py`

Add models following the existing pattern (every result has `parse_error: str | None = None`):

- `DefinitionLocation(BaseModel)` — `file`, `line`, `column`, `end_line`, `end_column`, `preview`
- `GotoDefinitionResult(BaseModel)` — `success`, `symbol`, `locations: list[DefinitionLocation]`, `parse_error`
- `ReferenceLocation(BaseModel)` — `file`, `line`, `column`, `preview`
- `FindReferencesResult(BaseModel)` — `success`, `symbol`, `reference_count`, `references: list[ReferenceLocation]`, `parse_error`

Add parser functions:
- `parse_definition_response(response, symbol)` — LSP response dict → `GotoDefinitionResult`
- `parse_references_response(response, symbol)` — LSP response dict → `FindReferencesResult`

Parsers handle: null results, empty arrays, single Location vs array, convert 0-based LSP positions to 1-based.

**Modify tests:** `tests/test_typed_tools.py` — add model + parser tests following existing pattern.

### Task 5: Integrate into sandbox

**Modify:** `src/punie/agent/monty_runner.py`
- Add `goto_definition` and `find_references` to `ExternalFunctions` dataclass
- Add to namespace dict in `run_code()`

**Modify:** `src/punie/agent/toolset.py`
- Add `sync_goto_definition()` and `sync_find_references()` bridge functions inside `execute_code()`
- Pattern: call `get_lsp_client()` → send request → parse with typed_tools parser → return Pydantic model
- Add to `ExternalFunctions(...)` constructor

**Modify tests:** `tests/test_monty_runner.py` (namespace), `tests/test_sandbox_typed_tools.py` (integration with fakes)

### Task 6: Update system prompt

**Modify:** `src/punie/agent/stubs.py`
- Add stubs for `goto_definition` and `find_references` after line 169
- Include field documentation and usage examples showing field access patterns
- Follow exact format of existing typed tool stubs (typecheck, ruff_check, pytest_run)

**Modify:** `src/punie/agent/config.py`
- Add guidance lines in `PUNIE_INSTRUCTIONS` for when to use navigation tools

**Modify tests:** `tests/test_stubs.py` — verify new stubs are generated

### Task 7: Generate training data

**Create:** `scripts/generate_lsp_navigation_examples.py`

~70 examples across 5 categories:
1. **Simple goto_definition (15)** — "Where is X defined?" → `goto_definition(...)` + field access
2. **Simple find_references (15)** — "Where is X used?" → `find_references(...)` + field access
3. **Navigation + field access (15)** — goto_definition + read_file at location, find_references + group by file
4. **Multi-step workflows (15)** — navigation chained with typecheck/ruff_check/read_file
5. **Direct answers (10)** — "What is LSP?" → no tool call (discrimination)

**Output:** `data/phase26_lsp_navigation/` in standard JSONL format

### Task 8: Merge and retrain

**Create:** `scripts/merge_phase26_lsp_data.py`, `scripts/train_phase26_lsp.sh`, `scripts/fuse_phase26_lsp.sh`, `scripts/quantize_phase26_lsp_5bit.sh`

Merge into full dataset:
- Phase 22 base (683) + Phase 23 ty (50) + Phase 24 ruff/pytest (100) + Phase 26 field access (120) + **Phase 26 LSP navigation (~70)** = **~1023 total**
- Output to `data/phase26_lsp_merged/`
- Train: 500 iters, batch 1, lr 1e-4, 8 layers
- Fuse to float16 → quantize to 5-bit (proven optimal)

### Task 9: Validate end-to-end

**Create:** `scripts/test_phase26_lsp_validation.py` — 25-query suite

Categories:
1. Navigation discrimination (5) — model picks goto_definition/find_references when appropriate
2. Single goto_definition + field access (5)
3. Single find_references + field access (5)
4. Multi-step workflows (5)
5. Direct answers (5) — no tool calls

**Critical:** Use `punie.agent.prompt_utils.format_prompt()` (Phase 26.1 lesson).

**Targets:** >=80% overall, >=80% field access, >=90% tool discrimination.

### Task 10: Update roadmap and documentation

**Modify:** `agent-os/product/roadmap.md` — mark Phase 26 LSP tasks as complete, update status
**Create:** `docs/diary/2026-02-xx-phase26-lsp-navigation.md` — phase diary entry
**Update:** spec with final results

---

## Verification

1. Use `astral:ruff` skill to check all modified Python files
2. Use `astral:ty` skill to check types
3. Run `uv run pytest tests/` to verify all tests pass (including new LSP tests)
4. Run the spike script to verify ty server connectivity
5. Run validation suite to verify model accuracy targets
