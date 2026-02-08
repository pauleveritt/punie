# Reference Files

## Core Implementation Files

### `src/punie/agent/factory.py`
Current agent factory to upgrade:
- Line 8: `create_pydantic_agent()` function
- Lines 9-15: Current Agent configuration with `system_prompt=`

**Changes needed:**
- Extract instructions to module constant
- Add `instructions=` parameter
- Add `model_settings=ModelSettings(...)`
- Add `retries=3, output_retries=2`
- Register `@agent.output_validator`

### `src/punie/agent/toolset.py`
All 7 tools to add error handling:
- Lines 15-35: `read_file` — tracked tool pattern
- Lines 37-80: `write_file` — tracked tool with permission
- Lines 82-140: `run_command` — tracked tool with permission
- Lines 142-160: Terminal lifecycle tools (4 simple tools)

**Changes needed:**
- Import `ModelRetry` from `pydantic_ai`
- Wrap tracked tools in try/except/finally
- Move `tracker.forget()` to finally block
- Wrap simple tools in try/except
- Raise `ModelRetry(f"Failed to ...: {exc}")` on errors

### `src/punie/agent/adapter.py`
PunieAgent adapter to add error handling:
- Lines 10-30: `__init__()` — add usage_limits parameter
- Lines 50-100: `prompt()` — add try/except around agent.run()

**Changes needed:**
- Add `import logging` and module logger
- Add `usage_limits: UsageLimits | None = None` to `__init__`
- Store as `self._usage_limits`
- Wrap `agent.run()` in try/except
- Catch `UsageLimitExceeded` and general `Exception`
- Send errors via `session_update`
- Return `PromptResponse(stop_reason="end_turn")`
- Pass `usage_limits=self._usage_limits` to `agent.run()`

### `src/punie/agent/deps.py`
ACPDeps frozen dataclass — **no changes needed**.

### `src/punie/acp/schema.py`
ACP protocol types:
- Line 17: `StopReason = Literal["end_turn", "max_tokens", ...]`

**Used in:** adapter error handling returns `PromptResponse(stop_reason="end_turn")`

## Pydantic AI Imports

### Core Types
```python
from pydantic_ai import Agent, RunContext, ModelRetry
from pydantic_ai.models import ModelSettings
from pydantic_ai.exceptions import UsageLimitExceeded, UnexpectedModelBehavior
from pydantic_ai.usage import UsageLimits
```

### Testing Utilities
```python
from pydantic_ai.models.test import TestModel
```

## Verified Pydantic AI Internals

These internal attributes are used for testing configuration:

- `agent._instructions: list[str]` — instructions content
- `agent.model_settings: dict` — property returning settings as dict
- `agent._max_tool_retries: int` — from `retries=` parameter
- `agent._max_result_retries: int` — from `output_retries=` parameter
- `agent._output_validators: list[OutputValidator]` — registered validators

**Note:** These are implementation details, tested carefully with awareness they may change.

## Testing Files

### `tests/test_pydantic_agent.py`
Existing test patterns to follow:
- Lines 1-20: Imports and fixtures
- Lines 30-50: Tool testing with FakeClient
- Lines 60-80: Agent run testing with TestModel

**To add:**
- Factory configuration tests (4 tests)
- Output validator tests (2 tests)
- Adapter error handling tests (2 tests)

### `tests/conftest.py`
Pytest configuration:
- Async test support (pytest-asyncio)
- Coverage configuration

**No changes needed.**

## Supporting Documentation

### `agent-os/product/roadmap.md`
Phase 3.4 definition:
- Lines 200-250: Phase 3.4 tasks and acceptance criteria

**Update after implementation:** Mark phase complete, document completion date.

### `CLAUDE.md`
Project standards reference:
- Lines 1-10: Astral tools usage
- Lines 12-15: Function-based tests
- Lines 17-20: No auto-commit policy

**No changes needed** — v1 idioms align with existing standards.

## Pydantic AI Documentation

### Official Docs (pydantic.dev/pydantic-ai)
- **Instructions vs System Prompts** — v1 migration guide
- **Model Settings** — temperature, max_tokens, etc.
- **Retry Configuration** — retries, output_retries parameters
- **Output Validators** — `@agent.output_validator` decorator
- **ModelRetry** — exception for retriable tool errors
- **UsageLimits** — token/request limits

### Key Concepts
- **Instructions** — re-evaluated per run, not stored in history
- **Retries** — automatic retry on ModelRetry exceptions
- **Validators** — post-process and validate agent outputs
- **Error Recovery** — graceful degradation on limits/failures
