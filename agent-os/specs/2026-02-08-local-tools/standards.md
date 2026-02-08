# Phase 6.3: Local Tools - Standards

## Python Standards

- Python 3.14 for modern language features
- Use `asyncio.subprocess` for async subprocess management
- Use `pathlib.Path` for filesystem operations
- Dataclass for LocalClient (not frozen due to mutable state)

## Testing Standards

- Function-based tests (never classes)
- Use real filesystem via `tmp_path` fixture
- No mocks — real subprocess operations
- First test: `test_local_client_satisfies_client_protocol` (isinstance check)

## Protocol Implementation

- Must satisfy `Client` protocol from `src/punie/acp/interfaces.py`
- Use `@param_model` decorators (handled by protocol, not implementation)
- Return correct response types (e.g., `ReadTextFileResponse`)

## Error Handling

- File operations: raise appropriate exceptions (FileNotFoundError, etc.)
- Terminal operations: raise if terminal_id not found
- ext_method: raise NotImplementedError (no IDE extensions locally)

## Documentation

- Docstrings on all public methods
- Explain differences from ACP client where relevant
- Document no-op behavior (session_update, ext_notification)

## Code Organization

```
src/punie/local/
├── __init__.py       # Export LocalClient
└── client.py         # LocalClient implementation
```

## Verification Requirements

1. Use `astral:ruff` skill for linting
2. Use `astral:ty` skill for type checking
3. All tests must pass
4. Runtime protocol check: `isinstance(client, Client)` must be True
