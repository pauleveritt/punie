# Shape: Test-Driven Refactoring

## Problem Statement

Punie currently depends on the external `agent-client-protocol` pip package. To enable future Pydantic AI integration (Phase 3), we need to modify the SDK internals. Vendoring enables modification while maintaining clear provenance. Additionally, the test suite bundles multiple concerns in one file and uses hardcoded test doubles, making it hard to extend for model behavior testing.

## Scope Boundaries

### In Scope
- Vendor ACP SDK into `src/punie/acp/`
- Transition all imports from `from acp` to `from punie.acp`
- Remove `agent-client-protocol` pip dependency
- Split monolithic test file by concern (schema, RPC, notifications, tool calls, concurrency)
- Create reusable testing utilities in `src/punie/testing/`
- Build configurable mock infrastructure for model responses
- Make protocols `@runtime_checkable` for isinstance() tests
- Document vendoring decisions and standards in spec files

### Out of Scope
- Modifying SDK behavior or adding features (Phase 3)
- Pydantic AI integration (Phase 3)
- Changing test assertion style or adding new test coverage
- Documentation updates beyond removing external dependency references
- Performance optimization or code cleanup of vendored code

## Key Design Decisions

### 1. Vendor Location: `src/punie/acp/`
**Decision:** Place vendored SDK as a subpackage of punie, not a sibling package.

**Rationale:**
- Clear ownership: "punie.acp" signals this is punie's version
- Simpler imports: `from punie.acp import Agent`
- Package distribution: vendored code ships with punie automatically
- Namespace isolation: avoids conflicts if pip package remains installed temporarily

**Alternative Considered:** Top-level `acp/` package alongside `punie/` — rejected because it suggests independence when this is now owned by punie.

### 2. Testing Utilities as Public Package
**Decision:** Create `src/punie/testing/` (not `tests/helpers/`)

**Rationale:**
- Discoverability: users can import test helpers
- Reusability: examples and external projects can use fakes
- Documentation: Sybil doctests can reference `punie.testing`
- Standards compliance: aligns with "fakes as first-class artifacts" principle

**Alternative Considered:** Keep in `tests/` — rejected because test helpers should be discoverable and documented.

### 3. Flat Test Structure
**Decision:** Split tests via file naming (`test_schema.py`, `test_rpc.py`) not subdirectories

**Rationale:**
- Simplicity: avoids conftest.py scoping complexity
- Discoverability: all tests visible in one directory
- Standard pattern: matches most Python projects
- Fixture sharing: centralized `tests/conftest.py` works naturally

**Alternative Considered:** `tests/unit/`, `tests/integration/` — rejected because distinction is unclear and adds ceremony.

### 4. Minimal SDK Modifications
**Decision:** Only three changes to vendored code:
1. Fix one absolute import in `router.py`
2. Add `@runtime_checkable` to two protocols
3. Add provenance comment to `schema.py`

**Rationale:**
- Easy to verify: diff against upstream minimal
- Easy to update: clear what changed if we pull updates
- Defer optimization: save improvements for Phase 3
- Trust upstream: assume code is already good

**Alternative Considered:** Refactor vendored code during import — rejected because it complicates tracking and isn't needed yet.

### 5. Protocol Satisfaction Tests
**Decision:** Use `isinstance(fake, Protocol)` tests, requires `@runtime_checkable`

**Rationale:**
- Runtime verification: proves fakes actually implement protocols
- Type safety: catches missing methods at test time
- Standards compliance: "agent-verification" standard
- Future-proof: if protocols change, tests fail

**Alternative Considered:** Rely only on type checker — rejected because runtime verification is stronger guarantee.

### 6. Model Responder Protocol
**Decision:** Abstract model behavior via `ModelResponder` protocol with pre-built fakes

**Rationale:**
- Testability: easy to inject canned responses, errors, sequences
- Composability: responders can wrap each other
- Extensibility: users can write custom responders
- Separation: model behavior separate from agent protocol

