# Standards Applied

## Python Dataclasses (frozen=True)

**Standard:** All configuration and data transfer objects use frozen dataclasses.

**Application:**
- `AgentConfig` (Phase 6.4) — frozen, immutable configuration
- `MemorySnapshot` (Phase 6.6) — frozen, point-in-time measurement
- Custom `__init__` on `WorkspaceBoundaryError` for rich error context

**Rationale:** Immutability prevents accidental modification, makes objects hashable, and signals intent clearly.

## Error Handling

**Standard:** Use custom exceptions for domain-specific errors with rich context.

**Application:**
- `WorkspaceBoundaryError` includes both the attempted path and the workspace boundary
- Exception message provides clear, actionable error information
- Custom `__init__` stores path and workspace as attributes for programmatic access

**Rationale:** Rich error context aids debugging and enables callers to handle errors intelligently.

## Configuration Priority

**Standard:** CLI flag > env var > default (established by `resolve_model()`)

**Application:**
- `resolve_mode()` follows exact pattern of existing `resolve_model()`
- Priority order: `--mode` flag > `PUNIE_MODE` env var > `"acp"` default
- Consistent with existing Punie configuration approach

**Rationale:** Users expect CLI flags to override environment, which overrides defaults. Consistency across the codebase reduces cognitive load.

## Backward Compatibility

**Standard:** New features must not break existing usage patterns.

**Application:**
- `create_pydantic_agent(config=None)` — no config = same behavior as before
- Default `AgentConfig()` uses `PUNIE_INSTRUCTIONS` (PyCharm mode)
- Existing `punie serve` invocations unchanged
- ACP mode remains the default

**Rationale:** Users upgrading Punie should not experience breaking changes. PyCharm integration is the primary use case.

## Validation Trade-offs

**Standard:** Balance safety with usability.

**Application:**
- **Phase 6.4:** Python syntax validation OFF by default (ACP mode), ON for local mode
  - Small local models may produce malformed code
  - PyCharm/ACP mode doesn't need validation (IDE handles it)
- **Phase 6.6:** Memory check warns but doesn't block
  - Users may know their system better than heuristics
  - Log warning and actual usage, let user decide

**Rationale:** Don't be overly protective. Provide safety rails, but let users opt out when they know better.

## Pure Functions for Core Logic

**Standard:** Extract pure functions for testability.

**Application:**
- `resolve_workspace_path(workspace, path)` — pure function, no side effects
- `get_memory_snapshot()` — reads current state, no side effects
- `check_memory_available(model_size_mb)` — deterministic given inputs
- `estimate_model_size(model_name)` — pure lookup/default logic

**Rationale:** Pure functions are easier to test, reason about, and compose.

## Stdlib Over Dependencies

**Standard:** Prefer standard library when functionality is adequate.

**Application:**
- `resource.getrusage()` for memory monitoring (stdlib, no psutil needed)
- `ast.parse()` for Python syntax validation (stdlib, no linter dependency)
- `os.sysconf()` for total system RAM (stdlib, Unix-only but sufficient)
- `Path.resolve()` and `is_relative_to()` for path canonicalization (stdlib)

**Rationale:** Fewer dependencies = faster installs, fewer breakages, easier maintenance.

## Test Organization

**Standard:** One test file per module, function-based tests, ~10-20 tests per file.

**Application:**
- `test_agent_config.py` — ~10 tests covering AgentConfig, factory integration, mode switching
- `test_workspace_safety.py` — ~10 tests covering path resolution, traversal attacks, end-to-end
- `test_memory.py` — ~8 tests covering memory snapshot, availability checks, size estimation

**Rationale:** Clear one-to-one mapping between test files and source modules aids navigation.

## Documentation Standards

**Standard:** Specs in `agent-os/specs/YYYY-MM-DD-feature-name/` with plan.md, shape.md, standards.md, references.md.

**Application:**
- Created `agent-os/specs/2026-02-08-local-model-integration/`
- Four spec files documenting all three phases
- Roadmap and evolution.md updated with implementation details

**Rationale:** Comprehensive spec documentation enables future maintainers to understand design decisions.
