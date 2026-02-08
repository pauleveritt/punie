# Shape: Session Registration

## Problem

Phase 4.1 successfully implemented three-tier dynamic tool discovery, but discovery happens **on every `prompt()` call**. This creates inefficiency:

- Redundant RPC calls to `discover_tools()` within the same session
- A new `PydanticAgent` constructed per prompt (wasteful — model, instructions, retries identical)
- No session-scoped caching of discovered tools

## Appetite

**Small batch (1-2 hours)**: Move discovery from per-prompt to session lifecycle.

## Solution

Discover tools **once** during `new_session()`, cache the result as immutable session state, and reuse across all `prompt()` calls for that session.

### Key Components

1. **SessionState frozen dataclass**: Immutable container for `catalog`, `toolset`, `agent`, and `discovery_tier`
2. **_sessions dict**: Maps `session_id -> SessionState` in `PunieAgent`
3. **_discover_and_build_toolset() helper**: Extracted from `prompt()`, called by `new_session()`
4. **Simplified prompt() logic**: Use cached agent from `_sessions[session_id]` if exists, lazy fallback otherwise

### Backward Compatibility

**Lazy fallback**: If `prompt()` is called with an unknown `session_id` (tests that skip `new_session()`), trigger discovery on-demand and cache the result. No breaking changes.

## Rabbit Holes

- **Don't change `new_session()` signature**: It's already async, no need to make it return anything
- **Don't invalidate session state**: Tools are immutable for session lifetime (matches ACP semantics)
- **Don't over-optimize**: Single `_sessions` dict is sufficient, no need for LRU cache or weak refs yet

## No-Gos

- No lifecycle methods like `close_session()` — keep it simple
- No dynamic tool refresh within a session — out of scope
- No validation of session IDs — trust the caller

## Standards Applied

1. `frozen-dataclass-services` — `SessionState` is frozen
2. `function-based-tests` — All new tests are functions, not classes
3. `fakes-over-mocks` — `FakeClient.discover_tools_calls` tracking
4. `sybil-doctest` — Example docstrings use Sybil style
5. `granular-dataclass-factories` — Discovery helper returns `SessionState` directly
