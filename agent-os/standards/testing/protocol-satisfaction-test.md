# Protocol Satisfaction Test

First test for every service: verify implementation satisfies its protocol.

```python
from mypackage.myservice import MyService, MyServiceProtocol

def test_myservice_protocol_satisfied():
    """Test that MyService satisfies MyServiceProtocol."""
    service = MyService()
    assert isinstance(service, MyServiceProtocol)
```

## Why First

- **Catches interface drift**: Detects if implementation diverges from protocol
- **Documents contract**: Test serves as living documentation

## Pattern

```python
def test_<impl>_protocol_satisfied():
    impl = MyImplementation()
    assert isinstance(impl, MyProtocol)
```

## Rules

- Always the first test in the test file
- Name: `test_<implementation>_protocol_satisfied`
- Requires `@runtime_checkable` on the Protocol
