# Phase 32: Domain Tools + LibCST Code Tools

## Context

Phase 32 adds domain-aware tools so the model reasons about **design decisions** (components, services, middleware) not just code syntax. It also adds general-purpose LibCST code tools for structured Python manipulation. This is the prerequisite for Phase 33 (full retrain with ~1215 examples including 150 domain tool examples).

**Critical correction from tdom-svcs/examples research:** There is NO `@view` decorator. The actual production patterns are:
- Components: `@dataclass` + `__call__(self) -> Node` + `html(t"...")`
- Services: `@injectable` + `@dataclass` + `Inject[ServiceType]` fields
- Middleware: `@middleware(categories=[...])` + `__call__(self, target, props, context)`

## Status

Implemented 2026-02-17. All files created and tests passing.

## Tool Count

14 (before) → 26 (after):
- 3 base tools unchanged
- 11 existing typed tools unchanged
- 3 new code tools (cst_find_pattern, cst_rename, cst_add_import)
- 9 new domain validators
