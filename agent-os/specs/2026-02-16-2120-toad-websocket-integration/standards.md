# Standards for Toad WebSocket Integration

This spec follows these Agent OS standards:

## agent-verification

Agents should use Astral tools directly via skills rather than convenience wrappers like justfile recipes. This ensures agents get the full context and guidance these tools provide.

### Rationale

- **Justfile recipes** (`just test`, `just lint`) are convenience wrappers for humans and CI/CD
- **Astral skills** (`astral:ruff`, `astral:ty`, `astral:uv`) provide richer context and guidance for agents
- **Direct tool usage** gives better error messages and actionable diagnostics
- **ty LSP** provides real-time type checking feedback during development
- **Skills can provide guidance** on how to fix issues, not just report them

### Rules for Verification

#### Type Checking

**DO:**
- Use the `astral:ty` skill to check types and get guidance
- Pay attention to ty LSP diagnostics as they appear in tool results
- Read and understand type errors before attempting fixes

**DON'T:**
- Run `just lint` or `just typecheck` through Bash
- Ignore ty diagnostics that appear during development

#### Linting and Formatting

**DO:**
- Use the `astral:ruff` skill to check, format, and fix code
- Let ruff guide you on style and error fixes

**DON'T:**
- Run `just lint` or `just format` through Bash
- Apply fixes without understanding what ruff is correcting

#### Testing

**DO:**
- Use `uv run pytest` directly with clear descriptions
- Use `astral:uv` skill if you need guidance on pytest or uv usage
- Specify test paths clearly (e.g., `uv run pytest tests/` not `just test`)

**DON'T:**
- Run `just test` through Bash
- Use justfile test recipes in verification steps

#### Package Management

**DO:**
- Use the `astral:uv` skill for dependency management and guidance
- Run `uv` commands directly when the operation is clear

**DON'T:**
- Run uv commands through bash without understanding the operation
- Skip using the skill when you need guidance on uv features

### Examples

#### ❌ Incorrect - Using Justfile Recipes

```
Bash: just test
Bash: just lint
Bash: just format
```

#### ✅ Correct - Using Astral Skills

```
Skill: astral:ty
  Check types and understand any errors

Skill: astral:ruff
  Check and fix linting issues

Bash: uv run pytest tests/
  Description: Run test suite
```

### In Plan Mode

When writing verification steps in implementation plans, always specify:

```markdown
## Verification

1. Use `astral:ty` skill to check types
2. Use `astral:ruff` skill to check and fix linting
3. Run `uv run pytest tests/` to verify all tests pass
4. Review ty LSP diagnostics for any warnings
```

**Never write:**
```markdown
## Verification

1. Run `just test`
2. Run `just lint`
```

### Exception: Human Documentation

CI/CD configurations, README files, and human-facing documentation should continue referencing justfile recipes, as these are the correct tools for human developers.

---

## function-based-tests

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

### Why Functions

- Simpler, less boilerplate
- No `self` parameter noise
- Fixtures work more naturally
- Pytest's native style

### Rules

- Name: `test_<what>_<scenario>()`
- One assertion focus per test
- Use fixtures for shared setup, not class `setUp`

---

## Application to This Spec

### Verification Steps

Following **agent-verification**, this spec will:

1. Use `astral:ty` skill to check types (not `just typecheck`)
2. Use `astral:ruff` skill to lint and format (not `just lint`)
3. Run `uv run pytest tests/test_toad_integration.py -v` directly (not `just test`)
4. Review ty LSP diagnostics for warnings

### Testing Approach

Following **function-based-tests**, this spec will:

1. Write all tests as functions (no classes)
2. Use clear names: `test_toad_websocket_agent_connects()`
3. One assertion focus per test
4. Use pytest fixtures for shared setup (TestClient, example agent)

### Examples

**Type Checking:**
```
# ✅ Correct
Skill: astral:ty

# ❌ Incorrect
Bash: just typecheck
```

**Testing:**
```python
# ✅ Correct
def test_toad_websocket_agent_connects():
    """Test example agent can connect to Punie server."""
    agent = ToadWebSocketAgent("ws://localhost:8000/ws", "/tmp")
    await agent.connect()
    assert agent._websocket is not None

# ❌ Incorrect
class TestToadWebSocketAgent:
    def test_connects(self):
        ...
```
