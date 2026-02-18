# Phase 32 Shaping Notes

## Scope

Phase 32 is bounded: add LibCST code tools + 9 domain validators, wire into existing infrastructure.

**In scope:**
- LibCST dependency (production, not dev-only)
- 3 general-purpose code tools (find_pattern, rename, add_import)
- 9 domain validators (3 tdom, 3 svcs, 3 tdom-svcs)
- Result models, stubs, config updates
- Tests + fixtures

**Out of scope:**
- Training data generation (Phase 33 task)
- Full app-level graph analysis (validators check single files)
- t-string native support in LibCST (handle as parse errors gracefully)

## Key Decisions

1. **Validators read local files** — Not through ACP, for simplicity and training alignment
2. **Pattern parameter is structured** — `"FunctionDef"`, `"call:print"`, `"decorator:dataclass"` etc.
3. **Parse errors are graceful** — Return DomainValidationResult with parse_error set
4. **LibCST PositionProvider** — Used for accurate line numbers in CstMatch

## Domain Pattern Summary (from tdom-svcs/examples)

### Components (tdom)
- `@dataclass` decorator on the class
- `__call__(self) -> Node` method
- Body uses `html(...)` or `html(t"...")`
- `Inject[ServiceType]` typed fields for DI

### Services (svcs)
- `@injectable` decorator (from svcs_di.injectors)
- `@dataclass` decorator
- `Inject[OtherService]` typed fields
- No lifecycle annotation in source (managed by container)

### Middleware (tdom-svcs)
- `@middleware(categories=[...])` for global middleware
- `@hookable(categories=[...])` for per-target hookables
- `@injectable` + `@dataclass` for DI-resolved middleware (like AriaVerifierMiddleware)
- `__call__(self, target, props, context)` signature
- Optional `priority: int` field