**Pre-built fakes:**
- `CannedResponder`: Default hardcoded response (matches current behavior)
- `ErrorResponder`: Simulates model failures
- `MultiTurnResponder`: Sequences for multi-turn conversations
- `CallbackResponder`: Arbitrary async callable wrapper

**Alternative Considered:** Subclass `FakeAgent` for each behavior — rejected because composition > inheritance.

## Constraints and Trade-offs

### Constraint: Maintain All Existing Tests
- **Implication:** Refactoring must preserve test coverage
- **Verification:** Test count stays same, all pass
- **Trade-off:** Can't fix questionable test design yet

### Constraint: No Breaking Changes for Examples
- **Implication:** All 9 example files must work after refactor
- **Verification:** Manual run or doctest each example
- **Trade-off:** Can't simplify example APIs yet

### Constraint: Keep Git History Clean
- **Implication:** Vendor as copy, not subtree merge
- **Verification:** Files appear as new in git diff
- **Trade-off:** Lose upstream commit history (but it's still on GitHub)

### Trade-off: Duplicate Code During Transition
- **Acceptance:** Both `agent-client-protocol` pip package and `punie.acp` coexist briefly in Task 2
- **Reason:** Allows verification before removing dependency
- **Resolution:** Task 3 removes pip package

### Trade-off: Large Auto-generated File
- **Acceptance:** `schema.py` is 137KB, excluded from ruff
- **Reason:** Auto-generated by ACP upstream, not meant for human editing
- **Resolution:** Document provenance, exclude from linting, copy verbatim

## Success Criteria

1. **Import Independence:** `uv run python -c "import acp"` fails (pip package gone)
2. **Import Success:** `uv run python -c "from punie.acp import Agent, Client"` works
3. **Test Stability:** `uv run pytest -v` passes with same test count
4. **Example Stability:** All 9 examples run without errors
5. **Type Safety:** `astral:ty` reports no errors
6. **Code Quality:** `astral:ruff` reports no issues
7. **Standards Compliance:** Protocol satisfaction tests exist and pass
8. **Documentation:** Spec files document decisions and standards

## Risk Mitigation

### Risk: SDK has transitive dependencies we miss
- **Likelihood:** Medium (pydantic is obvious, but others?)
- **Mitigation:** Check `agent-client-protocol` dependencies before removal
- **Plan explicitly adds:** `pydantic>=2.0` as direct dependency

### Risk: Absolute imports beyond router.py
- **Likelihood:** Low (plan says only one)
- **Mitigation:** Grep vendored code for `from acp.` patterns
- **Verification:** Import test in Task 2

### Risk: Test split loses subtle interactions
- **Likelihood:** Low (tests look independent)
- **Mitigation:** Run full suite after each split
- **Verification:** Test count matches, all pass

### Risk: Examples have hidden dependencies on test helpers
- **Likelihood:** Medium (example 07 imports from tests/)
- **Mitigation:** Plan explicitly updates example 07
- **Verification:** Run examples after Task 3

## Open Questions (Resolved)

### Q: Should we use git subtree or copy?
**A:** Copy. Simpler, clearer ownership, no ongoing merge complexity.

### Q: Should fakes be in tests/ or src/punie/testing/?
**A:** `src/punie/testing/`. Public package for reusability.

### Q: Should we modify schema.py formatting?
**A:** No. Exclude from ruff, copy verbatim, document provenance.

### Q: Should tests be split into subdirectories?
**A:** No. Flat structure simpler, avoids conftest complexity.

### Q: Should FakeAgent support custom model behavior?
**A:** Yes. Add `ModelResponder` protocol with pre-built implementations.

## References

- **Upstream SDK:** `~/PycharmProjects/python-acp-sdk/`
- **Current tests:** `tests/test_acp_sdk.py` (7 tests)
- **Current helpers:** `tests/acp_helpers.py` (_Server, FakeAgent, FakeClient)
- **Roadmap:** `agent-os/product/roadmap.md` (tasks 2.1-2.4)
- **Standards:** agent-verification, function-based-tests, fakes-over-mocks, protocol-satisfaction-test, sybil-doctest
