# ty LSP Integration — Ecosystem Findings

**Date:** 2026-02-15
**Context:** Research for Punie Phase 26 (LSP-Based Tool Architecture)

---

## Executive Summary

**Key Finding:** ty LSP integration is actively being tracked in multiple projects, with concrete evaluation work completed and blockers identified.

**Three major sources of ty LSP work:**

1. **Pydantic AI** — Issue #3970 tracking ty readiness for type checking replacement
2. **tdom** — Working LSP server implementation for domain-specific features
3. **TweakCC** — LSP tool integration in another agent system

**Recommendation:** Punie's Phase 26 LSP implementation should reference these efforts, particularly tdom's architecture and Pydantic AI's blocker analysis.

---

## 1. Pydantic AI — Issue #3970: Track ty Type Checker Readiness

**Status:** OPEN (created 2026-01-09)
**Assignee:** @dsfaccini
**Labels:** chore

### Summary

Pydantic AI evaluated ty as a potential pyright replacement and documented **specific blockers** preventing adoption.

### Key Findings

- **417 total diagnostics** when running ty on pydantic-ai codebase
- **337 are false positives (81%)**
- **80 legitimate errors** that should be caught

### Blocking Issues (Upstream ty Bugs)

| Priority | Issue | Description | Error Count | Status |
|----------|-------|-------------|-------------|--------|
| **High** | [ty#592](https://github.com/astral-sh/ty/issues/592) | PEP 696 TypeVar defaults not supported | 89 | Blocking |
| **High** | [ty#1332](https://github.com/astral-sh/ty/issues/1332) | `**kwargs` unpacking with TypedDict | 84 | Blocking |
| **Medium** | [ty#2265](https://github.com/astral-sh/ty/issues/2265) | Dict literals assignable to TypedDict unions | 25+ | Blocking |
| **Medium** | [ty#1535](https://github.com/astral-sh/ty/issues/1535) | Concatenate special form support | 22 | Blocking |
| **Medium** | [ty#154](https://github.com/astral-sh/ty/issues/154) | PEP 728 `closed=True` for TypedDict | 35 | **ty correct, wait for PEP 728** |
| **Lower** | [ty#2030](https://github.com/astral-sh/ty/issues/2030) | Generic inference for `@contextmanager` | 17 | Blocking |
| **Lower** | [ty#2182](https://github.com/astral-sh/ty/issues/2182) | Nested generic classes with defaults | - | Blocking |

### Important Note

One issue (#154 - TypedDict `in` narrowing) is where **ty is technically correct** and pyright/mypy are lenient. TypedDicts are open by default, so `if 'key' in td:` can't safely narrow types. PEP 728's `closed=True` will resolve this properly.

### Evaluation Artifacts

Issue mentions artifacts in `explore-ty` branch under `local-notes/` (not public, likely contributor's local workspace).

### Strategic Implications for Punie

1. **ty is not ready for type checking** — 81% false positive rate is too high
2. **But ty LSP may still be valuable** — LSP operations (goto definition, find references, hover) don't depend on the type inference engine's precision
3. **Monitor upstream issues** — when these 7 issues are resolved, ty becomes viable

**Key insight:** ty's LSP *protocol implementation* is separate from its type inference engine. Phase 26 could use ty's LSP server for **navigation/refactoring** even if type *checking* remains with pyright/basedpyright.

---

## 2. tdom LSP Server — Working Implementation

**Location:** `/Users/pauleveritt/projects/t-strings/tdom/tdom_lsp/`
**Status:** Implemented and working

### Architecture

The tdom LSP server provides a **reference implementation** of domain-specific LSP features:

**Core modules:**
- `server.py` — Main `TDOMLanguageServer` class
- `component_scanner.py` — Scans workspace for tdom components
- `completions.py` — Component name and attribute completions
- `hover.py` — Hover documentation for components
- `diagnostics.py` — Component validation
- `context.py` — LSP context management
- `spec_parser.py` — Parse tdom component specifications

### Capabilities

```python
{
    "capabilities": {
        "completionProvider": True,
        "hoverProvider": True,
        "textDocumentSync": {"openClose": True, "change": 1},
    }
}
```

### Key Design Patterns

**1. Separation of concerns:**
- Parser (spec_parser.py) — domain knowledge
- Scanner (component_scanner.py) — workspace indexing
- Providers (completions.py, hover.py) — LSP operations

**2. Domain-specific operations:**
- Completion for `<{ComponentName}` syntax
- Attribute completions with domain rules (class, style, data, aria)
- Hover with component documentation

**3. Workspace scanning:**
- Scans for user-defined components at initialization
- Maintains component registry
- Updates on file changes

### Integration Pattern

```python
server = TDOMLanguageServer()
result = server.initialize(workspace_path)
# → Scans workspace, returns capabilities

completions = server.get_completions(document_text, line, position)
# → Returns completion items

hover_text = server.get_hover(document_text, line, position)
# → Returns markdown documentation
```

### Strategic Value for Punie Phase 26

**This is the blueprint for domain LSP tools:**

1. **Phase 26 (LSP):** Use ty LSP for generic Python operations (goto definition, find references)
2. **Phase 27 (Domain Tools):** Extend with domain-specific LSP features (find tdom components, validate service registrations)

The tdom LSP shows how to **combine generic LSP (ty) with domain-specific semantic operations**.

---

## 3. TweakCC LSP Tool Integration

**Location:** `/Users/pauleveritt/.tweakcc/system-prompts/tool-description-lsp.md`

### TweakCC LSP Tool API

TweakCC (another agent system) has LSP integrated as a tool with the following operations:

**Navigation:**
- `goToDefinition` — Find symbol definitions
- `findReferences` — Find all references
- `goToImplementation` — Find interface implementations

**Information:**
- `hover` — Documentation and type info
- `documentSymbol` — File outline
- `workspaceSymbol` — Cross-file symbol search

**Call Hierarchy:**
- `prepareCallHierarchy` — Get call hierarchy item
- `incomingCalls` — Find callers
- `outgoingCalls` — Find callees

### API Pattern

All operations require:
```python
{
    "filePath": "path/to/file.py",
    "line": 42,           # 1-based
    "character": 10       # 1-based
}
```

### Strategic Value for Punie Phase 26

**This shows LSP as a tool-calling pattern:**

Instead of:
```python
# Text-based
grep_result = grep("class AgentConfig")
file_content = read_file(grep_result.file)
```

Use:
```python
# LSP-based
lsp_result = lsp_query("goToDefinition", symbol="AgentConfig", file="src/agent/config.py", line=1, character=1)
# → Returns precise location
file_content = read_file(lsp_result.file, start=lsp_result.line)
```

**Key insight:** LSP operations become **typed tools** that return structured results, not text.

---

## 4. Comparison: ty LSP vs Alternatives

### Option 1: ty LSP Server

**Pros:**
- Fast (Rust implementation)
- Modern (up-to-date Python features)
- Astral ecosystem (ruff, uv, ty all integrated)
- Growing adoption

**Cons:**
- **Type inference not ready** (81% false positives for Pydantic AI)
- Less mature than pyright
- Fewer LSP features implemented (no rename yet?)

**Verdict for Phase 26:** Use ty LSP for **navigation only** (goto definition, find references, hover). Not for type checking yet.

### Option 2: Pyright/Basedpyright LSP

**Pros:**
- Mature and stable
- Excellent type inference
- Full LSP feature set
- Used by VSCode Python extension

**Cons:**
- Node.js dependency (installation complexity)
- Slower than ty
- Not Astral ecosystem

**Verdict:** Keep for type checking, consider adding LSP operations.

### Option 3: Hybrid Approach

**Use both:**
- **ty LSP:** Navigation (goto definition, find references, hover)
- **Pyright:** Type checking (via existing `ty check` pattern)

**Rationale:** Navigation doesn't require perfect type inference, just symbol location. Type checking requires correctness.

---

## 5. Recommended Phase 26 Implementation Strategy

### Step 1: ty LSP Client (2-3 days)

Implement minimal LSP client for ty:

```python
# In typed_tools.py
class LSPResult(BaseModel):
    """Result from LSP query."""
    operation: str
    file: str | None = None
    line: int | None = None
    column: int | None = None
    symbol_type: str | None = None
    docstring: str | None = None
    locations: list[dict] | None = None  # For find_references
    error: str | None = None

# In toolset.py
def sync_lsp_query(operation: str, file: str, line: int, column: int, **kwargs) -> str:
    """Query ty LSP server."""
    # Connect to ty LSP via JSON-RPC
    # Send request
    # Parse response
    # Return LSPResult as JSON
```

### Step 2: LSP Operations (1-2 days)

Implement core operations:
- `goto_definition(file, line, column)` → location
- `find_references(file, line, column)` → list of locations
- `hover(file, line, column)` → documentation + type info

### Step 3: Training Data (2-3 days)

Generate ~100 examples showing:
- **LSP for symbol lookup** vs text grep
- **Multi-step workflows** (LSP → read → edit → verify)
- **When to use LSP vs text tools**

Example:
```python
# Query: "Find all usages of AgentConfig"
# Wrong approach:
grep_result = grep("AgentConfig")  # ❌ Matches strings in comments

# Right approach:
lsp_result = lsp_query("goto_definition", symbol="AgentConfig", ...)  # ✅ Find definition
refs = lsp_query("find_references", file=lsp_result.file, line=lsp_result.line, ...)  # ✅ Find usages
```

### Step 4: Phase 27 Domain Extension (Future)

After Phase 26 establishes ty LSP integration, extend with domain-specific operations in Phase 27:

```python
# Generic LSP (Phase 26)
lsp_query("find_references", ...)

# Domain LSP (Phase 27)
tdom_lsp_query("find_components", pattern="Button*")
svcs_lsp_query("find_service_registrations", protocol="AuthProtocol")
```

This follows the tdom pattern of **generic LSP + domain-specific extensions**.

---

## 6. Key Takeaways

### For Phase 26 (LSP Integration)

1. **Use ty LSP for navigation** — Don't wait for type checking to be perfect
2. **Reference tdom LSP architecture** — Proven pattern for domain-specific LSP
3. **Follow TweakCC tool API** — LSP as typed tool with structured results
4. **Monitor Pydantic AI issue #3970** — Track upstream ty blocker resolution

### For Phase 27 (Domain Tools)

1. **Extend ty LSP with domain operations** — tdom shows the pattern
2. **Domain validation ≠ LSP** — Domain tools validate *design*, LSP navigates *code*
3. **Combine both** — Use LSP to find code, domain tools to validate architecture

### Strategic Positioning

**Punie would be the first to:**
- Train a model on LSP + domain tool usage
- Combine semantic code navigation (LSP) with architectural validation (domain tools)
- Demonstrate that models can learn to "explore before acting" using LSP

This validates the claim in `lsp-trained-models.md` that **"LSP + RL training + coding agents"** is an unexplored research gap.

---

## 7. Recommended Next Actions

1. ✅ **Complete Phase 25** (7B experiment)
2. 📋 **Create Phase 26 implementation plan:**
   - ty LSP client (minimal JSON-RPC implementation)
   - Core operations (goto_definition, find_references, hover)
   - ~100 training examples
   - Benchmark (LSP precision vs text tools)
3. 📋 **Study tdom_lsp/** — Extract patterns for domain LSP extensions
4. 📋 **Monitor ty issues** — Track resolution of Pydantic AI blockers
5. 📋 **Plan Phase 27** — Domain-specific LSP + validation tools

---

## References

- **Pydantic AI Issue #3970:** <https://github.com/pydantic/pydantic-ai/issues/3970>
- **ty Repository:** <https://github.com/astral-sh/ty>
- **tdom LSP Implementation:** `/Users/pauleveritt/projects/t-strings/tdom/tdom_lsp/`
- **TweakCC LSP Tool:** `/Users/pauleveritt/.tweakcc/system-prompts/tool-description-lsp.md`
- **Punie LSP Research:**
  - `integrate-lsp-into-agent-loop.md`
  - `lsp-trained-models.md`
  - `do-lsps-help-agent-effectiveness.md`
