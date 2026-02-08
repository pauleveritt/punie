# References: Dynamic Tool Discovery

## Punie Codebase

### Protocol Layer
- `src/punie/acp/interfaces.py:17` — Client protocol definition
- `src/punie/acp/schema.py:19` — ToolKind Literal type
- `src/punie/acp/schema.py:183` — FileSystemCapability dataclass
- `src/punie/acp/schema.py:1080` — ClientCapabilities dataclass
- `src/punie/acp/schema.py:199` — TerminalCapability dataclass

### Agent Layer
- `src/punie/agent/adapter.py:1` — PunieAgent class (ACP to Pydantic AI bridge)
- `src/punie/agent/toolset.py:1` — Static toolset factory
- `src/punie/agent/factory.py:1` — create_pydantic_agent() factory
- `src/punie/agent/deps.py:1` — ACPDeps dependency injection

### Testing Infrastructure
- `src/punie/testing/fakes.py:1` — FakeClient implementation
- `tests/test_adapter.py:1` — PunieAgent tests (reference for test structure)
- `tests/test_toolset.py:1` — Toolset tests (reference for tool testing)

### Examples
- `examples/09_dynamic_tool_discovery.py:1` — Aspirational example (Tier 3 → Tier 1)
- `examples/01_read_write_file.py:1` — Basic tool usage (reference pattern)

## External References

