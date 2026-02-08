# Standards Applied

This implementation follows these Punie project standards:

## agent-verification

**What:** All agent features must have executable verification tests that simulate real-world usage patterns.

**Application:**
- Factory configuration tested via internal state inspection
- Output validator tested with both valid and empty inputs
- Adapter error handling tested with agent failures
- Test coverage ≥80% for all modified files
- Integration tests verify end-to-end behavior

## protocol-first-design

**What:** Design around protocols (structural interfaces) rather than concrete inheritance hierarchies.

**Application:**
- Tools continue using `Client` protocol from `interfaces.py`
- Error handling doesn't depend on concrete exception types
- `ModelRetry` is Pydantic AI's protocol for retriable errors
- Adapter accepts `usage_limits: UsageLimits | None` (protocol from pydantic_ai)

## frozen-dataclass-services

**What:** Use frozen dataclasses for immutable service configuration and data transfer objects.

**Application:**
- `ACPDeps` remains frozen dataclass (no changes)
- `ModelSettings` is a Pydantic model (immutable by default)
- `UsageLimits` is a Pydantic model (immutable)
- Instructions stored as static string constant

## fakes-over-mocks

**What:** Prefer fake implementations with real behavior over mock frameworks.

**Application:**
- Tests use `TestModel` from Pydantic AI (provides custom_output_text)
- FakeClient continues providing real in-memory implementations
- No mocking of internal Pydantic AI state
- Direct inspection of agent internals where necessary

## function-based-tests

**What:** Write tests as functions, never classes.

**Application:**
- All 8 new tests are `async def test_*()` functions
- No test classes or setUp/tearDown methods
- Direct construction of dependencies in each test
- Each test is independent and self-contained

## pydantic-ai-v1-idioms

**What:** Follow Pydantic AI v1 best practices for agent configuration and error handling.

**Application:**
- Use `instructions=` instead of `system_prompt=`
- Configure `ModelSettings` for deterministic behavior
- Set retry policies (`retries=`, `output_retries=`)
- Register output validators with `@agent.output_validator`
- Raise `ModelRetry` in tools for retriable errors
- Wrap `agent.run()` in try/except for error recovery
- Pass `usage_limits=` to control resource consumption

## explicit-error-handling

**What:** Handle errors explicitly at appropriate boundaries, communicate failures clearly.

**Application:**
- Tools raise `ModelRetry` for ACP errors (triggers retry)
- Adapter catches all exceptions (prevents protocol crashes)
- Errors communicated to IDE via `session_update` text
- Logging captures unexpected failures for debugging
- Permission denials return strings (not errors — LLM should know)
- Tracker cleanup in `finally` blocks (prevents leaks)
