# Vendored ACP SDK

**Source:** https://github.com/anthropics/python-acp-sdk
**Version:** v0.7.1 (approximately, based on schema ref v0.10.5)
**Vendored Date:** 2026-02-07
**Vendored By:** Test-Driven Refactoring (Roadmap Phase 2)

## Purpose

The ACP Python SDK has been vendored into Punie to enable:
1. Modifications for Pydantic AI integration (Phase 3)
2. Free-threaded Python 3.14.2t compatibility fixes
3. Independence from upstream release schedule
4. Direct access to internals for advanced features

## Modifications

The following files were modified during vendoring:

### 1. `router.py:11`
**Change:** `from acp.utils import to_camel_case` → `from .utils import to_camel_case`
**Reason:** Fix absolute import for vendored location

### 2. `interfaces.py:3`
**Change:** Added `runtime_checkable` to imports
**Location:** Line 3
**Reason:** Enable isinstance() checks for protocols

### 3. `interfaces.py:73, 143`
**Change:** Added `@runtime_checkable` decorator to `Client` and `Agent` protocols
**Reason:** Enable protocol satisfaction tests with isinstance()

### 4. `schema.py:1-5`
**Change:** Added vendoring provenance comment
**Reason:** Document source and modification policy

## Known Issues

### Type Checker Warnings (ty)

**Unused type: ignore directives (5 warnings):**
- `telemetry.py:11` - `# type: ignore[assignment]`
- `telemetry.py:18` - `# type: ignore[assignment]`
- `utils.py:111` - `# type: ignore[attr-defined]`
- `utils.py:135` - `# type: ignore[arg-type]`
- `utils.py:158` - `# type: ignore[arg-type]`

These were added for older type checkers and are not needed by ty. Can be removed safely.

**Coroutine vs Awaitable type mismatches (2 errors):**
- `connection.py:334` - `asyncio.create_task()` expects `Coroutine`, receives `Awaitable`
- `task/supervisor.py:41` - Similar issue

These may be Python 3.14t-specific type signature changes. Not impacting runtime behavior.

**tuple vs list mismatch (1 error):**
- `stdio.py:81` - Function expects `list[str]`, receives `tuple[str, ...]`

Minor type annotation inconsistency, does not affect runtime.

**Unused blanket type: ignore (3 warnings):**
- `router.py:93` - Can be removed
- `router.py:97` - Can be removed

## Modification Policy

### What to Modify
- **Critical bugs** affecting Punie's use cases
- **Python 3.14.2t compatibility** issues
- **Pydantic AI integration** needs (Phase 3)
- **Performance optimizations** for free-threading

### What NOT to Modify
- **Feature additions** - Propose upstream instead
- **Style changes** - Maintain upstream consistency
- **Refactoring** - Only if blocking integration

### When to Sync from Upstream
- **Security fixes** - Immediate
- **Critical bugs** - As needed
- **Feature releases** - Evaluate per-phase needs
- **Breaking changes** - Defer until impact assessed

## Exclusions from Quality Checks

### Ruff
`schema.py` is excluded from ruff checking (137KB auto-generated file):
```toml
[tool.ruff]
extend-exclude = ["src/punie/acp/schema.py"]
```

### Coverage
Consider excluding untested vendored modules if coverage remains below 80%:
- `stdio.py` (37% - not used in current phase)
- `transports.py` (24% - not used in current phase)
- `telemetry.py` (52% - optional dependency)

## Updating Vendored Code

To sync with upstream:

```bash
# 1. Check upstream for updates
cd ~/PycharmProjects/python-acp-sdk
git pull

# 2. Copy updated files
cd ~/projects/pauleveritt/punie
rsync -av --delete ~/PycharmProjects/python-acp-sdk/src/acp/ src/punie/acp/

# 3. Reapply modifications (listed above)
# - Fix router.py import
# - Add @runtime_checkable decorators
# - Update schema.py comment

# 4. Run tests
uv run pytest

# 5. Update this file with new version and date
```

## Future Plans

### Phase 3: Pydantic AI Integration
Expected modifications:
- Agent protocol extensions for Pydantic AI tool schema
- Tool execution delegation patterns
- Streaming response handling

### Phase 4: ACP Integration
Expected modifications:
- Dynamic tool discovery implementation
- Runtime tool registration
- Capability negotiation

### Phase 6: Advanced Features
Expected modifications:
- Free-threading optimizations
- Parallel agent operation support
- Performance tuning for GIL-free Python

## References

- **Upstream Repository:** https://github.com/anthropics/python-acp-sdk
- **ACP Specification:** https://agentclientprotocol.com/
- **Vendoring Decision:** See `agent-os/specs/2026-02-07-test-driven-refactoring/shape.md`
- **Roadmap:** See `agent-os/product/roadmap.md` Phase 2
