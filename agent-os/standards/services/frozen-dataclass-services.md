# Frozen Dataclass Services

Services should be immutable by default.

```python
from dataclasses import dataclass
from svcs_di import Inject

@dataclass(frozen=True)
class CleanBody:
    """Immutable service - no internal state."""

    def __call__(self, body_string: str) -> Element:
        ...
```

## Why Frozen

- Thread-safe / free-threading ready
- Predictable behavior
- Easier to test and reason about

## Exception: Stateful Services

Use non-frozen when service must maintain mutable state:

```python
@dataclass  # NOT frozen
class CacheService:
    """Maintains internal cache state."""
    _cache: dict = field(default_factory=dict)
```

## Rules

- Default to `@dataclass(frozen=True)`
- Only remove `frozen=True` when mutation is required
- Document why a service needs mutable state
