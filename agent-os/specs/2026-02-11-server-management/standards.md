# Server Management Spec - Standards

## Code Standards

- **Function-based tests**: All tests use functions, never classes
- **Frozen dataclasses**: Configuration objects are immutable
- **Pure functions**: Command builders, validators are side-effect-free
- **Async lifecycle**: Server start/stop use async/await
- **Type safety**: Full type annotations, passes `ty` checks

## Testing Standards

- **Unit tests**: Pure functions tested in isolation
- **Integration tests**: Would require mlx-lm, marked `@pytest.mark.slow` (not in Phase 12)
- **Mock-based**: Simulate process lifecycle without actual server
- **Coverage**: All new code tested, coverage stays above 80%

## Documentation Standards

- **Docstrings**: All public functions and classes
- **Examples**: Usage examples in docstrings
- **Type hints**: Clear parameter and return types
- **Comments**: Explain non-obvious implementation details

## Project Standards

- Use Astral tools via skills (`astral:ruff`, `astral:ty`)
- Python 3.14 modern syntax
- No auto-commit — always ask before creating commits
- Verify with `uv run pytest` directly
