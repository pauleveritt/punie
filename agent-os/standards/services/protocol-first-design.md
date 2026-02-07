# Protocol-First Design

Define service interfaces as `@runtime_checkable` Protocols before implementations.

## Structure

```
service_name/
├── __init__.py    # Export protocol and implementation
├── types.py       # Protocol definition
└── models.py      # Concrete implementation
```

## Protocol Definition (types.py)

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class MyServiceProtocol(Protocol):
    """One-line description of what this service does."""

    def __call__(self, input: InputType) -> OutputType:
        """Method docstring with Args/Returns."""
        ...
```

## Why

- **Testability**: Swap implementations with fakes
- **Type Safety**: Catch breaking changes at dev time
- **Multiple Implementations**: Different contexts (Sphinx, Django, etc.)

## Rules

- Always use `@runtime_checkable` for `isinstance()` checks in tests
- Protocol goes in `types.py`, implementation in `models.py`
- First test: verify implementation satisfies protocol
