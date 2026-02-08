# Shape: Pydantic AI Best Practices Implementation

## Scope

**In Scope:**

- Migrate `system_prompt=` to `instructions=` with rich content
- Add `ModelSettings` for deterministic coding behavior
- Configure retry policies for tools and output validation
- Add output validator to reject empty responses
- Implement `ModelRetry` error handling in all 7 tools
- Add error handling in adapter with `UsageLimitExceeded` and general exceptions
- Add `usage_limits` parameter to adapter
- Comprehensive test coverage for v1 idioms

**Out of Scope:**

- Structured output types (keeping `str` for ACP text protocol)
- Dynamic instructions (static constant sufficient)
- Custom result validators (output validator sufficient)
- Advanced streaming (not supported by ACP protocol)
- Dependency injection patterns (ACPDeps frozen dataclass sufficient)

## Agent Configuration Shape

### Instructions Content

Static module constant with:
- Role definition ("You are Punie...")
- Capabilities (file operations, commands, workspace access)
- Behavioral guidelines (read before modify, explain plans, handle errors)

### Model Settings

```python
ModelSettings(
    temperature=0.0,    # Deterministic for coding
    max_tokens=4096,    # Allow full responses
)
```

### Retry Configuration

- `retries=3` — tool retry count (for ModelRetry exceptions)
- `output_retries=2` — output validation retry count

### Output Validator

Single validator that:
- Checks for empty/whitespace-only responses
- Raises `ModelRetry` with descriptive message
- Returns valid output unchanged

## Tool Error Handling Shape

### Tracked Tools Pattern

Tools with lifecycle tracking (read_file, write_file, run_command):

```
Start tool call → send ToolCallStart
Try:
  Execute ACP operation
  Send ToolCallProgress (completed)
  Return result
Except:
  Raise ModelRetry (triggers retry)
Finally:
  tracker.forget() (cleanup)
```

### Simple Tools Pattern

Tools without tracking (terminal lifecycle):

```
Try:
  Execute ACP operation
  Return result
Except:
  Raise ModelRetry (triggers retry)
```

### Permission Denial Handling

Special case: Permission denied is NOT an error — return string describing denial. LLM should acknowledge denial, not retry blindly.

## Adapter Error Handling Shape

### Error Categories

1. **UsageLimitExceeded** — Token/request limits hit
   - Send error message via session_update
   - Return `PromptResponse(stop_reason="end_turn")`

2. **General Exception** — Agent failures (validation exhausted, tool errors)
   - Log exception with stack trace
   - Send error message via session_update
   - Return `PromptResponse(stop_reason="end_turn")`

### Logging Strategy

- Module-level logger: `logger = logging.getLogger(__name__)`
- Use `logger.exception()` for unexpected errors (includes stack trace)
- Don't log normal control flow (permissions, tool retries)

## Test Strategy

### Factory Tests

- `test_factory_uses_instructions` — verify `agent._instructions` contains "Punie"
- `test_factory_sets_model_settings` — verify `agent.model_settings` property
- `test_factory_sets_retries` — verify `_max_tool_retries` and `_max_result_retries`
- `test_factory_has_output_validator` — verify `len(agent._output_validators) == 1`

### Output Validator Tests

- `test_output_validator_accepts_valid` — non-empty passes through
- `test_output_validator_rejects_empty` — empty exhausts retries → `UnexpectedModelBehavior`

### Adapter Error Handling Tests

- `test_adapter_handles_agent_error` — empty output → adapter catches → session_update
- `test_adapter_accepts_usage_limits` — constructor accepts `usage_limits=` parameter

### Coverage Goals

- All new configuration options tested
- Both success and failure paths covered
- Internal agent state verified where necessary
- Integration with ACP protocol verified
