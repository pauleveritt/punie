# Function-Based Tests

Write tests as functions, never classes.

```python
# CORRECT
def test_user_can_login_with_valid_credentials():
    """Test successful login."""
    user = create_user(password="secret")
    assert user.login("secret") is True

def test_user_cannot_login_with_wrong_password():
    """Test login failure."""
    user = create_user(password="secret")
    assert user.login("wrong") is False
```

```python
# WRONG - Do not do this
class TestUserLogin:
    def test_valid_credentials(self):
        ...
    def test_wrong_password(self):
        ...
```

## Why Functions

- Simpler, less boilerplate
- No `self` parameter noise
- Fixtures work more naturally
- Pytest's native style

## Rules

- Name: `test_<what>_<scenario>()`
- One assertion focus per test
- Use fixtures for shared setup, not class `setUp`
