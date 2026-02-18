# Phase 32 Standards

## agent-verification
All new tools have corresponding tests. Validators tested with both valid and invalid fixture files. Tool count assertions updated in test_agent_config.py.

## frozen-dataclass-services
Domain models are Pydantic models (not dataclasses) to support JSON serialization and validation. ExternalFunctions in monty_runner.py uses frozen dataclass pattern (unchanged).

## function-based-tests
All tests are function-based (no classes). Follows existing project pattern.

## protocol-first-design
Validators return DomainValidationResult with a consistent schema across all 9 validators. The `domain` field distinguishes which validator family produced the result.
