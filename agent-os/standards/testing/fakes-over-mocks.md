# Fakes Over Mocks

Use simple dataclass fakes, not mock frameworks.

```python
@dataclass
class FakeDatabase:
    """Fake database - predictable, no side effects."""
    _results: dict[str, list[dict]] = field(default_factory=dict)

    def query(self, sql: str) -> list[dict]:
        return self._results.get(sql, [])

def test_service_uses_database():
    fake_db = FakeDatabase(_results={"SELECT * FROM users": [{"id": 1}]})
    service = UserService(db=fake_db)
    assert len(service.get_users()) == 1
```

## Why Fakes

- **Simplicity**: Plain Python classes, no magic
- **Refactor-resilient**: Fakes follow protocol; mocks break on rename
- **Predictable**: Explicit state, no surprising behavior

## Rules

- Fake should implement the same Protocol as the real service
- Keep fakes simple—avoid complex state machines
- Store fakes in test files or `tests/fakes/` if shared
- Never use `unittest.mock` or `pytest-mock` unless absolutely necessary