### Pydantic AI
- [FunctionToolset](https://ai.pydantic.dev/api/tools/#pydantic_ai.tools.FunctionToolset) — Tool container for Pydantic AI agents
- [Tool Definition](https://ai.pydantic.dev/tools/) — How to define tools for Pydantic AI
- [Agent Construction](https://ai.pydantic.dev/agents/) — Agent lifecycle and configuration

### Agent Communication Protocol (ACP)
- [ACP Spec](https://github.com/jetbrains/acp) — Official protocol specification
- [Tool Execution](https://github.com/jetbrains/acp#tool-execution) — How tools are invoked
- [Capabilities](https://github.com/jetbrains/acp#capabilities) — Client capability negotiation

### Python Standards
- [PEP 681 – Data Class Transforms](https://peps.python.org/pep-0681/) — Frozen dataclass semantics
- [PEP 544 – Protocols](https://peps.python.org/pep-0544/) — Structural subtyping
- [JSON Schema](https://json-schema.org/) — Schema language for tool parameters

## Design Patterns

### Protocol Extension Pattern
**Reference:** `src/punie/acp/interfaces.py`

When extending a vendored protocol:
1. Add method to protocol interface (abstract)
2. Add method to test fake (concrete)
3. Document that it's a Punie extension, not upstream
4. Keep return types schema-agnostic (dict, not domain objects)

**Example:**
```python
# Protocol (interfaces.py)
class Client(Protocol):
    async def discover_tools(self, session_id: str, **kwargs) -> dict[str, Any]: ...

# Fake (fakes.py)
class FakeClient:
    async def discover_tools(self, session_id: str, **kwargs) -> dict[str, Any]:
        return {"tools": self.tool_catalog}
```

### Frozen Dataclass Service Pattern
**Reference:** `src/punie/acp/schema.py:183` (FileSystemCapability)

When defining service objects:
1. Use `@dataclass(frozen=True)`
2. Use tuples for collections, not lists
3. Provide query methods, not setters
4. Document immutability in docstring

**Example:**
```python
@dataclass(frozen=True)
class ToolCatalog:
    """Immutable catalog of available tools.

    Construct once, query many times. No mutation after construction.
    """
    tools: tuple[ToolDescriptor, ...]

    def by_name(self, name: str) -> ToolDescriptor | None:
        return next((t for t in self.tools if t.name == name), None)
```

### Dynamic Factory Pattern
**Reference:** `src/punie/agent/toolset.py:19` (create_toolset)

When building dynamic toolsets:
1. Accept catalog/config as input
2. Match known tools by name/signature
3. Generate generic bridges for unknowns
4. Return standard container (FunctionToolset)

**Example:**
```python
def create_toolset_from_catalog(catalog: ToolCatalog) -> FunctionToolset[ACPDeps]:
    tools = []
    for descriptor in catalog.tools:
        if descriptor.name == "read_file":
            tools.append(read_file)
        elif descriptor.name == "write_file":
            tools.append(write_file)
        else:
            tools.append(create_generic_bridge(descriptor))
    return FunctionToolset(*tools)
```

### Fallback Chain Pattern
**Reference:** `src/punie/agent/adapter.py` (current initialize logic)

When providing backward compatibility:
1. Try primary mechanism (discover_tools)
2. Fall back to secondary (client_capabilities)
3. Fall back to default (static toolset)
4. Log which path was taken

**Example:**
```python
async def build_toolset(self) -> FunctionToolset[ACPDeps]:
    if hasattr(self._conn, "discover_tools"):
        catalog_dict = await self._conn.discover_tools(self._session_id)
        catalog = parse_tool_catalog(catalog_dict)
        return create_toolset_from_catalog(catalog)
    elif self._client_capabilities:
        return create_toolset_from_capabilities(self._client_capabilities)
    else:
        return create_toolset()  # All 7 static tools
```

## Implementation Notes

### JSON Schema Subset
For v1, keep tool parameter schemas simple:
- Use only `type`, `description`, `required` fields
- Support `string`, `number`, `boolean`, `object`, `array` types
- Defer complex validation (pattern, format, etc.) to v2

**Example Tool Descriptor:**
```json
{
  "name": "read_file",
  "kind": "read",
  "description": "Read contents of a file",
  "parameters": {
    "type": "object",
    "properties": {
      "path": {"type": "string", "description": "File path"},
      "encoding": {"type": "string", "description": "File encoding"}
    },
    "required": ["path"]
  },
  "requires_permission": false,
  "categories": ["file", "io"]
}
```

### Generic Bridge Function
For unknown tools, create a wrapper that:
1. Takes `**kwargs` matching JSON Schema
2. Calls `ext_method(tool_name, **kwargs)`
3. Returns result or raises clear error

**Implementation Hint:**
```python
def create_generic_bridge(descriptor: ToolDescriptor):
    async def bridge(ctx: RunContext[ACPDeps], **kwargs: Any) -> Any:
        conn = ctx.deps.conn
        return await conn.ext_method(
            descriptor.name,
            session_id=ctx.deps.session_id,
            **kwargs
        )
    bridge.__name__ = descriptor.name
    bridge.__doc__ = descriptor.description
    return bridge
```

### Testing Strategy
1. **Unit tests** — ToolCatalog lookups, frozen dataclass verification
2. **Integration tests** — Toolset creation from catalog/capabilities
3. **Adapter tests** — End-to-end fallback chain
4. **Fake tests** — Protocol satisfaction for FakeClient

Test coverage focus:
- All three fallback paths (catalog → capabilities → default)
- Known tool matching
- Unknown tool generic bridge
- Empty catalog handling
- Missing capabilities handling

## Related Roadmap Items

### Completed (Prerequisites)
- **3.1** — ACP vendoring (enables protocol modification)
- **3.2** — Pydantic AI integration (enables dynamic toolsets)
- **3.3** — Full ACP toolset (establishes 7 static tools)

### Current
- **4.1** — Dynamic tool discovery (this spec)

### Future (Build on This)
- **4.2** — Permission-aware tool execution (uses ToolDescriptor.requires_permission)
- **4.3** — Tool usage analytics (uses ToolCatalog for tracking)
- **4.4** — Tool composition pipelines (uses ToolDescriptor.categories)
- **4.5** — Tool marketplace (uses ToolCatalog as registry interface)

## Open Questions

### Question 1: IDE-Side Implementation Timeline
**Question:** When will PyCharm implement `discover_tools()`?
**Current Answer:** Unknown, but spec is designed for graceful degradation (empty catalog = use static tools)
**Next Step:** Coordinate with IDE team after Punie v1 completion

### Question 2: Tool Schema Versioning
**Question:** How do we handle tool schema evolution?
**Current Answer:** Not needed for v1 (static tools are stable)
**Next Step:** Add version field to ToolDescriptor in 4.2 if needed

### Question 3: Permission Model Integration
**Question:** How does `requires_permission` connect to actual permission system?
**Current Answer:** Field is present but unused in 4.1
**Next Step:** Implement permission checks in 4.2
