# Server Management Spec - Shape

## Architecture

```
src/punie/training/
├── __init__.py          # Package exports
├── server_config.py     # ServerConfig dataclass
├── server.py            # ServerProcess lifecycle management
└── benchmark.py         # Training speed benchmarking

tests/
├── test_training_server_config.py
├── test_training_server.py
└── test_training_benchmark.py
```

## Key Design Decisions

### Subprocess-based server management

- mlx_lm.server runs as external process
- No import-time dependency on mlx-lm
- Tests work without mlx-lm installed
- Easier lifecycle control (start/stop/health checks)

### Frozen dataclasses for configuration

- `ServerConfig` is immutable
- Easy to test, share, serialize
- Follows Punie's existing patterns

### Non-frozen dataclass for process management

- `ServerProcess` manages mutable state (subprocess handle)
- Follows `LocalClient` pattern from existing codebase
- Clear lifecycle with async context manager

### Integration via factory pattern

- `create_server_model()` returns Pydantic AI `Model` instance
- Uses `OpenAIProvider` for OpenAI-compatible API
- Seamless integration with existing agent creation

## Dependencies

- `httpx` for health checks (already in dependencies)
- `mlx-lm` as regular dependency (to be added in Phase 14)
- `psutil` optional for memory tracking (already in dependencies)
